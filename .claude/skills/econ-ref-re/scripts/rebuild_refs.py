#!/usr/bin/env python3
"""Rebuild an economics paper reference list from OCR markdown."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Sequence


REF_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*(references|bibliography|works cited)\b", re.I)
STOP_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*(appendix|acknowledg|supplement|notes)\b", re.I)
NUMBERED_RE = re.compile(r"^\s*(?:\[(\d+)\]|(\d+)[\.)])\s+(.+)")
YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20[0-4]\d)\b")


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def strip_markdown_noise(line: str) -> str:
    line = re.sub(r"<!--.*?-->", " ", line)
    line = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", line)
    line = re.sub(r"^\s*[-*_]{3,}\s*$", " ", line)
    return line.strip()


def extract_reference_section(markdown: str) -> str:
    lines = markdown.splitlines()
    start = None
    for i, line in enumerate(lines):
        if REF_HEADING_RE.match(line):
            start = i + 1
            break
    if start is None:
        raise ValueError("No References/Bibliography/Works Cited heading found.")

    end = len(lines)
    for i in range(start, len(lines)):
        if STOP_HEADING_RE.match(lines[i]):
            end = i
            break
    return "\n".join(lines[start:end]).strip()


def looks_like_reference_start(text: str) -> bool:
    text = normalize_space(text)
    if not text:
        return False
    if NUMBERED_RE.match(text):
        return True
    if re.match(r"[A-Z][A-Za-z'`\-]+,\s*(?:[A-Z]\.|[A-Z][a-z]+)", text) and YEAR_RE.search(text[:160]):
        return True
    if re.match(r"(FAO|IFPRI|OECD|UNCTAD|UNDP|World Bank|WorldBank|USDA|ADB|NBER)\b", text, re.I):
        return bool(YEAR_RE.search(text[:180]))
    return False


def parse_reference_blocks(section: str) -> List[Dict[str, Any]]:
    cleaned_lines = [strip_markdown_noise(line) for line in section.splitlines()]
    cleaned_lines = [line for line in cleaned_lines if line]

    numbered: List[Dict[str, Any]] = []
    current_num: Optional[int] = None
    current_lines: List[str] = []
    saw_numbered = False

    for line in cleaned_lines:
        match = NUMBERED_RE.match(line)
        if match:
            saw_numbered = True
            if current_lines:
                numbered.append({"num": current_num or len(numbered) + 1, "text": normalize_space(" ".join(current_lines))})
            current_num = int(match.group(1) or match.group(2))
            current_lines = [match.group(3)]
        elif saw_numbered and current_lines:
            current_lines.append(line)

    if saw_numbered:
        if current_lines:
            numbered.append({"num": current_num or len(numbered) + 1, "text": normalize_space(" ".join(current_lines))})
        return numbered

    blocks = [normalize_space(block) for block in re.split(r"\n\s*\n+", section) if normalize_space(block)]
    return [{"num": i, "text": block} for i, block in enumerate(blocks, 1)]


def fix_split_references(refs: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], int]:
    fixed: List[Dict[str, Any]] = []
    merges = 0
    for ref in refs:
        text = normalize_space(ref["text"])
        if fixed and not looks_like_reference_start(text):
            fixed[-1]["text"] = normalize_space(fixed[-1]["text"] + " " + text)
            merges += 1
        else:
            fixed.append({"num": len(fixed) + 1, "text": text})
    return fixed, merges


def load_resolver(path: Optional[Path]):
    resolver_path = path
    if resolver_path is None:
        skills_dir = Path(__file__).resolve().parents[2]
        resolver_path = skills_dir / "crossref-openalex" / "scripts" / "resolve_refs.py"
    if not resolver_path.exists():
        raise FileNotFoundError(f"Cannot find crossref-openalex resolver at {resolver_path}")
    spec = importlib.util.spec_from_file_location("crossref_openalex_resolver", resolver_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import resolver from {resolver_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identifier_suffix(ref: Dict[str, Any]) -> str:
    if ref.get("doi"):
        doi = str(ref["doi"]).replace("https://doi.org/", "")
        return f" DOI: [{doi}](https://doi.org/{doi})"
    if ref.get("isbn"):
        return f" ISBN: {ref['isbn']}"
    if ref.get("url"):
        return f" URL: [{ref['url']}]({ref['url']})"
    return ""


def summary_md(version: str, refs: List[Dict[str, Any]], steps: List[str], splits_fixed: int) -> str:
    total = len(refs)
    with_id = sum(1 for r in refs if r.get("doi") or r.get("isbn") or r.get("url"))
    counts: Dict[str, int] = {}
    for ref in refs:
        counts[str(ref.get("source") or "unresolved")] = counts.get(str(ref.get("source") or "unresolved"), 0) + 1

    lines = ["## Summary", "", f"**Version:** {version}", "", "**Process:**"]
    for i, step in enumerate(steps, 1):
        lines.append(f"{i}. {step}")
    lines.extend(["", "**Results:**", "| Metric | Count |", "|--------|-------|", f"| Total references | {total} |"])
    for key in sorted(counts):
        lines.append(f"| {key} | {counts[key]} |")
    pct = (100 * with_id / total) if total else 0
    lines.append(f"| With identifier | {with_id} ({pct:.1f}%) |")
    lines.append(f"| Without identifier | {total - with_id} |")
    lines.append(f"| Split references fixed | {splits_fixed} |")
    unmatched = [r for r in refs if not (r.get("doi") or r.get("isbn") or r.get("url"))]
    if unmatched:
        lines.extend(["", "**References without identifier:**"])
        for ref in unmatched:
            lines.append(f"- #{ref['num']}: {ref['text'][:120]}...")
    lines.extend(["", f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}"])
    return "\n".join(lines)


def write_md(path: Path, title: str, refs: List[Dict[str, Any]], steps: List[str], splits_fixed: int) -> None:
    lines = [f"# {title}", "", "## References", ""]
    for ref in refs:
        lines.append(f"{ref['num']}. {ref['text']}{identifier_suffix(ref)}")
        lines.append("")
    lines.append(summary_md("1.0.0", refs, steps, splits_fixed))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, title: str, refs: List[Dict[str, Any]]) -> None:
    with_id = sum(1 for r in refs if r.get("doi") or r.get("isbn") or r.get("url"))
    payload = {
        "source_paper": title,
        "total_references": len(refs),
        "references_with_identifier": with_id,
        "references_without_identifier": len(refs) - with_id,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "references": refs,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def ris_type(text: str) -> str:
    lower = text.lower()
    if "dissertation" in lower or "thesis" in lower:
        return "THES"
    if "working paper" in lower or "policy research" in lower or "report" in lower:
        return "RPRT"
    if "edited by" in lower or lower.startswith("in ") or " in:" in lower:
        return "CHAP"
    if "university press" in lower:
        return "BOOK"
    if "conference" in lower or "proceeding" in lower:
        return "CONF"
    return "JOUR"


def ris_authors(authors: str) -> List[str]:
    authors = normalize_space(authors)
    if not authors:
        return []
    if ";" in authors:
        return [a.strip(" .") for a in authors.split(";") if a.strip()]
    if " and " in authors:
        return [a.strip(" .") for a in re.split(r"\s+and\s+", authors) if a.strip()]
    return [authors.strip(" .")]


def write_ris(path: Path, refs: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    for ref in refs:
        lines.append(f"TY  - {ris_type(ref.get('text', ''))}")
        for author in ris_authors(ref.get("authors", "")):
            lines.append(f"AU  - {author}")
        if ref.get("title"):
            lines.append(f"TI  - {ref['title']}")
        if ref.get("year"):
            lines.append(f"PY  - {ref['year']}")
        if ref.get("doi"):
            lines.append(f"DO  - {str(ref['doi']).replace('https://doi.org/', '')}")
        if ref.get("url"):
            lines.append(f"UR  - {ref['url']}")
        if ref.get("isbn"):
            lines.append(f"SN  - {ref['isbn']}")
        lines.extend(["ER  - ", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def crossref_only(refs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for ref in refs:
        item = dict(ref)
        if item.get("source") != "crossref":
            item["doi"] = None
            item["isbn"] = None
            item["url"] = None
        out.append(item)
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract and rebuild OCR paper references.")
    parser.add_argument("--input", required=True, type=Path, help="OCR markdown file.")
    parser.add_argument("--paper-key", required=True, help="Filename prefix for outputs.")
    parser.add_argument("--title", required=True, help="Paper title for output headers.")
    parser.add_argument("--out-dir", required=True, type=Path, help="Output directory.")
    parser.add_argument("--crossref-openalex-script", type=Path, default=None)
    parser.add_argument("--mailto", default=os.environ.get("CROSSREF_MAILTO", ""))
    parser.add_argument("--openalex-api-key", default=os.environ.get("OPENALEX_API_KEY", ""))
    parser.add_argument("--crossref-threshold", type=float, default=0.55)
    parser.add_argument("--openalex-threshold", type=float, default=0.50)
    parser.add_argument("--sleep", type=float, default=0.4)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--skip-resolve", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    markdown = args.input.read_text(encoding="utf-8")
    section = extract_reference_section(markdown)
    refs, splits_fixed = fix_split_references(parse_reference_blocks(section))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    arranged_json = args.out_dir / f"{args.paper_key}_Ref-Arranged.json"
    arranged_md = args.out_dir / f"{args.paper_key}_Ref-Arranged.md"
    arranged_json.write_text(json.dumps({"references": refs}, indent=2, ensure_ascii=False), encoding="utf-8")
    write_md(arranged_md, args.title, refs, ["Extracted reference section from OCR markdown.", "Parsed and repaired reference blocks."], splits_fixed)

    if args.skip_resolve:
        print(f"Wrote arranged references only: {len(refs)} references")
        return 0

    resolver = load_resolver(args.crossref_openalex_script)
    resolver_args = SimpleNamespace(
        mailto=args.mailto,
        openalex_api_key=args.openalex_api_key,
        crossref_rows=5,
        openalex_per_page=5,
        crossref_threshold=args.crossref_threshold,
        openalex_threshold=args.openalex_threshold,
        sleep=args.sleep,
        timeout=args.timeout,
        no_network=args.no_network,
    )
    enriched = resolver.resolve_references(refs, resolver_args)

    cr_refs = crossref_only(enriched)
    write_md(args.out_dir / f"{args.paper_key}_CrossRef.md", args.title, cr_refs, ["Resolved references using CrossRef only."], splits_fixed)
    write_json(args.out_dir / f"{args.paper_key}_CrossRef.json", args.title, cr_refs)

    steps = [
        "Extracted reference section from OCR markdown.",
        "Parsed and repaired reference blocks.",
        "Resolved identifiers using CrossRef first and OpenAlex fallback.",
        "Applied DOI > ISBN > URL priority.",
    ]
    for suffix in ("CrossRef-OpenAlex", "Ref-Fin"):
        write_md(args.out_dir / f"{args.paper_key}_{suffix}.md", args.title, enriched, steps, splits_fixed)
        write_json(args.out_dir / f"{args.paper_key}_{suffix}.json", args.title, enriched)
        write_ris(args.out_dir / f"{args.paper_key}_{suffix}.ris", enriched)

    with_id = sum(1 for ref in enriched if ref.get("doi") or ref.get("isbn") or ref.get("url"))
    print(f"Rebuilt {len(enriched)} references; {with_id} with identifiers -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
