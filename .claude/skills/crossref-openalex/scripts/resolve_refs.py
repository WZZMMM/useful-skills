#!/usr/bin/env python3
"""Resolve reference identifiers with CrossRef and OpenAlex.

This module is intentionally generic so higher-level skills can import it.
It accepts reference strings or parsed reference records and writes enriched
JSON with DOI, ISBN, URL, OpenAlex ID, match source, and audit fields.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "by", "for", "from", "in", "into",
    "of", "on", "or", "the", "to", "with", "without", "using", "evidence",
}

DOI_RE = re.compile(r"(?:https?://(?:dx\.)?doi\.org/|doi[:\s]*)?(10\.\d{4,9}/[^\s\"'<>]+)", re.I)
ISBN_RE = re.compile(r"\b(?:ISBN(?:-1[03])?[:\s]*)?((?:97[89][-\s]?)?(?:\d[-\s]?){9,12}[\dXx])\b")
URL_RE = re.compile(r"https?://[^\s\"'<>)]+")
YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20[0-4]\d)\b")


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def clean_token_text(value: str) -> str:
    value = strip_accents(value).lower()
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"10\.\d{4,9}/\S+", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return normalize_space(value)


def tokens(value: str) -> set[str]:
    return {tok for tok in clean_token_text(value).split() if len(tok) > 2 and tok not in STOPWORDS}


def title_score(query_title: str, candidate_title: str) -> float:
    query_tokens = tokens(query_title)
    candidate_tokens = tokens(candidate_title)
    if not query_tokens or not candidate_tokens:
        return 0.0
    return len(query_tokens & candidate_tokens) / len(query_tokens)


def first_author(value: str) -> str:
    value = strip_accents(value or "")
    if not value:
        return ""
    match = re.match(r"\s*([A-Za-z][A-Za-z'`\-]+)", value)
    return match.group(1).lower() if match else ""


def author_from_crossref(item: Dict[str, Any]) -> str:
    authors = item.get("author") or []
    if not authors:
        return ""
    family = authors[0].get("family") or ""
    given = authors[0].get("given") or ""
    return normalize_space(f"{family}, {given}".strip(", "))


def author_from_openalex(item: Dict[str, Any]) -> str:
    authorships = item.get("authorships") or []
    if not authorships:
        return ""
    author = authorships[0].get("author") or {}
    return author.get("display_name") or ""


def candidate_year_crossref(item: Dict[str, Any]) -> str:
    for key in ("published-print", "published-online", "issued"):
        parts = ((item.get(key) or {}).get("date-parts") or [])
        if parts and parts[0]:
            return str(parts[0][0])
    return ""


def normalize_doi(value: str) -> str:
    match = DOI_RE.search(value or "")
    if not match:
        return ""
    doi = match.group(1).rstrip(".,;:)]}").lower()
    return f"https://doi.org/{doi}"


def normalize_isbn(value: str) -> str:
    match = ISBN_RE.search(value or "")
    if not match:
        return ""
    return re.sub(r"\s+", "-", match.group(1).strip())


def normalize_url(value: str) -> str:
    match = URL_RE.search(value or "")
    if not match:
        return ""
    return match.group(0).rstrip(".,;:)]}")


def strip_identifiers(value: str) -> str:
    value = DOI_RE.sub(" ", value or "")
    value = ISBN_RE.sub(" ", value)
    value = URL_RE.sub(" ", value)
    return normalize_space(value)


def extract_year(text: str) -> str:
    match = YEAR_RE.search(text or "")
    return match.group(1) if match else ""


def extract_authors(text: str) -> str:
    text = normalize_space(text)
    year = YEAR_RE.search(text)
    if year:
        return text[: year.start()].strip(" .,:;")
    match = re.match(r"(.+?)\.\s+[A-Z][^.]{8,}\.", text)
    return match.group(1).strip() if match else ""


def extract_title(text: str) -> str:
    text = strip_identifiers(normalize_space(text))
    quoted = re.search(r"[\"“]([^\"”]{8,})[\"”]", text)
    if quoted:
        return normalize_space(quoted.group(1))

    year = YEAR_RE.search(text)
    if year:
        after = text[year.end() :].lstrip(" .,:;")
        parts = re.split(r"\.\s+(?=[A-Z0-9])", after)
        if parts and len(parts[0]) >= 8:
            return normalize_space(parts[0].strip(" .,:;"))

    parts = [p.strip() for p in re.split(r"\.\s+", text) if len(p.strip()) >= 8]
    if len(parts) >= 2:
        return normalize_space(parts[1].strip(" .,:;"))
    return normalize_space(parts[0].strip(" .,:;")) if parts else ""


def reference_record(raw: Any, index: int) -> Dict[str, Any]:
    if isinstance(raw, str):
        rec: Dict[str, Any] = {"num": index, "text": raw}
    else:
        rec = dict(raw)
        rec.setdefault("num", rec.get("number", index))
        rec.setdefault("text", rec.get("reference", ""))

    rec["text"] = normalize_space(str(rec.get("text") or ""))
    rec.setdefault("authors", extract_authors(rec["text"]))
    rec.setdefault("title", extract_title(rec["text"]))
    rec.setdefault("year", extract_year(rec["text"]))
    return rec


def load_references(path: Path) -> List[Dict[str, Any]]:
    content = path.read_text(encoding="utf-8")
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            data = data.get("references", [])
        if not isinstance(data, list):
            raise ValueError("JSON input must be a list or an object with references")
        return [reference_record(item, i) for i, item in enumerate(data, 1)]
    except json.JSONDecodeError:
        blocks = [block.strip() for block in re.split(r"\n\s*\n+", content) if block.strip()]
        return [reference_record(block, i) for i, block in enumerate(blocks, 1)]


def http_get_json(url: str, headers: Dict[str, str], timeout: int = 20) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def build_headers(mailto: str) -> Dict[str, str]:
    headers = {"User-Agent": "crossref-openalex-resolver/1.0"}
    if mailto:
        headers["User-Agent"] += f" (mailto:{mailto})"
    return headers


def crossref_candidates(ref: Dict[str, Any], args: argparse.Namespace) -> List[Dict[str, Any]]:
    query = ref.get("title") or strip_identifiers(ref.get("text", ""))
    if not query:
        return []
    params = {
        "query.title": query,
        "rows": str(args.crossref_rows),
        "select": "DOI,title,author,type,published-print,published-online,issued,ISBN,URL",
    }
    if args.mailto:
        params["mailto"] = args.mailto
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    data = http_get_json(url, build_headers(args.mailto), args.timeout)
    return (data.get("message") or {}).get("items") or []


def openalex_candidates(ref: Dict[str, Any], args: argparse.Namespace) -> List[Dict[str, Any]]:
    query = ref.get("title") or strip_identifiers(ref.get("text", ""))
    if not query:
        return []
    params = {"search": query, "per-page": str(args.openalex_per_page)}
    if args.openalex_api_key:
        params["api_key"] = args.openalex_api_key
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    data = http_get_json(url, build_headers(args.mailto), args.timeout)
    return data.get("results") or []


def score_candidate(ref: Dict[str, Any], title: str, author: str, year: str) -> float:
    score = title_score(ref.get("title") or ref.get("text", ""), title)
    if year and ref.get("year") and str(year) == str(ref.get("year")):
        score += 0.08
    if author and ref.get("authors") and first_author(author) == first_author(ref.get("authors", "")):
        score += 0.08
    return min(score, 1.0)


def existing_identifier(ref: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    text = ref.get("text", "")
    doi = normalize_doi(text) or normalize_doi(str(ref.get("doi") or ""))
    isbn = normalize_isbn(text) or normalize_isbn(str(ref.get("isbn") or ""))
    url = normalize_url(text) or normalize_url(str(ref.get("url") or ""))
    if doi:
        return {"doi": doi, "isbn": None, "url": None, "source": "existing_doi", "match_score": 1.0}
    if isbn:
        return {"doi": None, "isbn": isbn, "url": None, "source": "existing_isbn", "match_score": 1.0}
    if url:
        return {"doi": None, "isbn": None, "url": url, "source": "existing_url", "match_score": 1.0}
    return None


def resolve_one(ref: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    out = dict(ref)
    out.setdefault("doi", None)
    out.setdefault("isbn", None)
    out.setdefault("url", None)
    out.setdefault("openalex_id", None)
    out.setdefault("matched_title", None)
    out.setdefault("match_score", 0.0)

    existing = existing_identifier(out)
    if existing:
        out.update(existing)
        return out

    if args.no_network:
        out["source"] = "not_found"
        return out

    try:
        candidates = crossref_candidates(out, args)
        best: Tuple[float, Optional[Dict[str, Any]]] = (0.0, None)
        for item in candidates:
            title = " ".join(item.get("title") or [])
            score = score_candidate(out, title, author_from_crossref(item), candidate_year_crossref(item))
            if score > best[0]:
                best = (score, item)
        if best[1] and best[0] >= args.crossref_threshold and best[1].get("DOI"):
            item = best[1]
            out.update({
                "doi": normalize_doi(item["DOI"]),
                "isbn": None,
                "url": None,
                "source": "crossref",
                "match_score": round(best[0], 3),
                "matched_title": " ".join(item.get("title") or []),
            })
            return out
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        out["crossref_error"] = str(exc)

    time.sleep(args.sleep)

    try:
        candidates = openalex_candidates(out, args)
        best = (0.0, None)
        for item in candidates:
            title = item.get("title") or ""
            score = score_candidate(out, title, author_from_openalex(item), str(item.get("publication_year") or ""))
            if score > best[0]:
                best = (score, item)
        if best[1] and best[0] >= args.openalex_threshold:
            item = best[1]
            openalex_id = item.get("id")
            doi = normalize_doi(item.get("doi") or "")
            out.update({
                "doi": doi or None,
                "isbn": None,
                "url": None if doi else openalex_id,
                "openalex_id": openalex_id,
                "source": "openalex" if doi else "openalex_url",
                "match_score": round(best[0], 3),
                "matched_title": item.get("title"),
            })
            return out
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        out["openalex_error"] = str(exc)

    out["source"] = "not_found"
    return out


def resolve_references(refs: Sequence[Dict[str, Any]], args: argparse.Namespace) -> List[Dict[str, Any]]:
    resolved = []
    for i, ref in enumerate(refs, 1):
        normalized = reference_record(ref, i)
        resolved.append(resolve_one(normalized, args))
        if not args.no_network and i < len(refs):
            time.sleep(args.sleep)
    return resolved


def default_args() -> argparse.Namespace:
    return argparse.Namespace(
        mailto=os.environ.get("CROSSREF_MAILTO", ""),
        openalex_api_key=os.environ.get("OPENALEX_API_KEY", ""),
        crossref_rows=5,
        openalex_per_page=5,
        crossref_threshold=0.55,
        openalex_threshold=0.50,
        sleep=0.4,
        timeout=20,
        no_network=False,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve reference identifiers with CrossRef and OpenAlex.")
    parser.add_argument("--input", required=True, type=Path, help="Input JSON or plain-text reference file.")
    parser.add_argument("--output", required=True, type=Path, help="Output JSON path.")
    parser.add_argument("--mailto", default=os.environ.get("CROSSREF_MAILTO", ""), help="Contact email for polite API use.")
    parser.add_argument("--openalex-api-key", default=os.environ.get("OPENALEX_API_KEY", ""), help="Optional OpenAlex API key.")
    parser.add_argument("--crossref-rows", type=int, default=5)
    parser.add_argument("--openalex-per-page", type=int, default=5)
    parser.add_argument("--crossref-threshold", type=float, default=0.55)
    parser.add_argument("--openalex-threshold", type=float, default=0.50)
    parser.add_argument("--sleep", type=float, default=0.4, help="Seconds between API calls.")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--no-network", action="store_true", help="Only extract identifiers already present in input.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    refs = load_references(args.input)
    resolved = resolve_references(refs, args)
    with_id = sum(1 for r in resolved if r.get("doi") or r.get("isbn") or r.get("url"))
    payload = {
        "source": "crossref-openalex",
        "total_references": len(resolved),
        "references_with_identifier": with_id,
        "references_without_identifier": len(resolved) - with_id,
        "references": resolved,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Resolved {with_id}/{len(resolved)} references -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
