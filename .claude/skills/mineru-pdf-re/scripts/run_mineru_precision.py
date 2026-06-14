"""
MinerU Precision Extract — single-file and batch PDF conversion.

Uses the MinerU v4 batch API:
  - POST /api/v4/file-urls/batch  →  batch_id + file_urls[]
  - PUT  {file_url}               →  upload each file
  - GET  /api/v4/extract-results/batch/{batch_id}  →  poll
  - GET  {full_zip_url}           →  download per-file ZIP

Supports:
  - Single file:  python run_mineru_precision.py --input paper.pdf
  - Directory:    python run_mineru_precision.py --input ./pdfs/ --start 10 --limit 20
  - Resume batch: python run_mineru_precision.py --input ./pdfs/ --batch-id <id>
"""

import argparse
import json
import logging
import os
import shutil
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

# ── API Configuration ────────────────────────────────────────────────────────
BASE_URL = "https://mineru.net"
BATCH_UPLOAD_URL = f"{BASE_URL}/api/v4/file-urls/batch"
BATCH_RESULT_URL = f"{BASE_URL}/api/v4/extract-results/batch/{{}}"
MAX_FILES_PER_BATCH = 50


# ── Helpers ──────────────────────────────────────────────────────────────────

def build_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("run_mineru_precision")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def request_with_retry(func, logger: logging.Logger, label: str, attempts: int = 8):
    delay = 5
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:
            if attempt == attempts:
                logger.exception("%s failed after %s attempts", label, attempts)
                raise
            logger.warning("%s failed attempt %s/%s: %s", label, attempt, attempts, exc)
            time.sleep(delay)
            delay = min(delay * 2, 60)


def get_token() -> str:
    token = os.environ.get("MINERU_API_KEY")
    if not token:
        raise RuntimeError("MINERU_API_KEY is not set")
    return token


# ── Single-file helpers (kept for --batch-id resume) ─────────────────────────

def request_upload_single(pdf_path: Path, args, token: str, logger: logging.Logger) -> str:
    """Submit a single file via the batch API and return batch_id."""
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {
        "model_version": args.model_version,
        "enable_formula": args.enable_formula,
        "enable_table": args.enable_table,
        "language": args.language,
        "files": [
            {
                "name": pdf_path.name,
                "is_ocr": args.is_ocr,
                "data_id": str(uuid.uuid4()),
            }
        ],
    }
    response = requests.post(BATCH_UPLOAD_URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    body = response.json()
    if body.get("code") != 0:
        raise RuntimeError(f"upload-url request failed: {body}")
    batch_id = body["data"]["batch_id"]
    file_url = body["data"]["file_urls"][0]
    with pdf_path.open("rb") as f:
        put_resp = requests.put(file_url, data=f, timeout=300)
    if put_resp.status_code not in (200, 201):
        raise RuntimeError(f"file upload failed: {put_resp.status_code}")
    logger.info("uploaded %s batch_id=%s", pdf_path, batch_id)
    return batch_id


# ── Batch API functions ──────────────────────────────────────────────────────

def build_payload(files_info: list[dict], args) -> dict:
    """Build the request payload for the batch upload URL API."""
    return {
        "model_version": args.model_version,
        "enable_formula": args.enable_formula,
        "enable_table": args.enable_table,
        "language": args.language,
        "files": files_info,
    }


def request_batch_upload(files_info: list[dict], args, token: str,
                         logger: logging.Logger) -> tuple[str, list[str]]:
    """Request upload URLs for a batch of files. Returns (batch_id, file_urls)."""
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = build_payload(files_info, args)
    response = request_with_retry(
        lambda: requests.post(BATCH_UPLOAD_URL, headers=headers, json=payload, timeout=120),
        logger,
        "request batch upload urls",
    )
    response.raise_for_status()
    body = response.json()
    if body.get("code") != 0:
        raise RuntimeError(f"batch upload-url request failed: {body}")
    batch_id = body["data"]["batch_id"]
    file_urls = body["data"]["file_urls"]
    logger.info("batch %s: got %d upload URLs", batch_id, len(file_urls))
    return batch_id, file_urls


def upload_files_concurrently(pdf_paths: list[Path], file_urls: list[str],
                              logger: logging.Logger, max_workers: int = 4):
    """Upload local files to the pre-signed URLs concurrently."""
    def _upload(pdf_path: Path, url: str):
        with pdf_path.open("rb") as f:
            resp = requests.put(url, data=f, timeout=300)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"upload failed ({resp.status_code}): {pdf_path.name}")
        return pdf_path.name

    if len(pdf_paths) <= 1 or max_workers <= 1:
        for p, u in zip(pdf_paths, file_urls):
            name = _upload(p, u)
            logger.info("uploaded %s", name)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_upload, p, u): p.name for p, u in zip(pdf_paths, file_urls)}
            for future in as_completed(futures):
                name = future.result()
                logger.info("uploaded %s", name)


def poll_batch_done(batch_id: str, token: str, logger: logging.Logger,
                    timeout: int, interval: int) -> list[dict]:
    """Poll until all files in the batch reach a terminal state.

    Returns the list of extract_result items.
    """
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    start = time.time()
    last_summary = ""

    while time.time() - start < timeout:
        response = request_with_retry(
            lambda: requests.get(BATCH_RESULT_URL.format(batch_id), headers=headers, timeout=120),
            logger,
            "poll batch",
        )
        response.raise_for_status()
        body = response.json()
        if body.get("code") != 0:
            time.sleep(interval)
            continue

        results = body.get("data", {}).get("extract_result", [])
        if not results:
            time.sleep(interval)
            continue

        states = [r.get("state") for r in results]
        done_count = sum(1 for s in states if s == "done")
        failed_count = sum(1 for s in states if s == "failed")
        total = len(states)
        summary = f"{done_count}/{total} done, {failed_count} failed"

        if summary != last_summary:
            # Log progress including per-file page progress
            progress_parts = []
            for r in results:
                s = r.get("state")
                name = r.get("file_name", "?")
                if s == "running":
                    ep = r.get("extract_progress", {})
                    progress_parts.append(
                        f"  {name}: running ({ep.get('extracted_pages', '?')}/{ep.get('total_pages', '?')} pages)"
                    )
                elif s == "done":
                    progress_parts.append(f"  {name}: done")
                elif s == "failed":
                    progress_parts.append(f"  {name}: FAILED — {r.get('err_msg', '')}")
                else:
                    progress_parts.append(f"  {name}: {s}")
            logger.info("batch %s: %s\n%s", batch_id, summary, "\n".join(progress_parts))
            last_summary = summary

        terminal = {"done", "failed"}
        if all(s in terminal for s in states):
            return results

        time.sleep(interval)

    raise TimeoutError(f"batch {batch_id} did not complete within {timeout}s")


def download_and_extract_zip(full_zip_url: str, final_dir: Path,
                             logger: logging.Logger) -> Path:
    """Download a result ZIP and extract to final_dir. Returns zip_path."""
    zip_path = final_dir.parent / f"{final_dir.name}_result.zip"
    response = request_with_retry(
        lambda: requests.get(full_zip_url, timeout=300),
        logger,
        "download zip",
    )
    response.raise_for_status()
    zip_path.write_bytes(response.content)
    final_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(final_dir)
    zip_path.unlink()
    return final_dir


# ── Post-processing ──────────────────────────────────────────────────────────

def rewrite_markdown_image_refs(md_path: Path) -> None:
    """Normalize image references inside the subfolder's full.md."""
    text = md_path.read_text(encoding="utf-8")
    text = text.replace("](./images/", "](images/")
    text = text.replace("](../images/", "](images/")
    md_path.write_text(text, encoding="utf-8")


def cleanup_timestamped_dirs(output_dir: Path, stem: str, logger: logging.Logger) -> None:
    for item in output_dir.iterdir():
        if item.is_dir() and item.name.startswith(f"{stem}_mineru_output_"):
            shutil.rmtree(item)
            logger.info("removed timestamped intermediate dir %s", item)


def remove_pdf_files(target_dir: Path, logger: logging.Logger) -> None:
    for pdf in target_dir.rglob("*.pdf"):
        pdf.unlink()
        logger.info("removed PDF %s", pdf)


def copy_md_to_parent(final_dir: Path, output_dir: Path, stem: str, logger: logging.Logger) -> None:
    src_md = final_dir / "full.md"
    if not src_md.exists():
        logger.warning("full.md not found in %s", final_dir)
        return
    text = src_md.read_text(encoding="utf-8")
    subfolder = final_dir.name
    text = text.replace("](images/", f"]({subfolder}/images/")
    text = text.replace("](./images/", f"]({subfolder}/images/")
    text = text.replace("](../images/", f"]({subfolder}/images/")
    dest_md = output_dir / f"{stem}_mineru.md"
    dest_md.write_text(text, encoding="utf-8")
    logger.info("copied full.md to %s with image refs rewritten", dest_md)


def post_process(final_dir: Path, output_dir: Path, stem: str, logger: logging.Logger):
    """Run all mandatory post-processing on an extracted result folder."""
    full_md = final_dir / "full.md"
    if full_md.exists():
        rewrite_markdown_image_refs(full_md)
    cleanup_timestamped_dirs(output_dir, stem, logger)
    remove_pdf_files(final_dir, logger)
    copy_md_to_parent(final_dir, output_dir, stem, logger)


# ── Single-file pipeline ────────────────────────────────────────────────────

def process_single(pdf_path: Path, output_dir: Path, token: str,
                   args, logger: logging.Logger, batch_id: str | None = None):
    """Full pipeline for a single PDF: upload → poll → download → post-process.

    If batch_id is provided, skip upload and resume from polling.
    """
    stem = pdf_path.stem
    final_dir = output_dir / f"{stem}_mineru"

    if batch_id:
        logger.info("resuming from batch_id=%s", batch_id)
    else:
        batch_id = request_with_retry(
            lambda: request_upload_single(pdf_path, args, token, logger),
            logger,
            "upload pdf",
        )

    logger.info("batch_id=%s", batch_id)
    results = poll_batch_done(batch_id, token, logger, args.timeout, args.poll_interval)

    item = results[0] if results else {}
    state = item.get("state")
    if state == "failed":
        raise RuntimeError(f"extraction failed for {pdf_path.name}: {item.get('err_msg', '')}")
    full_zip_url = item.get("full_zip_url")
    if not full_zip_url:
        raise RuntimeError("full_zip_url not found in result")

    download_and_extract_zip(full_zip_url, final_dir, logger)
    logger.info("extracted MinerU result to %s", final_dir)

    post_process(final_dir, output_dir, stem, logger)


# ── Batch pipeline ───────────────────────────────────────────────────────────

def collect_pdfs(input_path: Path, start: int, limit: int) -> list[Path]:
    """Collect PDF files from a file or directory, applying start/limit."""
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        raise FileNotFoundError(f"Input not found: {input_path}")

    pdfs = sorted(input_path.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found in {input_path}")

    pdfs = pdfs[start:]
    if limit > 0:
        pdfs = pdfs[:limit]
    return pdfs


def process_batch(pdf_paths: list[Path], output_dir: Path, token: str,
                  args, logger: logging.Logger):
    """Batch pipeline: chunk files → upload → poll → download each."""
    total = len(pdf_paths)
    succeeded, failed = [], []

    # Split into chunks of MAX_FILES_PER_BATCH
    chunks = [pdf_paths[i:i + MAX_FILES_PER_BATCH]
              for i in range(0, total, MAX_FILES_PER_BATCH)]

    for ci, chunk in enumerate(chunks):
        logger.info("=== batch chunk %d/%d: %d files ===", ci + 1, len(chunks), len(chunk))

        # Step 1: request upload URLs
        files_info = [
            {"name": p.name, "is_ocr": args.is_ocr, "data_id": str(uuid.uuid4())}
            for p in chunk
        ]
        batch_id, file_urls = request_batch_upload(files_info, args, token, logger)

        # Step 2: upload files concurrently
        upload_files_concurrently(chunk, file_urls, logger, max_workers=4)

        # Step 3: poll batch until all done/failed
        logger.info("polling batch %s for %d files ...", batch_id, len(chunk))
        results = poll_batch_done(batch_id, token, logger, args.timeout, args.poll_interval)

        # Build a lookup: file_name → result
        result_map = {r.get("file_name"): r for r in results}

        # Step 4: download and post-process each completed file
        for pdf_path in chunk:
            stem = pdf_path.stem
            r = result_map.get(pdf_path.name)
            if not r:
                logger.error("no result for %s in batch response", pdf_path.name)
                failed.append((pdf_path.name, "missing from batch response"))
                continue

            state = r.get("state")
            if state == "failed":
                err_msg = r.get("err_msg", "unknown error")
                logger.error("FAILED: %s — %s", pdf_path.name, err_msg)
                failed.append((pdf_path.name, err_msg))
                continue

            full_zip_url = r.get("full_zip_url")
            if not full_zip_url:
                logger.error("no full_zip_url for %s", pdf_path.name)
                failed.append((pdf_path.name, "no full_zip_url"))
                continue

            try:
                final_dir = output_dir / f"{stem}_mineru"
                download_and_extract_zip(full_zip_url, final_dir, logger)
                post_process(final_dir, output_dir, stem, logger)
                logger.info("DONE: %s", pdf_path.name)
                succeeded.append(pdf_path.name)
            except Exception as exc:
                logger.exception("error processing %s", pdf_path.name)
                failed.append((pdf_path.name, str(exc)))

    return succeeded, failed


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="MinerU Precision Extract — single-file and batch PDF conversion"
    )
    parser.add_argument("--input", required=True,
                        help="PDF file or directory of PDFs")
    parser.add_argument("--output-dir", default=None,
                        help="Output directory (default: Output/ocr/mineru)")
    parser.add_argument("--batch-id", default=None,
                        help="Resume from an existing batch_id (single-file mode only)")
    parser.add_argument("--model-version", default="vlm")
    parser.add_argument("--language", default="ch")
    parser.add_argument("--is-ocr", action="store_true")
    parser.add_argument("--enable-formula", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--enable-table", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--timeout", type=int, default=900,
                        help="Max seconds to wait per batch (default: 900)")
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--start", type=int, default=0,
                        help="Skip first N files in batch mode")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max files to process (0=all)")
    parser.add_argument("--log", default=None)
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else Path("Output/ocr/mineru").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path(args.log or f"Output/logs/run_mineru_precision_{time.strftime('%Y%m%d%H%M%S')}.log")
    logger = build_logger(log_path)

    token = get_token()

    # ── Resume mode (legacy single-file) ──
    if args.batch_id:
        if not input_path.is_file():
            raise ValueError("--batch-id requires --input to be a single PDF file")
        process_single(input_path, output_dir, token, args, logger,
                       batch_id=args.batch_id)
        return

    # ── Collect files ──
    pdf_paths = collect_pdfs(input_path, args.start, args.limit)
    logger.info("collected %d PDF(s) from %s", len(pdf_paths), input_path)

    # ── Single file: use single-file pipeline ──
    if len(pdf_paths) == 1:
        process_single(pdf_paths[0], output_dir, token, args, logger)
        return

    # ── Multiple files: use batch pipeline ──
    succeeded, failed = process_batch(pdf_paths, output_dir, token, args, logger)

    # Summary
    logger.info("=" * 60)
    logger.info("Batch complete: %d succeeded, %d failed", len(succeeded), len(failed))
    if failed:
        for name, err in failed:
            logger.error("  FAILED: %s -> %s", name, err)
    print(f"\nDone: {len(succeeded)} succeeded, {len(failed)} failed out of {len(pdf_paths)} files.")
    if failed:
        print("Failed files:")
        for name, err in failed:
            print(f"  {name}: {err}")


if __name__ == "__main__":
    main()
