import argparse
import logging
import time
from pathlib import Path

import requests


CREATE_URL = "https://mineru.net/api/v1/agent/parse/file"
RESULT_URL = "https://mineru.net/api/v1/agent/parse/{}"


def build_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("run_mineru_agent_light")
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


def create_task(pdf_path: Path, args, logger: logging.Logger) -> str:
    payload = {
        "file_name": pdf_path.name,
        "language": args.language,
        "enable_table": args.enable_table,
        "is_ocr": args.is_ocr,
        "enable_formula": args.enable_formula,
    }
    if args.page_range:
        payload["page_range"] = args.page_range
    response = requests.post(CREATE_URL, json=payload, timeout=120)
    response.raise_for_status()
    body = response.json()
    if body.get("code") != 0:
        raise RuntimeError(f"create task failed: {body}")
    task_id = body["data"]["task_id"]
    file_url = body["data"]["file_url"]
    with pdf_path.open("rb") as file_obj:
        put_response = requests.put(file_url, data=file_obj, timeout=300)
    if put_response.status_code not in (200, 201):
        raise RuntimeError(f"file upload failed: {put_response.status_code}")
    logger.info("uploaded %s task_id=%s", pdf_path, task_id)
    return task_id


def wait_for_markdown(task_id: str, logger: logging.Logger, timeout: int, interval: int) -> str:
    start = time.time()
    while time.time() - start < timeout:
        response = request_with_retry(
            lambda: requests.get(RESULT_URL.format(task_id), timeout=120),
            logger,
            "poll task",
        )
        response.raise_for_status()
        body = response.json()
        logger.info("task response: %s", str(body)[:2000])
        if body.get("code") != 0:
            time.sleep(interval)
            continue
        data = body.get("data", {})
        state = data.get("state")
        if state == "failed":
            raise RuntimeError(f"task failed: {body}")
        if state == "done" and data.get("markdown_url"):
            return data["markdown_url"]
        time.sleep(interval)
    raise TimeoutError(f"task {task_id} did not complete within {timeout}s")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--language", default="ch")
    parser.add_argument("--is-ocr", action="store_true")
    parser.add_argument("--enable-formula", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--enable-table", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--page-range", default=None)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--poll-interval", type=int, default=5)
    parser.add_argument("--log", default=None)
    args = parser.parse_args()

    pdf_path = Path(args.input).resolve()
    output_md = Path(args.output_md).resolve()
    output_md.parent.mkdir(parents=True, exist_ok=True)
    log_path = Path(args.log or f"Output/logs/run_mineru_agent_light_{time.strftime('%Y%m%d%H%M%S')}.log")
    logger = build_logger(log_path)

    task_id = args.task_id or request_with_retry(
        lambda: create_task(pdf_path, args, logger),
        logger,
        "create/upload task",
    )
    markdown_url = wait_for_markdown(task_id, logger, args.timeout, args.poll_interval)
    response = request_with_retry(lambda: requests.get(markdown_url, timeout=120), logger, "download markdown")
    response.raise_for_status()
    output_md.write_text(response.text, encoding="utf-8")
    logger.info("wrote markdown only to %s", output_md)


if __name__ == "__main__":
    main()
