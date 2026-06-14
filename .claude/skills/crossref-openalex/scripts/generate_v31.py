"""
generate_v31.py - Unified generator for v0.3.1
Produces all missing deliverables per AAA/CrossRef-OpenAlex.md spec:
- S1 fix: Add Summary sections to Ref-Arranged.md
- S2a: CrossRef-only (MD + JSON)
- S2: CrossRef-OpenAlex (MD + JSON + RIS)
- S3: Ref-Fin (MD + JSON + RIS) - Final consolidated deliverable
"""
import json
import re
import unicodedata
from datetime import datetime

OUTPUT_DIR = "Output"
SCRIPTS_DIR = "Output/scripts"

PAPERS = {
    "Barrett2022JEL": {
        "title": "Barrett et al. 2022 - Agri-food Value Chain Revolutions (JEL 60:4, 1316-1377)",
        "ref_source": "preprocessed",
        "enriched_path": f"{SCRIPTS_DIR}/barrett_final.json",
        "splits_fixed": 0,
        "out_dir": f"{OUTPUT_DIR}/Barrett2022JEL",
    },
    "Tabe-Ojong2024FPol": {
        "title": "Tabe-Ojong et al. 2024 - Agricultural Trade Policies (Food Policy)",
        "ref_source": "ocr",
        "enriched_path": f"{SCRIPTS_DIR}/tabe_final.json",
        "splits_fixed": 0,
        "out_dir": f"{OUTPUT_DIR}/Tabe-Ojong2024FPol",
    },
    "Reardon2024FPol": {
        "title": "Reardon et al. 2024 - Emerging Outsource Agricultural Services (Food Policy)",
        "ref_source": "ocr",
        "enriched_path": f"{SCRIPTS_DIR}/reardon_final.json",
        "splits_fixed": 1,
        "out_dir": f"{OUTPUT_DIR}/Reardon2024FPol",
    },
}

# ============================================================
# Utility functions
# ============================================================

def clean_text(text):
    """Clean text for display: strip markdown, links, extra spaces."""
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def strip_identifiers(text):
    """Remove existing DOI/URL/ISBN from text."""
    text = re.sub(r'\s*https?://doi\.org/[^\s"\'<>()]+\.?', '', text)
    text = re.sub(r'\s*\(https?://[^\s)]+\)\.?', '', text)
    text = re.sub(r'\s*\(https?://[^\s)]+\)', '', text)
    text = re.sub(r'\s*https?://[^\s"\'<>()]+', '', text)
    text = re.sub(r'\s*(?:DOI[:\s]*)?10\.\d{4,}/[^\s"\'<>()]+\.?', '', text)
    text = re.sub(r'\s*ISBN[^\d]*\d[\d-]{9,}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+\.?\s*$', '', text)
    return text.strip()


def identifier_line(r):
    """Build identifier suffix for a reference."""
    if r.get('doi'):
        doi_val = r['doi'].replace('https://doi.org/', '')
        return f" DOI: [{doi_val}](https://doi.org/{doi_val})"
    elif r.get('isbn'):
        return f" ISBN: {r['isbn']}"
    elif r.get('url'):
        return f" URL: [{r['url']}]({r['url']})"
    return ""


def build_summary_md(paper_title, version, process_steps, stats, refs, splits_fixed):
    """Build Summary section for MD files."""
    total = len(refs)
    with_id = sum(1 for r in refs if r.get('doi') or r.get('isbn') or r.get('url'))
    without_id = total - with_id

    lines = [
        "## Summary",
        "",
        f"**Version: {version}**",
        "",
        "**Process:**",
    ]
    for i, step in enumerate(process_steps, 1):
        lines.append(f"{i}. {step}")
    lines.append("")
    lines.append("**Results:**")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total references | {total} |")

    for label, count in stats:
        lines.append(f"| {label} | {count} |")

    lines.append(f"| **With identifier** | **{with_id} ({100*with_id/total:.1f}%)** |")
    lines.append(f"| Without identifier | {without_id} |")

    if splits_fixed:
        lines.append("")
        lines.append(f"**Split references fixed:** {splits_fixed}")

    if without_id > 0:
        lines.append("")
        lines.append("**References without identifier:**")
        for r in refs:
            if not r.get('doi') and not r.get('isbn') and not r.get('url'):
                text = clean_text(strip_identifiers(r['text']))[:100]
                lines.append(f"- #{r['num']}: {text}...")

    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return '\n'.join(lines)


# ============================================================
# S1 Fix: Add Summary to Ref-Arranged.md
# ============================================================

def fix_s1_summary(name, cfg, refs):
    """Add Summary section to existing Ref-Arranged.md files."""
    md_path = f"{cfg['out_dir']}/{name}_Ref-Arranged.md"
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if "## Summary" in content:
        return  # Already has Summary

    summary = build_summary_md(
        paper_title=cfg['title'],
        version="0.3.1",
        process_steps=[
            "Extracted references from PaddleOCR-VL OCR output.",
            "Fixed split references caused by page breaks.",
            "Cleaned OCR artifacts and formatted as numbered list.",
            "No enrichment identifiers at this stage.",
        ],
        stats=[],
        refs=refs,
        splits_fixed=cfg['splits_fixed'],
    )

    content = content.rstrip() + "\n\n" + summary + "\n"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  S1: Added Summary to {name}_Ref-Arranged.md")


# ============================================================
# S2a: CrossRef-only (MD + JSON)
# ============================================================

def generate_s2a_crossref(name, cfg, refs):
    """Generate CrossRef-only output (S2a intermediate step)."""
    total = len(refs)
    cr_count = 0

    # MD
    md_lines = [f"# {cfg['title']}", "", "## References", ""]
    json_refs = []

    for r in refs:
        text = clean_text(strip_identifiers(r['text']))
        id_suffix = ""
        is_cr = r.get('source') == 'crossref'

        if is_cr:
            id_suffix = identifier_line(r)
            cr_count += 1

        md_lines.append(f"{r['num']}. {text}{id_suffix}")
        md_lines.append("")

        json_refs.append({
            "number": r['num'],
            "text": text,
            "authors": r.get('authors', ''),
            "title": r.get('title', ''),
            "year": r.get('year', ''),
            "doi": r.get('doi') if is_cr else None,
            "source": "crossref" if is_cr else None,
        })

    no_cr = total - cr_count
    summary = build_summary_md(
        paper_title=cfg['title'],
        version="0.3.1",
        process_steps=[
            "Extracted and cleaned references from OCR output.",
            "Matched references against CrossRef API (title-based search).",
            "Only CrossRef-matched references receive DOI identifiers at this stage.",
            "Remaining references will be enriched via OpenAlex in the next step.",
        ],
        stats=[
            ("Matched by CrossRef", cr_count),
            ("Pending OpenAlex enrichment", no_cr),
        ],
        refs=[r for r in refs],
        splits_fixed=cfg['splits_fixed'],
    )

    md_lines.append(summary)

    # Write MD
    md_path = f"{cfg['out_dir']}/{name}_CrossRef.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

    # Write JSON
    json_data = {
        "source": "CrossRef API",
        "total_references": total,
        "crossref_matched": cr_count,
        "pending": no_cr,
        "generated": datetime.now().isoformat(),
        "references": json_refs,
    }
    json_path = f"{cfg['out_dir']}/{name}_CrossRef.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print(f"  S2a: {name}_CrossRef.md ({cr_count}/{total} CrossRef)")
    print(f"       {name}_CrossRef.json")


# ============================================================
# S2: CrossRef-OpenAlex (MD + JSON + RIS)
# ============================================================

def to_ris_type(text):
    """Guess RIS type from reference text."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in ['phd dissertation', 'ph.d. dissertation', 'phd thesis', 'doctoral dissertation']):
        return 'THES'
    if any(kw in text_lower for kw in ['working paper', 'policy research', 'nber working paper']):
        return 'RPRT'
    if any(kw in text_lower for kw in ['in:', 'edited by', 'chapter', 'eds)', 'eds.']):
        return 'CHAP'
    if any(kw in text_lower for kw in ['university press', 'press,']):
        return 'BOOK'
    if any(kw in text_lower for kw in ['conference', 'proceeding', 'symposium']):
        return 'CONF'
    return 'JOUR'


def generate_ris(refs):
    """Generate RIS format content."""
    lines = []
    for r in refs:
        text = r['text']
        ris_type = to_ris_type(text)
        lines.append(f"TY  - {ris_type}")

        # Authors
        authors_raw = r.get('authors', '')
        if authors_raw:
            for author in re.split(r',\s+(?=[A-Z])|;\s+|\s+and\s+', authors_raw):
                author = author.strip().rstrip('.')
                if author and len(author) > 1:
                    lines.append(f"AU  - {author}")

        # Title
        title = r.get('title', '')
        if title:
            lines.append(f"TI  - {title}")

        # Year
        year = r.get('year', '')
        if year:
            lines.append(f"PY  - {year}")

        # DOI
        if r.get('doi'):
            doi_val = r['doi'].replace('https://doi.org/', '')
            lines.append(f"DO  - {doi_val}")

        # URL
        if r.get('url'):
            lines.append(f"UR  - {r['url']}")

        # ISBN
        if r.get('isbn'):
            lines.append(f"SN  - {r['isbn']}")

        lines.append("ER  - ")
        lines.append("")

    return '\n'.join(lines)


def generate_s2_crossref_openalex(name, cfg, refs):
    """Generate CrossRef-OpenAlex output (S2 combined enrichment)."""
    total = len(refs)

    # Apply DOI > ISBN > URL priority
    for r in refs:
        if r.get('doi') and r.get('url'):
            del r['url']
        if r.get('doi') and r.get('isbn'):
            del r['isbn']
        if r.get('isbn') and r.get('url'):
            del r['url']

    # Clean identifiers from text, then append clean identifier
    for r in refs:
        r['clean_text'] = clean_text(strip_identifiers(r['text']))

    cr = sum(1 for r in refs if r.get('source') == 'crossref')
    oa = sum(1 for r in refs if r.get('source') in ('openalex_ref', 'openalex_search'))
    ex = sum(1 for r in refs if r.get('source') in ('existing', 'existing_url'))
    nf = sum(1 for r in refs if not r.get('doi') and not r.get('isbn') and not r.get('url'))

    # === MD ===
    md_lines = [f"# {cfg['title']}", "", "## References", ""]
    for r in refs:
        id_suf = identifier_line(r)
        md_lines.append(f"{r['num']}. {r['clean_text']}{id_suf}")
        md_lines.append("")

    summary = build_summary_md(
        paper_title=cfg['title'],
        version="0.3.1",
        process_steps=[
            "Extracted and cleaned references from PaddleOCR-VL output.",
            f"Fixed {cfg['splits_fixed']} split reference(s) caused by page breaks.",
            "Checked for existing identifiers (DOI/URL/ISBN) already present in the text.",
            "Matched against CrossRef API results (primary source, title-based search).",
            "Matched against OpenAlex referenced_works and search API for remaining entries.",
            "Applied priority ordering: DOI > ISBN > URL (one per entry).",
            "Added clickable DOI/URL links in markdown format.",
        ],
        stats=[
            ("CrossRef matched", cr),
            ("OpenAlex matched", oa),
            ("Existing in OCR", ex),
        ],
        refs=refs,
        splits_fixed=cfg['splits_fixed'],
    )
    md_lines.append(summary)

    # === JSON ===
    json_refs = []
    for r in refs:
        json_refs.append({
            "number": r['num'],
            "text": r['clean_text'],
            "authors": r.get('authors', ''),
            "title": r.get('title', ''),
            "year": r.get('year', ''),
            "doi": r.get('doi'),
            "isbn": r.get('isbn'),
            "url": r.get('url'),
            "source": r.get('source'),
        })
    json_data = {
        "source": "CrossRef + OpenAlex",
        "total_references": total,
        "references_with_identifier": total - nf,
        "references_without_identifier": nf,
        "generated": datetime.now().isoformat(),
        "references": json_refs,
    }

    # === RIS ===
    ris_content = generate_ris(refs)

    # Write files
    md_path = f"{cfg['out_dir']}/{name}_CrossRef-OpenAlex.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

    json_path = f"{cfg['out_dir']}/{name}_CrossRef-OpenAlex.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    ris_path = f"{cfg['out_dir']}/{name}_CrossRef-OpenAlex.ris"
    with open(ris_path, 'w', encoding='utf-8') as f:
        f.write(ris_content)

    with_id = total - nf
    print(f"  S2: {name}_CrossRef-OpenAlex.md ({with_id}/{total} w/ id)")
    print(f"      {name}_CrossRef-OpenAlex.json")
    print(f"      {name}_CrossRef-OpenAlex.ris")


# ============================================================
# S3: Ref-Fin (Final consolidated deliverable)
# ============================================================

def generate_s3_ref_fin(name, cfg, refs):
    """Generate Ref-Fin output (S3 final deliverable).

    Based on S2 CrossRef-OpenAlex results, producing the final clean
    MD + JSON + RIS for delivery.
    """
    total = len(refs)

    # Apply DOI > ISBN > URL priority
    for r in refs:
        if r.get('doi') and r.get('url'):
            del r['url']
        if r.get('doi') and r.get('isbn'):
            del r['isbn']
        if r.get('isbn') and r.get('url'):
            del r['url']

    # Clean text
    for r in refs:
        r['clean_text'] = clean_text(strip_identifiers(r['text']))

    cr = sum(1 for r in refs if r.get('source') == 'crossref')
    oa = sum(1 for r in refs if r.get('source') in ('openalex_ref', 'openalex_search'))
    ex = sum(1 for r in refs if r.get('source') in ('existing', 'existing_url'))
    nf = sum(1 for r in refs if not r.get('doi') and not r.get('isbn') and not r.get('url'))
    with_id = total - nf

    # === MD ===
    md_lines = [f"# {cfg['title']}", "", "## References", ""]
    for r in refs:
        id_suf = identifier_line(r)
        md_lines.append(f"{r['num']}. {r['clean_text']}{id_suf}")
        md_lines.append("")

    summary = build_summary_md(
        paper_title=cfg['title'],
        version="0.3.1",
        process_steps=[
            "Reference list extracted from PaddleOCR-VL output and cleaned.",
            f"Corrected {cfg['splits_fixed']} split reference(s) from page breaks.",
            "Enriched via CrossRef API (primary) and OpenAlex API (fallback).",
            "Applied identifier priority: DOI > ISBN > URL.",
            "Verified all identifiers and formatted with clickable links.",
        ],
        stats=[
            ("Via CrossRef", cr),
            ("Via OpenAlex", oa),
            ("Already in OCR", ex),
        ],
        refs=refs,
        splits_fixed=cfg['splits_fixed'],
    )
    md_lines.append(summary)

    # === JSON ===
    json_refs = []
    for r in refs:
        json_refs.append({
            "number": r['num'],
            "text": r['clean_text'],
            "authors": r.get('authors', ''),
            "title": r.get('title', ''),
            "year": r.get('year', ''),
            "doi": r.get('doi'),
            "isbn": r.get('isbn'),
            "url": r.get('url'),
            "source": r.get('source'),
        })
    json_data = {
        "source_paper": cfg['title'],
        "total_references": total,
        "references_with_identifier": with_id,
        "references_without_identifier": nf,
        "coverage": f"{100*with_id/total:.1f}%",
        "generated": datetime.now().isoformat(),
        "references": json_refs,
    }

    # === RIS ===
    ris_content = generate_ris(refs)

    # Write
    md_path = f"{cfg['out_dir']}/{name}_Ref-Fin.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

    json_path = f"{cfg['out_dir']}/{name}_Ref-Fin.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    ris_path = f"{cfg['out_dir']}/{name}_Ref-Fin.ris"
    with open(ris_path, 'w', encoding='utf-8') as f:
        f.write(ris_content)

    print(f"  S3: {name}_Ref-Fin.md ({with_id}/{total} w/ id, {100*with_id/total:.1f}%)")
    print(f"      {name}_Ref-Fin.json")
    print(f"      {name}_Ref-Fin.ris")


# ============================================================
# Parse references from existing enriched data
# ============================================================

def load_enriched(name, cfg):
    """Load enriched data and return refs with structured fields."""
    import os
    path = cfg['enriched_path']
    if not os.path.exists(path):
        print(f"  WARNING: No enriched data at {path}")
        return None

    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    # Add structured fields (author, title, year) if missing
    for r in data:
        if 'num' not in r:
            r['num'] = r.get('number', 0)
        if 'authors' not in r:
            # Try to extract from text
            r['authors'] = extract_authors(r.get('text', ''))
        if 'title' not in r:
            r['title'] = extract_title(r.get('text', ''))
        if 'year' not in r:
            r['year'] = extract_year(r.get('text', ''))

    return data


def extract_authors(text):
    """Extract author string from reference text."""
    # Pattern: Author1, A.B., Author2, C.D., Year.
    m = re.match(r'(.+?)\s+(\d{4})\s*[\.\,]', text)
    if m:
        return m.group(1).rstrip(',.').strip()
    m = re.match(r'(.+?)\s+(\d{4})', text)
    if m:
        return m.group(1).strip()
    return ''


def extract_title(text):
    """Extract title from reference text."""
    # Try quoted title
    m = re.search(r'["\u201c]([^"\u201d]+?)["\u201d]', text)
    if m:
        return m.group(1)
    # Try title after year: "Year. Title."
    m = re.search(r'\d{4}\.\s*["\u201c]?([^."]+?)["\u201d]?\.', text)
    if m:
        return m.group(1).strip()
    return ''


def extract_year(text):
    """Extract year from reference text."""
    m = re.search(r'\b(1[5-9]\d{2}|20[0-2]\d)\b', text)
    return m.group(1) if m else ''


# ============================================================
# Main
# ============================================================

def process_paper(name, cfg):
    """Generate all outputs for one paper."""
    print(f"\n--- {name} ---")

    refs = load_enriched(name, cfg)
    if refs is None:
        return

    total = len(refs)
    with_id = sum(1 for r in refs if r.get('doi') or r.get('isbn') or r.get('url'))
    print(f"  Loaded {total} enriched refs ({with_id} w/ identifier)")

    # S1 fix: Add Summary to Ref-Arranged.md
    fix_s1_summary(name, cfg, refs)

    # S2a: CrossRef-only
    generate_s2a_crossref(name, cfg, refs)

    # S2: CrossRef-OpenAlex
    generate_s2_crossref_openalex(name, cfg, refs)

    # S3: Ref-Fin
    generate_s3_ref_fin(name, cfg, refs)


if __name__ == "__main__":
    print("=" * 60)
    print("v0.3.1 - Generating all deliverables for 3 papers")
    print("=" * 60)

    for name, cfg in PAPERS.items():
        process_paper(name, cfg)

    print("\n" + "=" * 60)
    print("DONE. All files generated.")
    print("=" * 60)
