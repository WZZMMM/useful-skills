"""
Memo Paper Worker - Process a single PDF file with a single LLM model.
Called by memo_papers.py orchestrator. Not intended for direct user invocation.
"""

import os
import sys
import time
import json
import re
import logging
from pathlib import Path

from openai import OpenAI
import httpx


DEFAULT_TIMEOUT = 1200.0
DEFAULT_MAX_RETRIES = 3

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # Output/Skills/.../scripts -> project root
SCRIPTS_DIR = Path(__file__).parent
DOCS_DIR = SCRIPTS_DIR.parent / "references"


def setup_logging(log_dir: Path) -> logging.Logger:
    """Setup logging to file and console."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"memo_paper_{time.strftime('%Y%m%d_%H%M%S')}.log"

    logger = logging.getLogger("memo_paper")
    logger.setLevel(logging.DEBUG)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def load_provider_config(provider: str) -> dict:
    """Load provider configuration from references directory."""
    config_path = DOCS_DIR / f"{provider}_config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Provider config not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_api_key(config: dict) -> str:
    """Get API key from environment or .env file."""
    env_var = config["api_key_env"]

    api_key = os.environ.get(env_var)
    if api_key:
        return api_key

    env_file = SCRIPTS_DIR / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{env_var}="):
                    api_key = line.split("=", 1)[1].strip()
                    if api_key:
                        return api_key

    raise ValueError(f"API key not found. Set environment variable: {env_var}")


def load_prompt(prompt_name: str) -> str:
    """Load system prompt from Prompts directory."""
    prompt_path = PROJECT_ROOT / "Prompts" / f"{prompt_name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_path}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def get_paper_info(pdf_path: str) -> tuple:
    """
    Extract author, year info from PDF filename.
    Expected format: "LastName et al. - Year - Title.pdf"
    Returns: (author_str, year)
    """
    filename = Path(pdf_path).stem

    year_match = re.search(r'(\d{4})', filename)
    year = year_match.group(1) if year_match else "Unknown"

    parts = re.split(r'\s*-\s*', filename, maxsplit=2)
    author = parts[0] if parts else "Unknown"

    return author, year


def upload_file(client: OpenAI, file_path: str, logger: logging.Logger) -> str:
    """Upload a PDF file and return the file ID."""
    logger.info(f"  Uploading: {Path(file_path).name}")

    with open(file_path, "rb") as f:
        file = client.files.create(file=f, purpose="user_data")

    file_id = file.id
    logger.info(f"  File ID: {file_id}")

    logger.info("  Waiting for file processing...")
    max_wait = 300
    wait_time = 0

    while wait_time < max_wait:
        time.sleep(3)
        wait_time += 3
        file_status = client.files.retrieve(file_id)
        if file_status.status == "active":
            logger.info("  File processed")
            return file_id
        elif file_status.status == "error":
            raise Exception("File processing failed")

    raise Exception("File processing timeout")


def generate_memo(client: OpenAI, model_id: str, system_prompt: str,
                  file_id: str, author: str, year: str, journal: str,
                  logger: logging.Logger,
                  timeout: float = DEFAULT_TIMEOUT) -> tuple:
    """
    Generate memo using Responses API with thinking enabled.
    Returns: (reasoning_text, output_text, token_usage)
    """
    user_prompt = f"{author} ({year}, {journal})"
    logger.info(f"  Generating memo for: {user_prompt}")
    logger.info(f"  Model: {model_id}")

    reasoning_text = ""
    output_text = ""
    token_usage = {}

    client_timeout = OpenAI(
        base_url=client.base_url,
        api_key=client.api_key,
        http_client=httpx.Client(
            proxy=None,
            trust_env=False,
            timeout=httpx.Timeout(timeout, connect=60.0)
        )
    )

    response = client_timeout.responses.create(
        model=model_id,
        input=[
            {
                "role": "system",
                "content": [
                    {"type": "input_text", "text": system_prompt}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "input_file", "file_id": file_id},
                    {"type": "input_text", "text": f"Please write a memo for this paper based on the system instructions.\n\nPaper: {user_prompt}"}
                ]
            }
        ],
        stream=True,
        extra_body={
            "thinking": {"type": "enabled"},
            "temperature": 0.3
        }
    )

    for event in response:
        if event.type == "response.reasoning_summary_text.delta":
            delta = getattr(event, 'delta', '')
            if delta:
                reasoning_text += delta
        elif event.type == "response.reasoning_summary_text.done":
            text = getattr(event, 'text', '')
            if text:
                reasoning_text = text
        elif event.type == "response.output_text.delta":
            delta = getattr(event, 'delta', '')
            if delta:
                output_text += delta
        elif event.type == "response.output_text.done":
            text = getattr(event, 'text', '')
            if text:
                output_text = text
        elif event.type == "response.completed":
            resp = getattr(event, 'response', None)
            if resp and hasattr(resp, 'usage'):
                u = resp.usage
                token_usage = {
                    'input_tokens': getattr(u, 'input_tokens', 0),
                    'output_tokens': getattr(u, 'output_tokens', 0),
                    'total_tokens': getattr(u, 'total_tokens', 0),
                }
                if hasattr(u, 'output_tokens_details'):
                    details = u.output_tokens_details
                    token_usage['reasoning_tokens'] = getattr(details, 'reasoning_tokens', 0)
                if hasattr(u, 'input_tokens_details'):
                    details = u.input_tokens_details
                    cached = getattr(details, 'cached_tokens', 0)
                    if cached > 0:
                        token_usage['cached_tokens'] = cached
                logger.info(f"  Tokens: input={token_usage['input_tokens']}, "
                          f"output={token_usage['output_tokens']}, "
                          f"total={token_usage['total_tokens']}")

    return reasoning_text, output_text, token_usage


def format_token_comment(token_usage: dict) -> str:
    """Format token usage as HTML comment."""
    if not token_usage:
        return ""
    parts = []
    if token_usage.get('input_tokens'):
        parts.append(f"input={token_usage['input_tokens']}")
    if token_usage.get('output_tokens'):
        parts.append(f"output={token_usage['output_tokens']}")
    if token_usage.get('total_tokens'):
        parts.append(f"total={token_usage['total_tokens']}")
    if token_usage.get('reasoning_tokens'):
        parts.append(f"reasoning={token_usage['reasoning_tokens']}")
    if token_usage.get('cached_tokens'):
        parts.append(f"cached={token_usage['cached_tokens']}")
    if not parts:
        return ""
    return f"<!-- Tokens: {', '.join(parts)} -->\n"


def save_memo(output_file: Path, reasoning: str, output: str,
              pdf_name: str, model_id: str, token_usage: dict):
    """Save memo to file."""
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    result = ""
    if reasoning:
        result += '<div style="border: 2px solid #dddddd; border-radius: 10px;">\n'
        result += '  <details open style="padding: 5px;">\n'
        result += '    <summary>已深度思考</summary>\n'
        result += reasoning.replace('\n', '<br>') + '\n'
        result += '  </details>\n'
        result += '</div>\n\n'
    result += output

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"<!-- Paper: {pdf_name} -->\n")
        f.write(f"<!-- Timestamp: {timestamp} -->\n")
        f.write(f"<!-- Model: {model_id} -->\n")
        f.write(format_token_comment(token_usage))
        f.write(f"\n{result}")


def main():
    """
    Process a single PDF with a single model.

    Usage:
        python memo_paper_single.py <pdf_path> <provider> <model_id> [prompt_name] [journal_abbr] [output_dir]

    Args:
        pdf_path: Path to the PDF file
        provider: Provider name (e.g., volcano_engine, siliconflow)
        model_id: Model ID (e.g., doubao-seed-2-0-pro-260215)
        prompt_name: Prompt file name without extension (default: Memo)
        journal_abbr: Journal abbreviation for paper info (default: extracted from path)
        output_dir: Output directory (default: Output/Memo)
    """
    if len(sys.argv) < 4:
        print("Usage: python memo_paper_single.py <pdf_path> <provider> <model_id> [prompt_name] [journal_abbr] [output_dir]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    provider = sys.argv[2]
    model_id = sys.argv[3]
    prompt_name = sys.argv[4] if len(sys.argv) > 4 else "Memo"
    journal_abbr = sys.argv[5] if len(sys.argv) > 5 else None
    output_dir_str = sys.argv[6] if len(sys.argv) > 6 else None

    # Setup
    log_dir = PROJECT_ROOT / "Output" / "Logs"
    logger = setup_logging(log_dir)

    output_dir = Path(output_dir_str) if output_dir_str else PROJECT_ROOT / "Output" / "Memo"
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = str(Path(pdf_path).resolve())
    if not Path(pdf_path).exists():
        logger.error(f"PDF file not found: {pdf_path}")
        sys.exit(1)

    pdf_name = Path(pdf_path).name
    pdf_stem = Path(pdf_path).stem

    # Derive journal_abbr from path if not provided
    if not journal_abbr:
        path_parts = Path(pdf_path).parts
        for part in path_parts:
            if part.startswith("10_"):
                journal_abbr = part.replace("10_", "").split("_")[0]
                break
        if not journal_abbr:
            journal_abbr = "Unknown"

    # Load config
    try:
        config = load_provider_config(provider)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    api_key = get_api_key(config)
    base_url = config["base_url"]

    # Load prompt
    try:
        system_prompt = load_prompt(prompt_name)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    # Get paper info
    author, year = get_paper_info(pdf_path)

    # Check if already processed
    model_suffix = model_id.split("/")[-1] if "/" in model_id else model_id
    output_file = output_dir / f"{pdf_stem}_{model_suffix}.md"

    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.startswith(f"<!-- Error processing") and "## " in content:
            logger.info(f"Already processed: {pdf_name} with {model_id}")
            logger.info(f"Output: {output_file}")
            sys.exit(0)

    logger.info(f"Processing: {pdf_name}")
    logger.info(f"Provider: {provider}, Model: {model_id}")
    logger.info(f"Output: {output_file}")

    # Initialize client
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        http_client=httpx.Client(
            proxy=None,
            trust_env=False,
            timeout=httpx.Timeout(DEFAULT_TIMEOUT, connect=60.0)
        )
    )

    max_retries = DEFAULT_MAX_RETRIES
    retry = 0
    success = False
    file_id = None

    while retry <= max_retries and not success:
        if retry > 0:
            wait_time = min(60 * retry, 180)
            logger.info(f"  Retry {retry}/{max_retries}, waiting {wait_time}s...")
            time.sleep(wait_time)

        try:
            file_id = upload_file(client, pdf_path, logger)
            reasoning, output, token_usage = generate_memo(
                client, model_id, system_prompt,
                file_id, author, year, journal_abbr, logger
            )

            save_memo(output_file, reasoning, output, pdf_name, model_id, token_usage)
            success = True
            logger.info(f"  Done! Saved to: {output_file}")

            # Cleanup
            if file_id:
                try:
                    client.files.delete(file_id)
                    logger.info(f"  Cleaned up file: {file_id}")
                except Exception:
                    pass

        except Exception as e:
            retry += 1
            if file_id:
                try:
                    client.files.delete(file_id)
                except Exception:
                    pass

            error_str = str(e).lower()
            retryable = any(kw in error_str for kw in [
                'timeout', 'timed out', 'rate limit', '429',
                '503', '502', '504', 'connection', 'overloaded'
            ])

            if not retryable or retry > max_retries:
                logger.error(f"  Failed: {e}")
                # Save error marker
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"<!-- Error processing {pdf_name}: {e} -->")

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
