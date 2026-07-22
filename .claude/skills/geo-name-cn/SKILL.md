---
name: geo-name-cn
description: This skill should be used to query, batch-download, validate, and preserve data from China's National Database for Geographical Names public API, including administrative-division trees, place-name searches, category-filtered township/village retrieval, ID-based details, statistics, historical snapshot probes, pagination, checkpointing, and provenance.
author: WZM
---

# China National Geographical Names API

## Start safely

Read [references/api-reference.md](references/api-reference.md) before making network requests. Read [references/sources.md](references/sources.md) before citing the service or community implementations.

Use `scripts/geo_name_cn.py` instead of rewriting HTTP calls. Run `python scripts/geo_name_cn.py --dry-run ...` before a new batch. Preserve complete raw JSON before flattening or filtering.

## Select a snapshot

Handle snapshot semantics separately by endpoint. For `/xzqh/getList`, a calendar `year` can select an older or bucketed administrative tree, but it does not establish one faithful edition per requested year: a 1949–2025 probe produced only 10 distinct national-tree hashes, including one shared by 1949–2011. Preserve both the requested year and response hash, compare known boundaries against an external official series, and never call repeated responses independent annual editions.

For `/stname/listPub`, treat omitted `year` or `year=0` as the service's unlabelled current snapshot. A 156-combination probe found `2014`, `2018`, `2020`, `2021`, and `2022` nonempty for both tested regions and all three tested categories. It found `2016` only partially responsive: township `215` was nonempty, but `2161` and `2162` were structured empty responses in both regions, and the probe county in a prefecture-level city had only three township anchor records. Treat all of them as responsive candidates, not verified faithful historical editions; probe other years before scheduling work. Never relabel a current response as a requested calendar year.

Fingerprint the search records and details separately. In the tested township/autonomous categories for Beijing and a prefecture-level city, `2020` equalled `2021`, and explicit `2022` equalled the unlabelled `year=0` current snapshot, across search IDs, semantic search fields, and full details. Beijing autonomous-area search records were also identical in `2014` and `2018`, while their detail payloads differed. Do not infer an independent edition from a request year, and do not generalize these regional findings to the whole service.

Keep every search `id` bound to its search year. Pass that same year to `details`; reject `null` as a snapshot mismatch.

## Retrieve administrative divisions

Use `three-levels` to retrieve province, prefecture, and county rows. Prefer the script's province-first strategy: get `code=00&maxLevel=1`, request each province with `maxLevel=2`, deduplicate by returned code, reject code/name conflicts, and cross-check against the root tree.

Do not equate tree depth with the returned `level`. Count both, because municipalities and directly administered counties skip a tree layer.

Example:

```bash
python scripts/geo_name_cn.py three-levels --json divisions.json --csv divisions.csv
```

## Search names and fetch details

For a direct name query, supply a non-empty `stName`. For exhaustive category retrieval under a narrow six-digit county code, first probe an empty `stName` together with `placeTypeCode`, fetch every page, and verify the returned unique count against `total`; this combination succeeded in county-level tests even though empty-name requests over broad or missing regions can fail with HTTP 500. Fall back to bounded keywords when the category anchor fails or is inconsistent. Use `searchType=精确` for true exact matching and `searchType=模糊` for substring matching. Let the client normalize `exact`, `fuzzy`, `精确匹配`, and `模糊匹配` to the backend-safe values.

Resolve county details by searching each administrative-tree standard name with category `214`, the same snapshot, and the narrowest usable administrative code. Match the candidate's `standard_name`, `place_type_code`, `area`, `city`, `province`, and `place_code` prefix against the target. Fetch details only for a unique candidate; retain ambiguity records for review.

Send detail requests as form-encoded POST data. Do not send JSON bodies.

## Retrieve township and autonomous-organization names

Split broad work into bounded regions. For each county, try an empty-name category anchor first, paginate it completely, and verify `total`; use `乡`, `镇`, `街道`, `地区`, and `苏木` as cross-checks or fallback queries. Deduplicate by `id`, retain query provenance, and verify suffix-independent coverage against the current administrative tree where available.

Search administrative-village category `2161` with `村` and community category `2162` with `社区`. Prefer township-level codes for village work; split further when a regional query returns HTTP 500 or times out.

Persist one raw response per region, keyword, page, and snapshot. Maintain a checkpoint manifest containing request parameters, completed pages, response hash, total, unique-ID count, and error. Resume by skipping only entries whose raw file and hash both validate. Set `--min-interval` from service behavior; do not hard-code an arbitrary sample budget.

Example:

```bash
python scripts/geo_name_cn.py search-keywords --keywords 乡 镇 街道 地区 苏木 --place-type-code 215 --code 110101 --json townships.json
```

## Use statistics cautiously

Use the four named statistic operations exposed by `stats`. Supply `dist_code` for both by-type operations. Pass the detail endpoint's diacritic-bearing `roman_alphabet_spelling` to same-pinyin operations. Treat a service-level `status` other than `200` as failure even when HTTP status is `200`.

## Validate every batch

Record the effective base URL, endpoint, method, parameters, retrieval timestamp, HTTP status, service status, raw byte count, SHA-256 hash, and code version. Check pagination totals against unique IDs. Check administrative codes for duplicate conflicts. Check detail IDs against their search snapshot. Report unsupported years and server errors as evidence, not as empty data.

Run the offline suite before reuse:

```bash
python scripts/test_geo_name_cn.py
```
