---
name: econ-ref-re
description: "Reconstruct economics paper reference lists from OCR markdown and export cleaned/enriched bibliography deliverables. Use this skill when a user has a paper already processed by PaddleOCR, MinerU, or another OCR pipeline and needs the References section extracted, split-reference artifacts repaired, identifiers resolved through crossref-openalex, and final .md, .json, and .ris files prepared for downstream literature-review, memo, citation, or bibliography tasks."
author: WZM
---

# Economics Reference Rebuilder

## Purpose

Use this skill for paper-specific reference reconstruction after OCR. It owns
OCR markdown parsing, reference-list cleanup, split-reference repair, and
delivery files. It delegates DOI/ISBN/URL lookup to the `crossref-openalex`
infrastructure skill.

## Workflow

1. Locate the paper OCR markdown file.
2. Extract the `References`, `Bibliography`, or `Works Cited` section.
3. Parse references into numbered records.
4. Repair obvious page-break splits.
5. Write the clean arranged reference list.
6. Call `crossref-openalex/scripts/resolve_refs.py` to resolve identifiers.
7. Export Markdown, JSON, and RIS deliverables.
8. Review unmatched and low-score references before using downstream.

## Use The Script

```bash
python path/to/econ-ref-re/scripts/rebuild_refs.py --input paper.md --paper-key MyPaper --title "Paper title" --out-dir Output/MyPaper
```

Useful options:

- `--no-network`: parse and export only existing identifiers.
- `--skip-resolve`: stop after arranged references.
- `--mailto`: CrossRef/OpenAlex contact email; otherwise use `CROSSREF_MAILTO`.
- `--openalex-api-key`: optional; otherwise use `OPENALEX_API_KEY`.
- `--crossref-openalex-script`: explicit resolver path if skills are not installed
  as sibling folders.

## Outputs

The script creates:

```text
<paper-key>_Ref-Arranged.md
<paper-key>_Ref-Arranged.json
<paper-key>_CrossRef.md
<paper-key>_CrossRef.json
<paper-key>_CrossRef-OpenAlex.md
<paper-key>_CrossRef-OpenAlex.json
<paper-key>_CrossRef-OpenAlex.ris
<paper-key>_Ref-Fin.md
<paper-key>_Ref-Fin.json
<paper-key>_Ref-Fin.ris
```

Every Markdown file must contain `## References` and `## Summary`.

## Quality Checks

- Inspect the extracted reference count against the source paper.
- Review merged split references, especially around OCR page boundaries.
- Inspect all `source: not_found` records.
- Inspect low scores near the chosen threshold before treating them as final.
- Prefer DOI over ISBN over URL if multiple identifiers appear.

## References

Read `references/pipeline.md` for parsing heuristics, output schema, and review
guidance when handling difficult OCR results.
