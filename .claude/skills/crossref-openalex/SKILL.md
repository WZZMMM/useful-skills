---
name: crossref-openalex
description: "Resolve bibliographic references to persistent identifiers using CrossRef and OpenAlex. Use this skill when Codex needs infrastructure-level DOI, ISBN, URL, or OpenAlex Work ID lookup for raw reference strings, parsed reference JSON, paper titles, bibliography entries, or another skill's reference-enrichment step. This skill does not parse OCR papers or generate paper-specific reference deliverables; use econ-ref-re for economics paper OCR reference reconstruction."
author: WZM
---

# CrossRef-OpenAlex Identifier Resolver

## Purpose

Use this skill as a reusable infrastructure layer for reference identifier lookup.
It accepts raw or lightly parsed references and returns structured records with
the best available persistent identifier.

Identifier priority is always:

1. DOI
2. ISBN
3. URL or OpenAlex Work URL

## Use The Script

Prefer the bundled script for repeatable work:

```bash
python path/to/crossref-openalex/scripts/resolve_refs.py --input refs.json --output refs.resolved.json
```

Inputs may be:

- A JSON list of references.
- A JSON object with a `references` list.
- A plain text file where references are separated by blank lines.

Recommended reference shape:

```json
{
  "num": 1,
  "text": "Smith, J. 2020. Paper title. Journal.",
  "authors": "Smith, J.",
  "title": "Paper title",
  "year": "2020"
}
```

The script can infer `authors`, `title`, and `year` from `text` when absent,
but parsed fields improve matching quality.

## Environment

Set a contact email for polite API use:

```bash
set CROSSREF_MAILTO=you@example.com
```

Optional:

```bash
set OPENALEX_API_KEY=...
```

Never hardcode API keys or private email addresses in a skill, script, or
project file. Pass them through environment variables or CLI flags.

## Output Contract

The resolver writes JSON:

```json
{
  "source": "crossref-openalex",
  "references": [
    {
      "num": 1,
      "text": "...",
      "authors": "...",
      "title": "...",
      "year": "2020",
      "doi": "https://doi.org/10.xxxx/yyyy",
      "isbn": null,
      "url": null,
      "openalex_id": null,
      "source": "crossref",
      "match_score": 0.92,
      "matched_title": "Paper title"
    }
  ]
}
```

Valid `source` values include `existing_doi`, `existing_isbn`,
`existing_url`, `crossref`, `openalex`, `openalex_url`, and `not_found`.

## Matching Rules

- Extract existing DOI, ISBN, and URL before querying APIs.
- Query CrossRef first because DOI metadata is the preferred identifier source.
- Query OpenAlex only when no DOI/ISBN/URL has been found.
- Score candidate titles by normalized token overlap.
- Apply small bonuses when candidate year and first author agree.
- Keep `matched_title`, `match_score`, and candidate metadata for auditability.
- Treat low-score matches as unresolved unless the user explicitly asks for a
  more aggressive recall-oriented run.

## API Reference

Read `references/api_reference.md` when you need endpoint details, response
fields, rate-limit notes, or troubleshooting guidance.

## Relationship To Other Skills

This skill should stay generic. It should not assume economics papers, OCR
section headings, RIS exports, or a specific output directory layout. Higher
level skills such as `econ-ref-re` should call this resolver and own those
paper-specific decisions.
