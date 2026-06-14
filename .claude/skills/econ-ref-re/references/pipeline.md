# Econ Reference Reconstruction Pipeline

## Input Expectations

The input should be markdown created from a paper PDF by OCR or PDF extraction.
The paper should contain a recognizable heading such as:

- `References`
- `Bibliography`
- `Works Cited`

If the OCR output has no heading, manually isolate the reference section before
running the script.

## Parsing Heuristics

The parser first looks for numbered references such as:

```text
1. Author. Year. Title.
[2] Author. Year. Title.
```

If numbering is absent, it falls back to blank-line separated blocks. It then
merges likely split blocks when a block does not look like a new reference
start.

Reference starts are detected by year and author-like patterns, including
personal names, hyphenated names, apostrophes, and common institutional authors.

## Enrichment

`econ-ref-re` does not implement API lookup itself. It imports or executes the
resolver in the sibling `crossref-openalex` skill. Keep API keys and email
addresses in environment variables:

```text
CROSSREF_MAILTO
OPENALEX_API_KEY
```

## Output Review

Before using the bibliography downstream:

- Compare total reference count with the source paper.
- Review any record whose `source` is `not_found`.
- Review low-confidence matches near the threshold.
- Confirm that book/report references without DOI received an ISBN or stable URL
  only when one is actually available.
- Confirm RIS author fields if importing into a citation manager.
