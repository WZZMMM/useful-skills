#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR-VL-1.6 Async PDF-to-Markdown Converter

Converts PDF files to Markdown using PaddleOCR-VL-1.6 async jobs API.
PDFs exceeding the API page limit (default 100) are automatically split
into chunks, submitted separately, and merged back into a single output.

For each PDF, outputs:
  - {stem}_paddle.md          (merged markdown, images referenced via relative paths)
  - {stem}_paddle/jsonl.jsonl (raw PaddleOCR JSONL result)
  - {stem}_paddle/img/        (downloaded images)

Usage:
    python run_paddle_ocr_async.py --input <PDF file or directory>
    python run_paddle_ocr_async.py --input <PDF> --output <dir>
    python run_paddle_ocr_async.py --input <PDF> --chunk-pages 50

Environment:
    PADDLE_API_KEY - API Token
"""

import os
import re
import sys
import json
import time
import shutil
import argparse
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from pypdf import PdfReader, PdfWriter

# Windows UTF-8 support
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# API Configuration
JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
MODEL = "PaddleOCR-VL-1.6"
POLL_INTERVAL = 5  # seconds
MAX_WAIT = 600     # seconds
MAX_PAGES = 100    # API page limit per request
DEFAULT_OUTPUT = "Output/ocr/paddle"


def build_optional_payload(args) -> dict:
    """Build optionalPayload from CLI args.

    Image correction is OFF by default:
      --orientation  enables useDocOrientationClassify (0/90/180/270 rotation)
      --unwarping    enables useDocUnwarping (wrinkle/skew correction)
    """
    payload = {
        "useDocOrientationClassify": args.orientation,
        "useDocUnwarping": args.unwarping,
        "useChartRecognition": args.chart_recognition,
    }
    # Only include non-None advanced params so API defaults apply
    if args.layout_detection is not None:
        payload["useLayoutDetection"] = args.layout_detection
    if args.layout_threshold is not None:
        payload["layoutThreshold"] = args.layout_threshold
    if args.layout_nms is not None:
        payload["layoutNms"] = args.layout_nms
    if args.layout_unclip_ratio is not None:
        payload["layoutUnclipRatio"] = args.layout_unclip_ratio
    if args.layout_merge_mode is not None:
        payload["layoutMergeBboxesMode"] = args.layout_merge_mode
    if args.layout_shape_mode is not None:
        payload["layoutShapeMode"] = args.layout_shape_mode
    if args.prompt_label is not None:
        payload["promptLabel"] = args.prompt_label
    if args.repetition_penalty is not None:
        payload["repetitionPenalty"] = args.repetition_penalty
    if args.temperature is not None:
        payload["temperature"] = args.temperature
    if args.top_p is not None:
        payload["topP"] = args.top_p
    if args.min_pixels is not None:
        payload["minPixels"] = args.min_pixels
    if args.max_pixels is not None:
        payload["maxPixels"] = args.max_pixels
    if args.show_formula_number is not None:
        payload["showFormulaNumber"] = args.show_formula_number
    if args.restructure_pages is not None:
        payload["restructurePages"] = args.restructure_pages
    if args.merge_tables is not None:
        payload["mergeTables"] = args.merge_tables
    if args.relevel_titles is not None:
        payload["relevelTitles"] = args.relevel_titles
    if args.prettify_markdown is not None:
        payload["prettifyMarkdown"] = args.prettify_markdown
    return payload


def split_pdf(pdf_path: str, max_pages: int, tmp_dir: Path) -> list:
    """Split a PDF into chunks of at most max_pages pages.

    Returns a list of chunk file paths. If the PDF has <= max_pages pages,
    returns [pdf_path] (no split, no temp files).
    """
    reader = PdfReader(pdf_path)
    total = len(reader.pages)
    if total <= max_pages:
        return [pdf_path]

    stem = Path(pdf_path).stem
    chunks = []
    for start in range(0, total, max_pages):
        end = min(start + max_pages, total)
        writer = PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])
        chunk_name = f"{stem}_chunk{start}-{end - 1}.pdf"
        chunk_path = tmp_dir / chunk_name
        with open(chunk_path, "wb") as f:
            writer.write(f)
        chunks.append(str(chunk_path))
        print(f"    Split: pages {start+1}-{end} -> {chunk_name}")
    print(f"  Split {total} pages into {len(chunks)} chunks (limit={max_pages})")
    return chunks


def submit_job(pdf_path: str, api_key: str, optional_payload: dict) -> str:
    """Submit a PDF to PaddleOCR async API and return jobId."""
    headers = {"Authorization": f"bearer {api_key}"}

    if pdf_path.startswith("http"):
        headers["Content-Type"] = "application/json"
        payload = {
            "fileUrl": pdf_path,
            "model": MODEL,
            "optionalPayload": optional_payload,
        }
        resp = requests.post(JOB_URL, json=payload, headers=headers)
    else:
        data = {
            "model": MODEL,
            "optionalPayload": json.dumps(optional_payload),
        }
        with open(pdf_path, "rb") as f:
            resp = requests.post(JOB_URL, headers=headers, data=data, files={"file": f})

    if resp.status_code != 200:
        raise Exception(f"Job submit failed ({resp.status_code}): {resp.text}")

    return resp.json()["data"]["jobId"]


def poll_job(job_id: str, api_key: str) -> dict:
    """Poll job status until done/failed. Return job result data."""
    headers = {"Authorization": f"bearer {api_key}"}
    start = time.time()

    while True:
        if time.time() - start > MAX_WAIT:
            raise TimeoutError(f"Job {job_id} timed out after {MAX_WAIT}s")

        resp = requests.get(f"{JOB_URL}/{job_id}", headers=headers)
        if resp.status_code != 200:
            raise Exception(f"Poll failed ({resp.status_code}): {resp.text}")

        data = resp.json()["data"]
        state = data["state"]

        if state == "done":
            return data
        elif state == "failed":
            raise Exception(f"Job failed: {data.get('errorMsg', 'unknown')}")
        elif state == "running":
            progress = data.get("extractProgress", {})
            total = progress.get("totalPages", "?")
            done = progress.get("extractedPages", "?")
            print(f"    running: {done}/{total} pages", end="\r")

        time.sleep(POLL_INTERVAL)


def download_and_merge(jsonl_urls: list, output_dir: Path, stem: str) -> str:
    """Download JSONL results from one or more chunks, merge into final artifacts.

    Args:
        jsonl_urls: List of JSONL download URLs, one per chunk (in page order).
        output_dir: Top-level output directory.
        stem: Original PDF filename stem.

    Output structure:
        {stem}_paddle.md           - merged markdown
        {stem}_paddle/jsonl.jsonl  - raw PaddleOCR JSONL (all chunks concatenated)
        {stem}_paddle/img/         - downloaded images

    MD image references use relative paths: {stem}_paddle/img/{filename}
    """
    # Create subfolder structure
    subfolder = output_dir / f"{stem}_paddle"
    img_dir = subfolder / "img"
    img_dir.mkdir(parents=True, exist_ok=True)

    all_jsonl_lines = []
    md_parts = []
    all_images = {}  # relative_path -> remote_url
    used_local_names = set()  # track filenames to avoid collisions

    for chunk_idx, jsonl_url in enumerate(jsonl_urls):
        resp = requests.get(jsonl_url)
        resp.raise_for_status()

        raw_text = resp.text
        all_jsonl_lines.append(raw_text)

        for line in raw_text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            result = json.loads(line)["result"]
            for page_result in result.get("layoutParsingResults", []):
                md_data = page_result.get("markdown", {})
                text = md_data.get("text", "")
                if text:
                    md_parts.append(text)
                for rel_path, remote_url in md_data.get("images", {}).items():
                    # If the same rel_path appears in multiple chunks, later
                    # chunks overwrite earlier ones (shouldn't happen for split PDFs).
                    all_images[rel_path] = remote_url

    # Save concatenated raw JSONL
    jsonl_path = subfolder / "jsonl.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        f.write("\n".join(all_jsonl_lines) + "\n")

    # Merge markdown text
    merged_md = "\n\n".join(md_parts)

    # Download images and rewrite references
    for rel_path, remote_url in all_images.items():
        orig_name = Path(rel_path).name
        # Replace underscores with hyphens
        local_name = orig_name.replace("_", "-")
        # Handle filename collisions across chunks by appending chunk index
        if local_name in used_local_names:
            base = Path(local_name).stem
            suffix = Path(local_name).suffix
            idx = 2
            while f"{base}_{idx}{suffix}" in used_local_names:
                idx += 1
            local_name = f"{base}_{idx}{suffix}"
        used_local_names.add(local_name)

        local_path = img_dir / local_name
        if not local_path.exists():
            try:
                img_resp = requests.get(remote_url)
                if img_resp.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(img_resp.content)
            except Exception:
                pass
        # Rewrite reference in markdown
        merged_md = merged_md.replace(rel_path, f"{stem}_paddle/img/{local_name}")

    # Clean up empty image references and collapse blank lines
    merged_md = re.sub(r"!\[[^\]]*\]\(\s*\)", "", merged_md)
    merged_md = re.sub(r"\n{3,}", "\n\n", merged_md)

    # Write merged markdown
    md_path = output_dir / f"{stem}_paddle.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(merged_md)

    return str(md_path)


def process_single_pdf(pdf_path: str, output_dir: Path, api_key: str,
                       optional_payload: dict, chunk_pages: int = MAX_PAGES) -> dict:
    """Process a single PDF: split (if needed) -> submit -> poll -> merge."""
    stem = Path(pdf_path).stem

    print(f"  Processing: {stem}")
    try:
        # Split large PDFs into chunks if needed
        total_pages = len(PdfReader(pdf_path).pages)
        needs_split = total_pages > chunk_pages
        if needs_split:
            tmp_dir = output_dir / f"{stem}_tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            chunks = split_pdf(pdf_path, chunk_pages, tmp_dir)
        else:
            chunks = [pdf_path]

        # Submit and poll each chunk
        jsonl_urls = []
        for idx, chunk_path in enumerate(chunks):
            label = f"chunk {idx+1}/{len(chunks)}" if needs_split else "submit"
            print(f"    {label}: {Path(chunk_path).name}")
            job_id = submit_job(chunk_path, api_key, optional_payload)
            print(f"    Job ID: {job_id}")
            result_data = poll_job(job_id, api_key)
            jsonl_urls.append(result_data["resultUrl"]["jsonUrl"])

        # Download and merge results from all chunks
        md_path = download_and_merge(jsonl_urls, output_dir, stem)

        # Cleanup temp split files
        if needs_split and tmp_dir.exists():
            shutil.rmtree(tmp_dir)

        print(f"  Done: {md_path}")
        return {"pdf": pdf_path, "md": md_path, "status": "success"}
    except Exception as e:
        print(f"  FAILED: {e}")
        return {"pdf": pdf_path, "md": None, "status": f"failed: {e}"}


def collect_pdfs(input_path: str) -> list:
    """Collect PDF files from a file or directory."""
    p = Path(input_path)
    if p.is_file():
        return [str(p)]
    elif p.is_dir():
        return sorted(str(f) for f in p.rglob("*.pdf"))
    else:
        raise FileNotFoundError(f"Input not found: {input_path}")


def main():
    parser = argparse.ArgumentParser(description="PaddleOCR async PDF-to-Markdown converter")
    parser.add_argument("--input", "-i", required=True, help="PDF file or directory")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT, help=f"Output directory (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--api-key", default=None, help="API key (or set PADDLE_API_KEY)")
    parser.add_argument("--workers", "-w", type=int, default=3, help="Parallel workers (default: 3)")
    parser.add_argument("--start", type=int, default=0, help="Start index in file list")
    parser.add_argument("--limit", type=int, default=0, help="Max files to process (0=all)")
    parser.add_argument("--chunk-pages", type=int, default=MAX_PAGES,
                        help=f"Max pages per API request; larger PDFs are split (default: {MAX_PAGES})")

    # ── Image correction (OFF by default) ──
    parser.add_argument("--orientation", action="store_true", default=False,
                        help="Enable doc orientation classification (rotate 0/90/180/270). OFF by default.")
    parser.add_argument("--unwarping", action="store_true", default=False,
                        help="Enable doc unwarping (correct wrinkles/skew). OFF by default.")
    parser.add_argument("--chart-recognition", action="store_true", default=False,
                        help="Enable chart recognition (parse charts into tables). OFF by default.")

    # ── Layout detection ──
    parser.add_argument("--layout-detection", type=lambda x: x.lower() == "true", default=None, metavar="BOOL",
                        help="Enable layout detection (default: API default). Pass true/false.")
    parser.add_argument("--layout-threshold", type=float, default=None,
                        help="Layout region filter threshold")
    parser.add_argument("--layout-nms", type=lambda x: x.lower() == "true", default=None, metavar="BOOL",
                        help="Enable NMS post-processing for layout detection")
    parser.add_argument("--layout-unclip-ratio", type=float, default=None,
                        help="Layout detection expansion ratio")
    parser.add_argument("--layout-merge-mode", default=None,
                        help="Layout overlap box merge mode")
    parser.add_argument("--layout-shape-mode", default=None, choices=["rect", "quad", "poly", "auto"],
                        help="Layout detection result geometry shape mode")

    # ── VL model tuning ──
    parser.add_argument("--prompt-label", default=None, choices=["ocr", "formula", "table", "chart"],
                        help="VL prompt type (only when layout detection is off)")
    parser.add_argument("--repetition-penalty", type=float, default=None,
                        help="Repetition penalty (increase when text repeats)")
    parser.add_argument("--temperature", type=float, default=None,
                        help="Temperature (decrease for stability, increase if missing content)")
    parser.add_argument("--top-p", type=float, default=None,
                        help="Top-P sampling (decrease for more conservative results)")
    parser.add_argument("--min-pixels", type=float, default=None,
                        help="Minimum image pixel count")
    parser.add_argument("--max-pixels", type=float, default=None,
                        help="Maximum image pixel count")

    # ── Output formatting ──
    parser.add_argument("--show-formula-number", type=lambda x: x.lower() == "true", default=None, metavar="BOOL",
                        help="Include formula numbers in Markdown output")
    parser.add_argument("--restructure-pages", type=lambda x: x.lower() == "true", default=None, metavar="BOOL",
                        help="Restructure multi-page results for cross-page table merging and title leveling")
    parser.add_argument("--merge-tables", type=lambda x: x.lower() == "true", default=None, metavar="BOOL",
                        help="Merge cross-page tables (only when layout detection is off)")
    parser.add_argument("--relevel-titles", type=lambda x: x.lower() == "true", default=None, metavar="BOOL",
                        help="Identify paragraph heading levels (only when layout detection is off)")
    parser.add_argument("--prettify-markdown", type=lambda x: x.lower() == "true", default=None, metavar="BOOL",
                        help="Output prettified Markdown")

    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("PADDLE_API_KEY")
    if not api_key:
        print("Error: No API key. Set PADDLE_API_KEY or use --api-key")
        sys.exit(1)

    pdfs = collect_pdfs(args.input)
    if args.start > 0:
        pdfs = pdfs[args.start:]
    if args.limit > 0:
        pdfs = pdfs[:args.limit]

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    optional_payload = build_optional_payload(args)

    print(f"Found {len(pdfs)} PDF(s) | Output: {output_dir} | Workers: {args.workers}")
    print(f"Output per PDF: {{stem}}_paddle.md + {{stem}}_paddle/ (jsonl.jsonl + img/)")
    print(f"Payload: {json.dumps(optional_payload, ensure_ascii=False)}\n")

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_single_pdf, pdf, output_dir, api_key,
                            optional_payload, args.chunk_pages): pdf
            for pdf in pdfs
        }
        for i, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            ok = sum(1 for r in results if r["status"] == "success")
            fail = sum(1 for r in results if r["status"] != "success")
            print(f"\nProgress: {i}/{len(pdfs)} (ok={ok}, fail={fail})")

    ok = sum(1 for r in results if r["status"] == "success")
    fail = sum(1 for r in results if r["status"] != "success")
    print(f"\n{'='*50}\nDone: {ok} success, {fail} failed\n{'='*50}")


if __name__ == "__main__":
    main()
