---
name: crossref-openalex
description: "Comprehensive use of CrossRef and OpenAlex to convert a paper's reference list into uniquely-identified .md, .json, and .ris files. This skill should be used when a user has a paper's references extracted from OCR (PaddleOCR, MinerU, etc.) in markdown format and needs them enriched with DOI, ISBN, URL identifiers, structured into numbered lists, and exported in RIS and JSON formats. The pipeline produces multiple deliverables: cleaned reference lists (Ref-Arranged), CrossRef-only enrichment (CrossRef), combined CrossRef+OpenAlex enrichment (CrossRef-OpenAlex), and final polished deliverables (Ref-Fin). Prerequisite: the source paper's references must already be converted to markdown via PDF OCR (PaddleOCR-VL, MinerU, or similar tools). This skill handles the enrichment and formatting pipeline, not the OCR step."
author: WZM
---

# CrossRef-OpenAlex Reference Enrichment

## Overview

This skill converts a paper's OCR-extracted reference list (markdown) into structured, uniquely-identified deliverables in `.md`, `.json`, and `.ris` formats.

**Prerequisite**: The source paper's PDF must already be converted to markdown containing a "References" section.

**Identifiers**: DOI is the primary identifier. Books use ISBN. Preprints, reports, and in-press works use URL (including OpenAlex work URLs).

## Pipeline Stages

The pipeline produces multiple deliverables per paper, organized into four stages:

| Stage | Suffix | Description |
|-------|--------|-------------|
| S1 | `_Ref-Arranged` | Cleaned, numbered reference list (no identifiers) |
| S2a | `_CrossRef` | CrossRef-only enrichment (intermediate) |
| S2 | `_CrossRef-OpenAlex` | Combined CrossRef + OpenAlex enrichment |
| S3 | `_Ref-Fin` | Final consolidated deliverable |

Each stage generates `.md` (readable) and `.json` (structured). S2 and S3 also generate `.ris` (bibliographic export).

## Core Script

The main script `scripts/generate_v31.py` handles all stages. Run it to produce
all deliverables from pre-enriched JSON data.

### Script Usage

```bash
cd "path/to/project"
python -X utf8 Output/scripts/generate_v31.py
```

### Configuration

The script reads paper configurations from `PAPERS` dict:

```python
PAPERS = {
    "PaperName": {
        "title": "Full paper title for headers",
        "ref_source": "preprocessed" | "ocr",
        "enriched_path": "path/to/enriched_data.json",
        "splits_fixed": 0,
        "out_dir": "Output/PaperName",
    },
}
```

Each entry points to an `*_final.json` enriched data file produced by the enrichment pipeline (see below).

## Enrichment Pipeline

Before running `generate_v31.py`, each paper's references must be enriched with CrossRef and OpenAlex identifiers. The enrichment process:

### Step 1: Parse References

Extract references from the OCR markdown. References start after "## References".
Each reference is a block separated by blank lines. For preprocessed files with numbered lists, parse the numbered format.

### Step 2: Fix Split References

Check for references split across page boundaries. Common pattern: a reference ends mid-sentence at the bottom of one page, and continues at the top of the next page without an author name starting the new block.

Merge such splits before enrichment.

### Step 3: CrossRef Enrichment

For each reference:

1. Check for existing DOI/ISBN/URL already in the reference text.
2. If none found, query CrossRef API with the reference title.
3. Score results by word overlap (>0.25 threshold).
4. Store matched DOI.

CrossRef API endpoint:
```
https://api.crossref.org/works?query=<query>&mailto=<email>&select=DOI,title,author,type&rows=5
```

### Step 4: OpenAlex Enrichment

For references not matched by CrossRef:

1. Query OpenAlex search API with the reference title.
2. Score results by word overlap (>0.25 threshold).
3. If no direct match, search OpenAlex for the work by title to get its OpenAlex ID and use that as a URL identifier.
4. For books/reports not found via search, try direct title search in OpenAlex with shorter, more specific queries.

OpenAlex API endpoint:
```
https://api.openalex.org/works?search=<query>&per-page=3
```

### Step 5: Save Enriched Data

Save enriched data as JSON:
```json
[
  {
    "num": 1,
    "text": "Author, A. 2020. Title. Journal.",
    "doi": "https://doi.org/10.xxxx/xxx",
    "isbn": null,
    "url": null,
    "source": "crossref"
  }
]
```

Source values: `crossref`, `openalex_search`, `openalex_ref`, `existing`,
`existing_url`, `existing_isbn`, or `null` (not found).

## DOI Format in Output

All output uses clickable markdown links:
```
 DOI: [10.1257/jel.20201539](https://doi.org/10.1257/jel.20201539)
```

For books with ISBN:
```
 ISBN: 978-0-262-06253-0
```

For works without DOI (reports, preprints):
```
 URL: [https://openalex.org/W1234567](https://openalex.org/W1234567)
```

## Identifier Priority

When a reference has multiple identifiers, use only one:
**DOI > ISBN > URL**

## Required User Inputs

The script requires two pieces of user-provided information:

1. **Email address** (`MAILTO`): Used in CrossRef API requests for rate-limit polite pool. User must provide their registered email.
   
2. **OpenAlex API Key**: If available, set the environment variable `OPENALEX_API_KEY`. The script reads it via `os.environ.get()`.
   **Never hardcode API keys in the script.**

## Author Key Extraction

The matching algorithm extracts first author names using regex patterns:

1. Apostrophe names: `D'Odorico`, `D'Amico`
2. Hyphenated names: `Liverpool-Tasie`, `Gonzalez-Navarro`
3. Standard format: `Smith, J.`
4. Organizational authors: `ADB.`, `FAO.`, `WorldBank.` (single-word fallback)

Author names are Unicode-normalized (NFKD) to strip accents before comparison.

## Word Overlap Matching

Title matching uses word overlap scoring:
```
score = len(common_words) / len(title_words)
```
Threshold: >0.15 for initial matching, >0.25 for CrossRef/OpenAlex search.

## Output Directory Structure

All outputs for each paper are placed in a subdirectory:
```
Output/
  PaperName/
    PaperName_Ref-Arranged.md      # S1: Cleaned refs
    PaperName_Ref-Arranged.json    # S1: Structured refs
    PaperName_CrossRef.md          # S2a: CrossRef-only
    PaperName_CrossRef.json        # S2a: CrossRef-only
    PaperName_CrossRef-OpenAlex.md # S2: Combined
    PaperName_CrossRef-OpenAlex.json
    PaperName_CrossRef-OpenAlex.ris
    PaperName_Ref-Fin.md           # S3: Final
    PaperName_Ref-Fin.json
    PaperName_Ref-Fin.ris
```

## RIS Type Mapping

References are mapped to RIS types based on content:
- `THES` - PhD dissertations
- `RPRT` - Working papers, policy reports
- `CHAP` - Book chapters (contains "In:", "edited by")
- `BOOK` - Books (contains "University Press")
- `JOUR` - Journal articles (default)
- `CONF` - Conference proceedings

## Common Unmatched References

The following types of references typically cannot be matched:
- Books published before widespread DOI adoption
- In-press book chapters
- Government agency reports
- Policy briefs without formal publication
- Conference presentations without proceedings

For these, try OpenAlex title search with shortened, more specific queries.
If truly no DOI/ISBN/URL exists, note them in the Summary section.

## Summary Section

Every output .md file must include both `## References` and `## Summary` sections.
The Summary should document:
- Version number
- Process steps taken
- Match statistics (CrossRef, OpenAlex, Existing counts)
- List of any unmatched references
- Generation timestamp



