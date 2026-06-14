"""
Extract table and chart bounding boxes from MinerU layout.json sub-blocks,
compute union bbox (caption + body + footnote), and crop from original PDF.
"""

import argparse
import csv
import json
import re
from copy import copy
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

TARGET_TYPES = {"table", "chart"}


def figure_number(caption: str) -> str:
    match = re.search(
        r"\b(Table|Figure|Fig\.?)\s*([A-Z]?\d+[A-Za-z0-9.\-]*)",
        caption,
        re.I,
    )
    if not match:
        return ""
    label = "Figure" if match.group(1).lower().startswith("fig") else match.group(1).title()
    return f"{label} {match.group(2)}"


def text_from_lines(lines: list) -> str:
    parts = []
    for line in lines:
        for span in line.get("spans", []):
            parts.append(span.get("content", ""))
    return " ".join(parts).strip()


def union_bbox(bboxes: list[list[float]]) -> list[float]:
    return [
        min(b[0] for b in bboxes),
        min(b[1] for b in bboxes),
        max(b[2] for b in bboxes),
        max(b[3] for b in bboxes),
    ]


def clamp(v: float, low: float, high: float) -> float:
    return max(low, min(high, v))


def crop_rect(bbox: list[float], page_w: float, page_h: float, margin: float) -> RectangleObject:
    x0, y0, x1, y1 = [float(v) for v in bbox]
    x0 = clamp(x0 - margin, 0, page_w)
    y0 = clamp(y0 - margin, 0, page_h)
    x1 = clamp(x1 + margin, 0, page_w)
    y1 = clamp(y1 + margin, 0, page_h)
    # MinerU: top-left origin -> pypdf: bottom-left origin
    return RectangleObject([x0, page_h - y1, x1, page_h - y0])


def extract_blocks(layout_path: Path) -> list[dict]:
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    pages = layout.get("pdf_info", layout if isinstance(layout, list) else [])

    results = []
    for page_idx, page in enumerate(pages):
        actual_idx = int(page.get("page_idx", page_idx))
        for block in page.get("para_blocks") or page.get("preproc_blocks") or []:
            typ = block.get("type")
            if typ not in TARGET_TYPES:
                continue

            caption_bboxes, body_bboxes, footnote_bboxes = [], [], []
            caption_texts, footnote_texts = [], []

            for sub in block.get("blocks", []):
                sub_type = sub.get("type", "")
                sub_bbox = sub.get("bbox")
                if not (sub_bbox and len(sub_bbox) == 4):
                    continue
                if "caption" in sub_type:
                    caption_bboxes.append(sub_bbox)
                    caption_texts.append(text_from_lines(sub.get("lines", [])))
                elif "body" in sub_type:
                    body_bboxes.append(sub_bbox)
                elif "footnote" in sub_type:
                    footnote_bboxes.append(sub_bbox)
                    footnote_texts.append(text_from_lines(sub.get("lines", [])))

            # fallback to top-level bbox
            top_bbox = block.get("bbox")
            if top_bbox and len(top_bbox) == 4:
                if not body_bboxes and not caption_bboxes:
                    body_bboxes = [top_bbox]

            all_bboxes = caption_bboxes + body_bboxes + footnote_bboxes
            if not all_bboxes:
                continue

            caption_text = " ".join(caption_texts).strip()
            footnote_text = "\n".join(footnote_texts).strip()

            results.append({
                "page_idx": actual_idx,
                "block_type": typ,
                "union_bbox": union_bbox(all_bboxes),
                "body_bbox": union_bbox(body_bboxes) if body_bboxes else [],
                "caption_bbox": union_bbox(caption_bboxes) if caption_bboxes else [],
                "footnote_bbox": union_bbox(footnote_bboxes) if footnote_bboxes else [],
                "caption_text": caption_text,
                "footnote_text": footnote_text,
                "figure_number": figure_number(caption_text),
            })

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--layout", required=True, help="Path to MinerU layout.json")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--margin", type=float, default=2.0)
    parser.add_argument("--types", nargs="+", default=sorted(TARGET_TYPES))
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    output_dir = Path(args.output)
    tables_dir = output_dir / "tables"
    charts_dir = output_dir / "charts"
    for d in [tables_dir, charts_dir]:
        d.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(pdf_path))
    items = [i for i in extract_blocks(Path(args.layout)) if i["block_type"] in set(args.types)]

    csv_fields = ["index", "page_idx", "figure_number",
                  "union_bbox", "body_bbox", "caption_bbox", "footnote_bbox",
                  "caption_text", "footnote_text"]

    tables_csv_rows, charts_csv_rows = [], []
    manifest = []

    for idx, item in enumerate(items, 1):
        page_idx = item["page_idx"]
        if page_idx >= len(reader.pages):
            continue
        page = reader.pages[page_idx]
        page_w, page_h = float(page.mediabox.width), float(page.mediabox.height)

        rect = crop_rect(item["union_bbox"], page_w, page_h, args.margin)

        slug = item["figure_number"].lower().replace(" ", "") or f"item{idx:03d}"
        pdf_name = f"{pdf_path.stem}_p{page_idx + 1:03d}_{idx:03d}_{item['block_type']}_{slug}.pdf"

        if item["block_type"] == "table":
            out_path = tables_dir / pdf_name
            tables_csv_rows.append({**item, "index": idx})
        else:
            out_path = charts_dir / pdf_name
            charts_csv_rows.append({**item, "index": idx})

        page_copy = copy(page)
        page_copy.cropbox = rect
        page_copy.mediabox = rect
        writer = PdfWriter()
        writer.add_page(page_copy)
        with out_path.open("wb") as f:
            writer.write(f)

        manifest.append({
            "page": page_idx + 1,
            "type": item["block_type"],
            "figure_number": item["figure_number"],
            "caption": item["caption_text"][:120],
            "cropped_pdf": f"{'tables' if item['block_type'] == 'table' else 'charts'}/{pdf_name}",
        })
        print(f"  {pdf_name}")

    # write CSVs
    stem = pdf_path.stem + "_mineru"
    for rows, suffix in [(tables_csv_rows, "_tables"), (charts_csv_rows, "_charts")]:
        csv_path = output_dir / f"{stem}{suffix}.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                out = {**row}
                for k in ("union_bbox", "body_bbox", "caption_bbox", "footnote_bbox"):
                    out[k] = json.dumps(out[k], ensure_ascii=False) if out[k] else ""
                writer.writerow(out)

    # write manifest
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    n_tables = sum(1 for m in manifest if m["type"] == "table")
    n_charts = sum(1 for m in manifest if m["type"] == "chart")
    print(f"\nDone: {n_tables} tables + {n_charts} charts -> {output_dir}")


if __name__ == "__main__":
    main()
