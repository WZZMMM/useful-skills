"""Assemble page Markdown from the raw Paddle result and verify local output."""

import codecs
import html
import json
import re
from pathlib import Path
from urllib.parse import unquote

if __package__:
    from .paddle_appendices import APPENDIX_FORMAT_VERSION, PAGE_START, annotate_appendices, page_marker
    from .paddle_folios import display_page
    from .paddle_footnotes import render_footnotes
else:
    from paddle_appendices import APPENDIX_FORMAT_VERSION, PAGE_START, annotate_appendices, page_marker
    from paddle_folios import display_page
    from paddle_footnotes import render_footnotes


IMAGE = re.compile(
    r'!\[[^\]\n]*\]\(\s*(?:<([^>\n]+)>|([^\s)]+))'
    r"""|<img\b[^>]*?\ssrc\s*=\s*["']([^"']+)""", re.I,
)


def download_raw_results(urls, raw_path: Path, fetch) -> None:
    """Keep complete results, or the downloaded chunks in .part on interruption."""
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    partial = raw_path.with_suffix(raw_path.suffix + ".part")
    with partial.open("wb") as stream:
        for url in urls:
            response = fetch(url)
            response.raise_for_status()
            chunk = response.content.removeprefix(codecs.BOM_UTF8)
            stream.write(chunk)
            if chunk and not chunk.endswith(b"\n"):
                stream.write(b"\n")
    partial.replace(raw_path)


def iter_pages(raw_path: Path):
    with raw_path.open(encoding="utf-8-sig") as stream:
        for line in stream:
            if line.strip():
                yield from json.loads(line)["result"]["layoutParsingResults"]


def source_page_labels(reader) -> list[str] | None:
    """Read optional original PDF navigation labels independently of printed folios."""
    try:
        labels = reader.page_labels
    except Exception:
        # Missing or malformed page-label metadata cannot prevent OCR conversion.
        return None
    return labels if isinstance(labels, list) and all(isinstance(label, str) for label in labels) else None


def render_page(page_result: dict, physical_page: int) -> str:
    layout = page_result.get("prunedResult") or {}
    blocks = layout.get("parsing_res_list") or []
    text, folio = display_page((page_result.get("markdown") or {}).get("text") or "",
                               blocks, layout.get("height"), layout.get("width"))
    text = render_footnotes(text, blocks, physical_page)
    return f"{page_marker(folio)}\n\n{text.strip()}".rstrip()


def validate_markdown(md_path: Path, expected_pages: int) -> None:
    text = md_path.read_text(encoding="utf-8")
    markers = list(PAGE_START.finditer(text))
    if not markers or markers[0].start() != 0 or len(markers) != expected_pages:
        raise ValueError(f"Expected {expected_pages} page-start annotations in {md_path.name}")
    for match in IMAGE.finditer(text):
        target = html.unescape(next(value for value in match.groups() if value is not None))
        image = md_path.parent / unquote(target)
        if not image.is_file() or not image.stat().st_size:
            raise ValueError(f"Unresolved local image in {md_path.name}")
