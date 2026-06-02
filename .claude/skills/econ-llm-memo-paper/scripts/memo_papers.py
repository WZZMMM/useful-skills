"""
Memo Papers Orchestrator - Process multiple PDF files with multiple LLM models.
Manages concurrency, tracks progress, and dispatches to worker script.

Usage:
    python memo_papers.py --help
    python memo_papers.py paper1.pdf paper2.pdf --model volcano_engine/doubao-seed-2-0-pro-260215
    python memo_papers.py *.pdf --model volcano_engine/doubao-seed-2-0-pro-260215 siliconflow/deepseek-r1
    python memo_papers.py --list-providers
    python memo_papers.py --list-models
"""

import os
import sys
import time
import json
import argparse
import glob
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional


PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SKILL_DIR = Path(__file__).parent
REFERENCES_DIR = SKILL_DIR.parent / "references"
SCRIPTS_DIR = SKILL_DIR
LOGS_DIR = PROJECT_ROOT / "Output" / "Logs"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "Memo"

DEFAULT_MAX_CONCURRENT = 8
DEFAULT_WAIT = 5  # seconds between launching tasks


@dataclass
class ModelSpec:
    provider: str
    model_id: str

    @property
    def display(self) -> str:
        return f"{self.provider}/{self.model_id}"

    @property
    def suffix(self) -> str:
        return self.model_id.split("/")[-1]


@dataclass
class TaskResult:
    pdf_path: str
    model: ModelSpec
    success: bool
    duration: float = 0
    error: str = ""


def load_provider_configs() -> dict:
    """Load all provider configurations."""
    providers = {}
    for config_file in REFERENCES_DIR.glob("*_config.json"):
        provider_name = config_file.stem.replace("_config", "")
        with open(config_file, "r", encoding="utf-8") as f:
            providers[provider_name] = json.load(f)
    return providers


def list_providers(providers: dict):
    """Print available providers."""
    print("\nAvailable Providers:")
    print("=" * 50)
    for name, config in providers.items():
        api_key_set = bool(os.environ.get(config.get("api_key_env", "")))
        print(f"  {name:20s}  API Key: {'[set]' if api_key_set else '[NOT set]'}")
        print(f"    Base URL: {config.get('base_url', 'N/A')}")
    print()


def list_models(providers: dict):
    """Print available models."""
    print("\nAvailable Models:")
    print("=" * 50)
    for provider, config in providers.items():
        api_key_set = bool(os.environ.get(config.get("api_key_env", "")))
        print(f"\n  {provider} {'[API Key: set]' if api_key_set else '[API Key: NOT set]'}")
        models = config.get("models", {})
        default = config.get("default_model")
        for key, model_cfg in models.items():
            model_id = model_cfg.get("model_id", key)
            is_default = " (default)" if key == default else ""
            print(f"    {model_id}{is_default}")
    print()


def parse_model_specs(model_args: List[str], providers: dict) -> List[ModelSpec]:
    """
    Parse model specifications from command line arguments.
    Format: provider/model_id or provider (uses default model)
    """
    specs = []
    for arg in model_args:
        if "/" in arg:
            provider, model_id = arg.split("/", 1)
            provider = provider.strip()
            model_id = model_id.strip()
        else:
            provider = arg.strip()
            if provider not in providers:
                print(f"[ERROR] Unknown provider: {provider}")
                continue
            model_key = providers[provider].get("default_model")
            if model_key and "models" in providers[provider]:
                model_id = providers[provider]["models"][model_key].get("model_id", model_key)
            else:
                print(f"[ERROR] No default model for provider: {provider}")
                continue

        if provider not in providers:
            print(f"[ERROR] Unknown provider: {provider}")
            continue

        specs.append(ModelSpec(provider=provider, model_id=model_id))

    return specs


def resolve_pdf_files(file_args: List[str]) -> List[str]:
    """
    Resolve file arguments, expanding globs and validating existence.
    """
    files = []
    for arg in file_args:
        expanded = glob.glob(arg)
        if expanded:
            files.extend(expanded)
        elif Path(arg).exists():
            files.append(arg)
        else:
            print(f"[WARNING] File/glob not found: {arg}")

    # Deduplicate and sort
    seen = set()
    unique_files = []
    for f in files:
        abs_path = str(Path(f).resolve())
        if abs_path not in seen:
            seen.add(abs_path)
            unique_files.append(abs_path)

    return sorted(unique_files)


def run_single_task(pdf_path: str, model: ModelSpec, prompt_name: str,
                    journal_abbr: str, output_dir: Path) -> TaskResult:
    """Run a single paper-model task via subprocess."""
    start = time.time()
    pdf_name = Path(pdf_path).name
    pdf_stem = Path(pdf_path).stem

    # Check if already processed
    output_file = output_dir / f"{pdf_stem}_{model.suffix}.md"
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.startswith(f"<!-- Error processing") and "## " in content:
            return TaskResult(
                pdf_path=pdf_path, model=model, success=True,
                duration=0, error="Already processed"
            )

    worker_script = SCRIPTS_DIR / "memo_paper_single.py"

    cmd = [
        sys.executable, str(worker_script),
        pdf_path,
        model.provider,
        model.model_id,
        prompt_name,
        journal_abbr,
        str(output_dir)
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        duration = time.time() - start

        if result.returncode == 0:
            return TaskResult(
                pdf_path=pdf_path, model=model, success=True,
                duration=duration
            )
        else:
            error_msg = result.stderr.strip()[-500:] if result.stderr else "Unknown error"
            return TaskResult(
                pdf_path=pdf_path, model=model, success=False,
                duration=duration, error=error_msg
            )

    except Exception as e:
        duration = time.time() - start
        return TaskResult(
            pdf_path=pdf_path, model=model, success=False,
            duration=duration, error=str(e)
        )


def derive_journal_abbr(pdf_path: str) -> str:
    """Try to derive journal abbreviation from the file path."""
    path = Path(pdf_path)
    for part in path.parts:
        if part.startswith("10_"):
            return part.replace("10_", "").split("_")[0]
    # Try to find any known journal abbreviation
    known_journals = [
        "QJE", "RES", "AER", "ECTA", "JPE", "EJ", "REST", "JEEA",
        "CER", "JDE", "WD", "FPol", "AJAE", "JEEM", "JPubE",
        "JUE", "JPopE", "JLE", "JEBO"
    ]
    for part in path.parts:
        for j in known_journals:
            if j in part.upper():
                return j
    return "Unknown"


def run_orchestrator(pdf_files: List[str], models: List[ModelSpec],
                     prompt_name: str, max_concurrent: int,
                     wait_between: float):
    """Run all paper-model combinations with concurrency control."""

    # Ensure output dirs exist
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build task list
    tasks = []
    for pdf_path in pdf_files:
        journal_abbr = derive_journal_abbr(pdf_path)
        for model in models:
            tasks.append((pdf_path, model, journal_abbr))

    total_tasks = len(tasks)
    if total_tasks == 0:
        print("No tasks to run.")
        return

    # Summary
    print("\n" + "=" * 60)
    print("  Memo Papers Orchestrator")
    print("=" * 60)
    print(f"  Papers:     {len(pdf_files)}")
    print(f"  Models:     {len(models)}")
    for m in models:
        print(f"    - {m.display}")
    print(f"  Total tasks: {total_tasks}")
    print(f"  Concurrency: {max_concurrent}")
    print(f"  Prompt:      {prompt_name}")
    print(f"  Output dir:  {OUTPUT_DIR}")
    print("=" * 60)

    # Run tasks
    results = []
    completed = 0
    failed = 0
    skipped = 0
    lock = threading.Lock()

    def task_callback(task_idx, pdf_path, model, journal_abbr):
        nonlocal completed, failed, skipped

        task_num = task_idx + 1
        pdf_name = Path(pdf_path).name

        with lock:
            print(f"\n[{task_num}/{total_tasks}] Starting: {pdf_name} x {model.model_id}")

        result = run_single_task(pdf_path, model, prompt_name, journal_abbr, OUTPUT_DIR)

        with lock:
            if result.error == "Already processed":
                skipped += 1
                print(f"[{task_num}/{total_tasks}] Skipped (already processed): {pdf_name} x {model.model_id}")
            elif result.success:
                completed += 1
                print(f"[{task_num}/{total_tasks}] Done ({result.duration:.0f}s): {pdf_name} x {model.model_id}")
            else:
                failed += 1
                print(f"[{task_num}/{total_tasks}] FAILED: {pdf_name} x {model.model_id}")
                print(f"  Error: {result.error[:200]}")

        results.append(result)

    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = []
        for task_idx, (pdf_path, model, journal_abbr) in enumerate(tasks):
            future = executor.submit(task_callback, task_idx, pdf_path, model, journal_abbr)
            futures.append(future)
            # Small delay to avoid overwhelming the API
            if wait_between > 0:
                time.sleep(wait_between)

        # Wait for all to complete
        for future in as_completed(futures):
            future.result()  # Re-raise any exceptions

    # Final summary
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Completed:  {completed}")
    print(f"  Failed:     {failed}")
    print(f"  Skipped:    {skipped}")
    print(f"  Output dir: {OUTPUT_DIR}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Process multiple PDF papers with multiple LLM models to generate memos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s paper1.pdf paper2.pdf --model volcano_engine/doubao-seed-2-0-pro-260215
  %(prog)s "E:/papers/*.pdf" --model volcano_engine siliconflow
  %(prog)s --list-models
  %(prog)s --list-providers
  %(prog)s paper.pdf --model volcano_engine/doubao-seed-2-0-pro --prompt Memo --concurrent 4
        """
    )

    parser.add_argument("files", nargs="*", help="PDF file paths or glob patterns")
    parser.add_argument("--model", nargs="+", dest="models",
                       help="Model specs: provider/model_id or just provider (uses default)")
    parser.add_argument("--prompt", default="Memo", help="Prompt name (default: Memo)")
    parser.add_argument("--concurrent", type=int, default=DEFAULT_MAX_CONCURRENT,
                       help=f"Max concurrent tasks (default: {DEFAULT_MAX_CONCURRENT})")
    parser.add_argument("--wait", type=float, default=DEFAULT_WAIT,
                       help=f"Seconds between launching tasks (default: {DEFAULT_WAIT})")
    parser.add_argument("--list-providers", action="store_true",
                       help="List available providers")
    parser.add_argument("--list-models", action="store_true",
                       help="List available models")

    args = parser.parse_args()

    providers = load_provider_configs()

    if args.list_providers:
        list_providers(providers)
        return

    if args.list_models:
        list_models(providers)
        return

    # Validate inputs
    if not args.files:
        parser.error("At least one PDF file is required.")

    if not args.models:
        parser.error("At least one model is required. Use --list-models to see available options.")

    pdf_files = resolve_pdf_files(args.files)
    if not pdf_files:
        print("[ERROR] No PDF files found.")
        sys.exit(1)

    print(f"\nFound {len(pdf_files)} PDF files:")
    for f in pdf_files:
        print(f"  {f}")

    model_specs = parse_model_specs(args.models, providers)
    if not model_specs:
        print("[ERROR] No valid model specifications.")
        sys.exit(1)

    # Check API keys
    missing_keys = []
    for model in model_specs:
        config = providers[model.provider]
        env_var = config.get("api_key_env", "")
        if not os.environ.get(env_var):
            missing_keys.append(f"{env_var} (for {model.provider})")

    if missing_keys:
        print("\n[WARNING] Missing API keys:")
        for key in missing_keys:
            print(f"  - {key}")
        print("Set them as environment variables before running.")
        sys.exit(1)

    run_orchestrator(pdf_files, model_specs, args.prompt, args.concurrent, args.wait)


if __name__ == "__main__":
    main()
