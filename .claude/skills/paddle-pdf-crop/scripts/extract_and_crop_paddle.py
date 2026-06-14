"""
Extract table and chart bounding boxes from PaddleOCR JSONL results.
Groups figure_title + table/chart + vision_footnote blocks by spatial proximity,
then merges multiple blocks sharing the same figure number.
"""

import argparse
import csv
import json
import re
from copy import copy
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

TITLE_Y_TOLERANCE = 60
FOOTNOTE_Y_TOLERANCE = 80


def figure_number(text: str) -> str:
    match = re.search(
        r"\b(Table|Figure|Fig\.?)\s*([A-Z]?\d+[A-Za-z0-9.\-]*)",
        text,
        re.I,
    )
    if not match:
        return ""
    label = "Figure" if match.group(1).lower().startswith("fig") else match.group(1).title()
    return f"{label} {match.group(2)}"


def union_bbox(bboxes: list[list[float]]) -> list[float]:
    return [
        min(b[0] for b in bboxes),
        min(b[1] for b in bboxes),
        max(b[2] for b in bboxes),
        max(b[3] for b in bboxes),
    ]


def clamp(v: float, low: float, high: float) -> float:
    return max(low, min(high, v))


def crop_rect(bbox: list[float], page_w: float, page_h: float,
              scale_x: float, scale_y: float, margin: float) -> RectangleObject:
    x0, y0, x1, y1 = [float(v) for v in bbox]
    x0, x1 = x0 * scale_x, x1 * scale_x
    y0, y1 = y0 * scale_y, y1 * scale_y
    x0 = clamp(x0 - margin, 0, page_w)
    y0 = clamp(y0 - margin, 0, page_h)
    x1 = clamp(x1 + margin, 0, page_w)
    y1 = clamp(y1 + margin, 0, page_h)
    return RectangleObject([x0, page_h - y1, x1, page_h - y0])


def flatten_jsonl(jsonl_path: Path) -> list[dict]:
    pages = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            batch = json.loads(line)
            results = batch["result"]["layoutParsingResults"]
            page_dims = batch["result"]["dataInfo"]["pages"]
            for i, r in enumerate(results):
                pages.append({
                    "width": page_dims[i]["width"],
                    "height": page_dims[i]["height"],
                    "prunedResult": r["prunedResult"],
                })
    return pages


def group_page_blocks(blocks: list[dict]) -> list[dict]:
    """Group figure_title + table/chart + vision_footnote by spatial proximity.

    Algorithm:
    1. Assign each body to the nearest title above (within TITLE_Y_TOLERANCE).
    2. Bodies with no title above are absorbed into the nearest group above
       if no other title intervenes (handles multi-panel tables).
    3. Assign each footnote to the nearest body above (within FOOTNOTE_Y_TOLERANCE).
    """

    titles = sorted(
        [b for b in blocks if b["label"] == "figure_title"],
        key=lambda b: b["bbox"][1],
    )
    bodies = sorted(
        [b for b in blocks if b["label"] in ("table", "chart")],
        key=lambda b: b["bbox"][1],
    )
    footnotes = sorted(
        [b for b in blocks if b["label"] == "vision_footnote"],
        key=lambda b: b["bbox"][1],
    )

    # Step 1: assign each body to a title
    body_title_idx = []  # index into titles, or -1
    for body in bodies:
        b_y0 = body["bbox"][1]
        best_i, best_dist = -1, float("inf")
        for i, t in enumerate(titles):
            dist = b_y0 - t["bbox"][3]
            if 0 <= dist <= TITLE_Y_TOLERANCE and dist < best_dist:
                best_i, best_dist = i, dist
        body_title_idx.append(best_i)

    # Step 2: absorb orphan bodies into nearest group above (no intervening title)
    for j, body in enumerate(bodies):
        if body_title_idx[j] >= 0:
            continue
        b_y0 = body["bbox"][1]
        # find nearest assigned body above
        best_group_title, best_dist = -1, float("inf")
        for k in range(j - 1, -1, -1):
            if body_title_idx[k] < 0:
                continue
            gap = b_y0 - bodies[k]["bbox"][3]
            # check no title lies between
            mid_y = (bodies[k]["bbox"][3] + b_y0) / 2
            blocked = any(
                bodies[k]["bbox"][3] < t["bbox"][1] < b_y0 for t in titles
            )
            if not blocked and 0 <= gap < best_dist:
                best_group_title = body_title_idx[k]
                best_dist = gap
        if best_group_title >= 0:
            body_title_idx[j] = best_group_title

    # Step 3: build groups
    title_groups: dict[int, dict] = {}
    for j, body in enumerate(bodies):
        ti = body_title_idx[j]
        if ti >= 0:
            if ti not in title_groups:
                title_groups[ti] = {
                    "title": titles[ti],
                    "bodies": [],
                    "body_indices": [],
                }
            title_groups[ti]["bodies"].append(body)
            title_groups[ti]["body_indices"].append(j)
        else:
            # standalone body with no title
            title_groups[(-j - 1)] = {
                "title": None,
                "bodies": [body],
                "body_indices": [j],
            }

    # Step 4: assign footnotes to nearest body above
    body_fn_map: dict[int, list] = {j: [] for j in range(len(bodies))}
    for fn in footnotes:
        fn_y0 = fn["bbox"][1]
        best_j, best_dist = -1, float("inf")
        for j, body in enumerate(bodies):
            dist = fn_y0 - body["bbox"][3]
            if 0 <= dist <= FOOTNOTE_Y_TOLERANCE and dist < best_dist:
                best_j, best_dist = j, dist
        if best_j >= 0:
            body_fn_map[best_j].append(fn)

    # Step 5: assemble final groups
    merged = []
    for key in sorted(title_groups.keys()):
        g = title_groups[key]
        t = g["title"]
        caption = t["content"].strip() if t else ""
        caption_bbox = t["bbox"] if t else []

        all_bodies = [b["bbox"] for b in g["bodies"]]
        all_fn = []
        fn_texts = []
        for j in g["body_indices"]:
            for fn in body_fn_map.get(j, []):
                all_fn.append(fn["bbox"])
                fn_texts.append(fn["content"].strip())

        all_bboxes = all_bodies[:]
        if caption_bbox:
            all_bboxes.append(caption_bbox)
        all_bboxes.extend(all_fn)

        body_type = g["bodies"][0]["label"]

        merged.append({
            "figure_number": figure_number(caption),
            "union_bbox": union_bbox(all_bboxes),
            "body_bboxes": all_bodies,
            "caption_bbox": caption_bbox,
            "footnote_bbox": union_bbox(all_fn) if all_fn else [],
            "caption_text": caption,
            "footnote_text": "\n".join(fn_texts),
            "body_type": body_type,
        })

    return merged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--jsonl", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--margin", type=float, default=2.0)
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    output_dir = Path(args.output)
    tables_dir = output_dir / "tables"
    charts_dir = output_dir / "charts"
    for d in [tables_dir, charts_dir]:
        d.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(pdf_path))
    paddle_pages = flatten_jsonl(Path(args.jsonl))

    tables_csv, charts_csv = [], []
    manifest = []
    global_idx = 0

    for page_idx, ppage in enumerate(paddle_pages):
        if page_idx >= len(reader.pages):
            break

        pdf_page = reader.pages[page_idx]
        pdf_w = float(pdf_page.mediabox.width)
        pdf_h = float(pdf_page.mediabox.height)
        scale_x = pdf_w / ppage["width"]
        scale_y = pdf_h / ppage["height"]

        blocks = []
        for b in ppage["prunedResult"].get("parsing_res_list", []):
            bbox = b.get("block_bbox")
            if bbox and len(bbox) == 4:
                blocks.append({
                    "label": b.get("block_label", ""),
                    "bbox": bbox,
                    "content": b.get("block_content", ""),
                })

        groups = group_page_blocks(blocks)

        for g in groups:
            global_idx += 1
            g["page_idx"] = page_idx

            is_chart = g["body_type"] == "chart"
            block_type = "chart" if is_chart else "table"

            slug = g["figure_number"].lower().replace(" ", "") or f"item{global_idx:03d}"
            pdf_name = f"{pdf_path.stem}_p{page_idx + 1:03d}_{global_idx:03d}_{block_type}_{slug}.pdf"

            rect = crop_rect(g["union_bbox"], pdf_w, pdf_h, scale_x, scale_y, args.margin)
            page_copy = copy(pdf_page)
            page_copy.cropbox = rect
            page_copy.mediabox = rect
            writer = PdfWriter()
            writer.add_page(page_copy)

            if is_chart:
                out_path = charts_dir / pdf_name
                charts_csv.append({**g, "index": global_idx})
            else:
                out_path = tables_dir / pdf_name
                tables_csv.append({**g, "index": global_idx})

            with out_path.open("wb") as f:
                writer.write(f)

            manifest.append({
                "page": page_idx + 1,
                "type": block_type,
                "figure_number": g["figure_number"],
                "caption": g["caption_text"][:120],
                "cropped_pdf": f"{'charts' if is_chart else 'tables'}/{pdf_name}",
            })
            print(f"  {pdf_name}")

    # write CSVs
    fields = ["index", "page_idx", "figure_number",
              "union_bbox", "body_bboxes", "caption_bbox", "footnote_bbox",
              "caption_text", "footnote_text"]
    stem = pdf_path.stem + "_paddle"
    for rows, suffix in [(tables_csv, "_tables"), (charts_csv, "_charts")]:
        csv_path = output_dir / f"{stem}{suffix}.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                out = {
                    "index": row["index"],
                    "page_idx": row["page_idx"],
                    "figure_number": row["figure_number"],
                    "union_bbox": json.dumps(row["union_bbox"]),
                    "body_bboxes": json.dumps(row["body_bboxes"]),
                    "caption_bbox": json.dumps(row["caption_bbox"]) if row["caption_bbox"] else "",
                    "footnote_bbox": json.dumps(row["footnote_bbox"]) if row["footnote_bbox"] else "",
                    "caption_text": row["caption_text"],
                    "footnote_text": row["footnote_text"],
                }
                writer.writerow(out)

    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    n_tables = sum(1 for m in manifest if m["type"] == "table")
    n_charts = sum(1 for m in manifest if m["type"] == "chart")
    print(f"\nDone: {n_tables} tables + {n_charts} charts -> {output_dir}")


if __name__ == "__main__":
    main()
