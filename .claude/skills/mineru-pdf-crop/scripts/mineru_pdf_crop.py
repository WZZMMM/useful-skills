import argparse
import csv
import json
import re
from copy import copy
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

TARGET_TYPES = {"table", "chart", "image"}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def find_mineru_dir(pdf_path: Path) -> Path:
    for base in [Path("Output/ocr/mineru"), pdf_path.parent]:
        candidate = base / f"{pdf_path.stem}_mineru"
        if (candidate / "layout.json").exists():
            return candidate
    raise FileNotFoundError("MinerU precision output folder not found")


def first_content_list(mineru_dir: Path) -> Path:
    files = sorted(mineru_dir.glob("*content_list*.json"))
    if not files:
        raise FileNotFoundError(f"No content_list JSON found in {mineru_dir}")
    preferred = [p for p in files if "_v2" not in p.stem]
    return preferred[0] if preferred else files[0]


def text_join(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return " ".join(text_join(v) for v in value).strip()
    return str(value).strip()


def figure_number(*texts: str) -> str:
    match = re.search(
        r"\b(Table|Figure|Fig\.?)\s*([A-Z]?\d+[A-Za-z0-9.\-]*)",
        " ".join(t for t in texts if t),
        re.I,
    )
    if not match:
        return ""
    label = "Figure" if match.group(1).lower().startswith("fig") else match.group(1).title()
    return f"{label} {match.group(2)}"


def collect_layout_blocks(mineru_dir: Path) -> dict[tuple[int, str], list[list[float]]]:
    layout = load_json(mineru_dir / "layout.json")
    pages = layout.get("pdf_info", layout if isinstance(layout, list) else [])
    grouped: dict[tuple[int, str], list[list[float]]] = {}
    for idx, page in enumerate(pages):
        page_idx = int(page.get("page_idx", idx))
        for block in page.get("para_blocks") or page.get("preproc_blocks") or []:
            typ = block.get("type")
            bbox = block.get("bbox")
            if typ in TARGET_TYPES and bbox and len(bbox) == 4:
                grouped.setdefault((page_idx, typ), []).append(bbox)
    return grouped


def collect_content_items(mineru_dir: Path) -> list[dict]:
    items = []
    for item in load_json(first_content_list(mineru_dir)):
        typ = item.get("type")
        if typ not in TARGET_TYPES or item.get("page_idx") is None:
            continue
        caption = text_join(item.get("table_caption") or item.get("image_caption") or item.get("caption"))
        body = text_join(item.get("table_body") or item.get("content") or item.get("text"))
        items.append(
            {
                "page_idx": int(item["page_idx"]),
                "type": typ,
                "content_bbox": item.get("bbox") or [],
                "mineru_image": item.get("img_path") or item.get("image_path") or "",
                "caption": caption,
                "figure_table_number": figure_number(caption, body[:300]),
            }
        )
    return items


def clamp(v: float, low: float, high: float) -> float:
    return max(low, min(high, v))


def rect_from_top_left_bbox(bbox, page_w: float, page_h: float, margin: float) -> RectangleObject:
    x0, y0, x1, y1 = [float(v) for v in bbox]
    x0, x1 = clamp(x0 - margin, 0, page_w), clamp(x1 + margin, 0, page_w)
    y0, y1 = clamp(y0 - margin, 0, page_h), clamp(y1 + margin, 0, page_h)
    return RectangleObject([x0, page_h - y1, x1, page_h - y0])


def rect_from_scaled_bbox(bbox, page_w: float, page_h: float, scale_w: float, scale_h: float, margin: float):
    x0, y0, x1, y1 = [float(v) for v in bbox]
    return rect_from_top_left_bbox(
        [x0 / scale_w * page_w, y0 / scale_h * page_h, x1 / scale_w * page_w, y1 / scale_h * page_h],
        page_w,
        page_h,
        margin,
    )


def crop_pdf(reader: PdfReader, page_idx: int, rect: RectangleObject, output_path: Path) -> None:
    page = copy(reader.pages[page_idx])
    page.cropbox = rect
    page.mediabox = rect
    writer = PdfWriter()
    writer.add_page(page)
    with output_path.open("wb") as f:
        writer.write(f)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--mineru-dir")
    parser.add_argument("--output")
    parser.add_argument("--margin", type=float, default=4.0)
    parser.add_argument("--types", nargs="+", default=sorted(TARGET_TYPES))
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    mineru_dir = Path(args.mineru_dir) if args.mineru_dir else find_mineru_dir(pdf_path)
    output_dir = Path(args.output or f"Output/beamer/img_{pdf_path.stem}_mineru")
    output_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(pdf_path))
    layout = collect_layout_blocks(mineru_dir)
    items = [i for i in collect_content_items(mineru_dir) if i["type"] in set(args.types)]

    page_items = {}
    for item in items:
        page_items.setdefault(item["page_idx"], []).append(item)
    scale = {}
    for page_idx, same_page in page_items.items():
        page = reader.pages[page_idx]
        max_x = max([float(i["content_bbox"][2]) for i in same_page if len(i["content_bbox"]) == 4] or [float(page.mediabox.width)])
        max_y = max([float(i["content_bbox"][3]) for i in same_page if len(i["content_bbox"]) == 4] or [float(page.mediabox.height)])
        scale[page_idx] = (max(max_x, float(page.mediabox.width)), max(max_y, float(page.mediabox.height)))

    offsets = {}
    rows = []
    for index, item in enumerate(items, 1):
        page_idx, typ = item["page_idx"], item["type"]
        if page_idx >= len(reader.pages):
            continue
        page = reader.pages[page_idx]
        page_w, page_h = float(page.mediabox.width), float(page.mediabox.height)
        key = (page_idx, typ)
        offset = offsets.get(key, 0)
        offsets[key] = offset + 1
        source_bbox = []
        if offset < len(layout.get(key, [])):
            source_bbox = layout[key][offset]
            rect = rect_from_top_left_bbox(source_bbox, page_w, page_h, args.margin)
        elif len(item["content_bbox"]) == 4:
            sw, sh = scale[page_idx]
            rect = rect_from_scaled_bbox(item["content_bbox"], page_w, page_h, sw, sh, args.margin)
        else:
            continue
        slug = item["figure_table_number"].lower().replace(" ", "") or f"item{index:03d}"
        pdf_name = f"{pdf_path.stem}_p{page_idx + 1:03d}_{index:03d}_{typ}_{slug}.pdf"
        crop_pdf(reader, page_idx, rect, output_dir / pdf_name)
        rows.append(
            {
                "index": index,
                "page": page_idx + 1,
                "page_idx": page_idx,
                "type": typ,
                "source_bbox": json.dumps(source_bbox, ensure_ascii=False),
                "content_bbox": json.dumps(item["content_bbox"], ensure_ascii=False),
                "figure_table_number": item["figure_table_number"],
                "caption": item["caption"],
                "mineru_image": item["mineru_image"],
                "cropped_pdf": pdf_name,
            }
        )

    fields = ["index", "page", "page_idx", "type", "source_bbox", "content_bbox", "figure_table_number", "caption", "mineru_image", "cropped_pdf"]
    with (output_dir / "manifest.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / "manifest.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"cropped {len(rows)} items to {output_dir}")


if __name__ == "__main__":
    main()
