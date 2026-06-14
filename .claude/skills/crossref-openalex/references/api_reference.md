# CrossRef And OpenAlex Resolver Reference

## CrossRef

Endpoint:

```text
GET https://api.crossref.org/works
```

Useful query parameters:

- `query.title`: title-focused search string.
- `query.bibliographic`: fallback search using the whole reference string.
- `mailto`: contact email for polite API pool.
- `select`: reduce payload, e.g. `DOI,title,author,type,published-print,published-online,issued,ISBN,URL`.
- `rows`: keep small, usually 5.

Preferred lookup order:

1. Search with parsed title if available.
2. Fall back to a cleaned bibliographic query.
3. Accept a result only if title score passes threshold and DOI exists.

Normalize DOI output to `https://doi.org/<doi>`.

## OpenAlex

Endpoint:

```text
GET https://api.openalex.org/works
```

Useful query parameters:

- `search`: title or shortened reference query.
- `per-page`: keep small, usually 3 to 5.
- `api_key`: optional API key from `OPENALEX_API_KEY`.

Headers:

```text
User-Agent: mailto:you@example.com
```

OpenAlex may return:

- `doi`: use as DOI when present.
- `id`: use as `openalex_id`.
- `primary_location.landing_page_url`: possible URL fallback.
- `title`, `publication_year`, `authorships`: useful for scoring.

When no DOI is available but the title match is strong, use the work URL
`https://openalex.org/W...` as the URL identifier.

## Scoring

Use normalized token overlap:

```python
score = len(query_tokens & candidate_tokens) / len(query_tokens)
```

Remove punctuation, accents, and common stopwords. Add small bonuses for exact
year match and first-author match, but cap final score at 1.0.

Recommended defaults:

- CrossRef threshold: `0.55`
- OpenAlex threshold: `0.50`

Lower thresholds increase recall but need manual review.

## Common Failure Modes

- OCR has split one reference across pages.
- Title extraction stops at an abbreviation such as `U.S.` or `Ph.D.`.
- Books, policy reports, and older working papers have no DOI.
- Translated titles and institutional authors reduce token overlap.
- A search result is the cited article's container, not the cited work.

For high-stakes bibliographies, inspect unresolved and low-score matches before
using the exported references downstream.
