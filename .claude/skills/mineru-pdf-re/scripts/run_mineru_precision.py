import argparse
import json
import logging
import os
import time
import uuid
import zipfile
from pathlib import Path

import requests


BASE_URL = "https://mineru.net"
BATCH_UPLOAD_URL = f"{BASE_URL}/api/v4/file-urls/batch"
BATCH_RESULT_URL = f"{BASE_URL}/api/v4/extract-results/batch/{{}}"


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


def request_upload(pdf_path: Path, args, token: str, logger: logging.Logger) -> str:
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
    with pdf_path.open("rb") as file_obj:
        put_response = requests.put(file_url, data=file_obj, timeout=300)
    if put_response.status_code not in (200, 201):
        raise RuntimeError(f"file upload failed: {put_response.status_code}")
    logger.info("uploaded %s batch_id=%s", pdf_path, batch_id)
    return batch_id


def wait_for_done(batch_id: str, token: str, logger: logging.Logger, timeout: int, interval: int) -> dict:
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    start = time.time()
    while time.time() - start < timeout:
        response = request_with_retry(
            lambda: requests.get(BATCH_RESULT_URL.format(batch_id), headers=headers, timeout=120),
            logger,
            "poll batch",
        )
        response.raise_for_status()
        body = response.json()
        logger.info("batch response: %s", json.dumps(body, ensure_ascii=False)[:2000])
        if body.get("code") != 0:
            time.sleep(interval)
            continue
        results = body.get("data", {}).get("extract_result", [])
        if any(item.get("state") == "failed" for item in results):
            raise RuntimeError(f"batch failed: {body}")
        if results and all(item.get("state") == "done" for item in results):
            return body
        time.sleep(interval)
    raise TimeoutError(f"batch {batch_id} did not complete within {timeout}s")


def download_zip(result: dict, output_dir: Path, stem: str, logger: logging.Logger) -> Path:
    results = result.get("data", {}).get("extract_result", [])
    full_zip_url = next((item.get("full_zip_url") for item in results if item.get("full_zip_url")), None)
    if not full_zip_url:
        raise RuntimeError("full_zip_url not found in MinerU result")
    zip_path = output_dir / f"{stem}_mineru_result.zip"
    response = request_with_retry(lambda: requests.get(full_zip_url, timeout=300), logger, "download zip")
    response.raise_for_status()
    zip_path.write_bytes(response.content)
    return zip_path


def rewrite_markdown_image_refs(md_path: Path) -> None:
    text = md_path.read_text(encoding="utf-8")
    text = text.replace("](./images/", "](images/")
    text = text.replace("](../images/", "](images/")
    md_path.write_text(text, encoding="utf-8")


def cleanup_timestamped_dirs(output_dir: Path, stem: str, logger: logging.Logger) -> None:
    for item in output_dir.iterdir():
        if item.is_dir() and item.name.startswith(f"{stem}_mineru_output_"):
            import shutil
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--model-version", default="vlm")
    parser.add_argument("--language", default="ch")
    parser.add_argument("--is-ocr", action="store_true")
    parser.add_argument("--enable-formula", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--enable-table", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--log", default=None)
    args = parser.parse_args()

    pdf_path = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else Path("Output/ocr/mineru").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path(args.log or f"Output/logs/run_mineru_precision_{time.strftime('%Y%m%d%H%M%S')}.log")
    logger = build_logger(log_path)

    token = os.environ.get("MINERU_API_KEY")
    if not token:
        raise RuntimeError("MINERU_API_KEY is not set")

    batch_id = args.batch_id or request_with_retry(
        lambda: request_upload(pdf_path, args, token, logger),
        logger,
        "upload pdf",
    )
    logger.info("batch_id=%s", batch_id)
    result = wait_for_done(batch_id, token, logger, args.timeout, args.poll_interval)
    zip_path = download_zip(result, output_dir, pdf_path.stem, logger)

    final_dir = output_dir / f"{pdf_path.stem}_mineru"
    final_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(final_dir)
    zip_path.unlink()

    full_md = final_dir / "full.md"
    if full_md.exists():
        rewrite_markdown_image_refs(full_md)
    logger.info("extracted complete MinerU result to %s", final_dir)

    cleanup_timestamped_dirs(output_dir, pdf_path.stem, logger)
    remove_pdf_files(final_dir, logger)
    copy_md_to_parent(final_dir, output_dir, pdf_path.stem, logger)


if __name__ == "__main__":
    main()
