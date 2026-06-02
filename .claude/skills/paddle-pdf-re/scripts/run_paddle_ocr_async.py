#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaddleOCR-VL-1.6 Async PDF-to-Markdown Converter

Converts PDF files to Markdown using PaddleOCR-VL-1.6 async jobs API.
For each PDF, outputs:
  - {stem}_paddle.md          (merged markdown, images referenced via relative paths)
  - {stem}_paddle/jsonl.jsonl (raw PaddleOCR JSONL result)
  - {stem}_paddle/img/        (downloaded images)

Usage:
    python run_paddle_ocr_async.py --input <PDF file or directory>
    python run_paddle_ocr_async.py --input <PDF> --output <dir>

Environment:
    PADDLE_API_KEY - API Token
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Windows UTF-8 support
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# API Configuration
JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
MODEL = "PaddleOCR-VL-1.6"
POLL_INTERVAL = 5  # seconds
MAX_WAIT = 600     # seconds
DEFAULT_OUTPUT = "Output/ocr/paddle"


def submit_job(pdf_path: str, api_key: str) -> str:
    """Submit a PDF to PaddleOCR async API and return jobId."""
    headers = {"Authorization": f"bearer {api_key}"}
    optional_payload = {
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useChartRecognition": False,
    }

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


def download_and_merge(jsonl_url: str, output_dir: Path, stem: str) -> str:
    """Download JSONL result, save raw data, download images, merge into markdown.

    Output structure:
        {stem}_paddle.md           - merged markdown
        {stem}_paddle/jsonl.jsonl  - raw PaddleOCR result
        {stem}_paddle/img/         - downloaded images

    MD image references use relative paths: {stem}_paddle/img/{filename}
    """
    resp = requests.get(jsonl_url)
    resp.raise_for_status()

    # Create subfolder structure
    subfolder = output_dir / f"{stem}_paddle"
    img_dir = subfolder / "img"
    img_dir.mkdir(parents=True, exist_ok=True)

    # Save raw JSONL
    jsonl_path = subfolder / "jsonl.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        f.write(resp.text)

    # Parse pages and collect images
    md_parts = []
    all_images = {}  # relative_path -> remote_url

    for line in resp.text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        result = json.loads(line)["result"]
        for page_result in result.get("layoutParsingResults", []):
            md_data = page_result.get("markdown", {})
            text = md_data.get("text", "")
            if text:
                md_parts.append(text)
            all_images.update(md_data.get("images", {}))

    merged_md = "\n\n".join(md_parts)

    # Download images and replace paths with relative references
    for rel_path, remote_url in all_images.items():
        local_name = Path(rel_path).name
        local_path = img_dir / local_name
        if not local_path.exists():
            try:
                img_resp = requests.get(remote_url)
                if img_resp.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(img_resp.content)
            except Exception:
                pass
        # Replace in markdown with relative path including subfolder
        merged_md = merged_md.replace(rel_path, f"{stem}_paddle/img/{local_name}")

    # Write merged markdown
    md_path = output_dir / f"{stem}_paddle.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(merged_md)

    return str(md_path)


def process_single_pdf(pdf_path: str, output_dir: Path, api_key: str) -> dict:
    """Process a single PDF: submit -> poll -> download -> merge."""
    stem = Path(pdf_path).stem

    print(f"  Submitting: {stem}")
    try:
        job_id = submit_job(pdf_path, api_key)
        print(f"  Job ID: {job_id}")

        result_data = poll_job(job_id, api_key)
        jsonl_url = result_data["resultUrl"]["jsonUrl"]

        md_path = download_and_merge(jsonl_url, output_dir, stem)
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

    print(f"Found {len(pdfs)} PDF(s) | Output: {output_dir} | Workers: {args.workers}")
    print(f"Output per PDF: {{stem}}_paddle.md + {{stem}}_paddle/ (jsonl.jsonl + img/)\n")

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_single_pdf, pdf, output_dir, api_key): pdf
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
