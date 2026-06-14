# CrossRef & OpenAlex API Reference

## CrossRef API

### Works Search
```
GET https://api.crossref.org/works?query=<query>&mailto=<email>&select=DOI,title,author,type&rows=5
```

**Parameters:**
- `query`: URL-encoded reference title or search string
- `mailto`: Registered email for polite pool (higher rate limit)
- `select`: Comma-separated fields to return (reduces response size)
- `rows`: Number of results (default 20, max 1000)

**Response:**
```json
{
  "status": "ok",
  "message": {
    "items": [
      {
        "DOI": "10.1257/jel.20201539",
        "title": ["Paper Title"],
        "author": [{"family": "Smith", "given": "J."}],
        "type": "journal-article"
      }
    ]
  }
}
```

**Rate Limits:**
- Without mailto: ~50 requests/minute (shared pool)
- With mailto: significantly higher (polite pool)

### Title Extraction for Query
Clean the reference text to extract just the title portion:
- Remove author names, year, journal name, volume/pages
- Use the longest contiguous title-like segment
- Strip punctuation and special characters

### Word Overlap Scoring
```python
def word_overlap(query_title, result_title):
    query_words = set(query_title.lower().split())
    result_words = set(result_title.lower().split())
    if not query_words:
        return 0
    return len(query_words & result_words) / len(query_words)
```

**Threshold:** >0.25 for CrossRef matching

---

## OpenAlex API

### Works Search
```
GET https://api.openalex.org/works?search=<query>&per-page=3
```

**Parameters:**
- `search`: URL-encoded title (OpenAlex handles semantic search)
- `per-page`: Number of results (default 25, max 200)
- `api_key`: Optional, set via `OPENALEX_API_KEY` env var for higher limits

**Headers:**
```
User-Agent: mailto:your@email.com
```

**Response:**
```json
{
  "results": [
    {
      "id": "https://openalex.org/W3121596959",
      "doi": "https://doi.org/10.1257/jel.20201539",
      "title": "Paper Title",
      "type": "journal-article",
      "primary_location": {
        "source": {
          "id": "https://openalex.org/S12345",
          "url": "https://example.com/journal"
        }
      },
      "publication_year": 2022
    }
  ]
}
```

### Referenced Works
```
GET https://api.openalex.org/works/<openalex_id>
```

Returns full work metadata including `referenced_works` array (list of OpenAlex IDs).

### Word Overlap Scoring for OpenAlex
```python
def word_overlap(query_title, result_title):
    query_words = set(query_title.lower().split())
    result_words = set(result_title.lower().split())
    if not query_words:
        return 0
    return len(query_words & result_words) / len(query_words)
```

**Threshold:** >0.15 for OpenAlex matching (lower than CrossRef due to semantic search)

---

## Enrichment Pipeline Logic

### Identifier Priority
For each reference, use only one identifier: **DOI > ISBN > URL**

### Step Order
1. Check reference text for existing DOI/ISBN/URL
2. Query CrossRef API with title
3. Score results by word overlap (>0.25)
4. If no CrossRef match, query OpenAlex search
5. Score OpenAlex results (>0.15)
6. If no direct match, try shortened/more specific OpenAlex queries
7. Fall back to OpenAlex work URL as identifier

### Source Values
- `crossref` - Matched via CrossRef API
- `openalex_search` - Matched via OpenAlex search
- `openalex_ref` - Matched via pre-fetched OpenAlex referenced_works
- `existing` - DOI/ISBN/URL already in OCR text
- `existing_url` - URL already in OCR text
- `existing_isbn` - ISBN already in OCR text
- `null` - Not found

---

## Common Pitfalls

### Unicode Normalization
Author names with accents must be normalized before comparison:
```python
import unicodedata
normalized = unicodedata.normalize('NFKD', name)
```

### Split References
Page breaks can split a single reference across two pages. Look for:
- Reference ending mid-sentence (no period, no author name)
- Next block starting without an author name pattern
- Merge consecutive blocks where the second lacks an author start

### False Positive Regex
When detecting new reference starts, require the "LastName, Initial" pattern:
```python
# Good: requires comma + capital letter
re.match(r'[A-Za-z]+,\s*[A-Z]', line)
# Bad: matches any word followed by space
re.match(r'[A-Za-z]+[,\s]', line)  # Matches "Markets " as false positive
```

### Organizational Authors
Single-word organization names (e.g., "FAO.", "ADB.", "WorldBank.") need fallback regex:
```python
re.match(r'([A-Za-z]+)\s*[\.,]', text)
```

### API Rate Limiting
- Add `time.sleep(0.5)` between requests
- Use `mailto` parameter for CrossRef polite pool
- Set `OPENALEX_API_KEY` env var for OpenAlex higher limits
