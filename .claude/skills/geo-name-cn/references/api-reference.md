# API reference and observed behavior

## Contents

1. Scope and conventions
2. Administrative-division search
3. Year-parameter semantics
4. Place-name search
5. Place details
6. Statistical endpoints
7. Category codes
8. Batch recipes
9. Verified limitations

## 1. Scope and conventions

Use base URL `https://dmfw.mca.gov.cn/9095`. Treat the official interface chapters as normative for endpoint names and documented fields. Treat the observations below as reproducible behavior seen on 2026-07-19, not as a stability guarantee.

Interpret all returned geographic coordinates as CGCS2000 longitude/latitude. Preserve the original JSON because record fields and administrative-code lengths differ between snapshots.

## 2. Administrative-division search

`GET /xzqh/getList`

| Parameter | Official documentation | Observed behavior |
|---|---|---|
| `year` | Optional integer; latest if omitted; no documented range | The frontend fixes it to `0`. Full-tree A/B found current aliases, invalid textual values, unstable extreme low values, and only 10 responses for 77 requested years. See `year-semantics.md`; do not interpret request years as historical editions. |
| `code` | Optional string | Required in practice for reliable calls. Omitting it produced HTTP 500. Use `00` for the national root; all-zero variants normalize to `00`. Prefixes and 12-digit returned codes both work. |
| `maxLevel` | Required integer, documented `0`–`2` | `1` and `2` work. Root `00` with `0` produced HTTP 500. Undocumented `3` worked on 2026-07-19. |

Ignore the current website's separate `maxdeep` parameter when calling `/9095`; `/9095` ignored it and used its default depth. Use the documented camel-case `maxLevel`.

Read `data` as a single root object, despite the official response table describing `Object[]`. Recurse through lowercase `children`. Use returned `level` rather than tree depth to classify divisions.

Observed current national root with `code=00&maxLevel=3`:

| Measure | Count |
|---|---:|
| Returned `level=1` | 34 |
| Returned `level=2` | 333 |
| Returned `level=3` | 2,846 |
| Tree depth 1 | 34 |
| Tree depth 2 | 451 |
| Tree depth 3 | 2,728 |

Explain the count difference by 118 county-level units appearing at tree depth 2 under municipalities or directly administered structures. Avoid parsers that inspect only one fixed depth.

Prefer the robust three-level strategy:

1. Request `code=00&maxLevel=1`.
2. Extract every returned `level=1` code.
3. Request each province code with `maxLevel=2`.
4. Flatten recursively and keep returned levels 1–3.
5. Deduplicate by full returned code and reject code/name or code/level conflicts.
6. Cross-check the unique code set against `code=00&maxLevel=3` without treating either request as proof of historical coverage.

The response exposes `code`, `name`, `level`, `type`, and `children`, plus top-level `message`, `status`, and `total`.

## 3. Year-parameter semantics

Read `references/year-semantics.md` before requesting historical data. It records the complete 10-bucket map, boundary-value A/B, current frontend behavior, anachronistic-name checks, and the external MCA comparison. The safe rule is: current administrative data may use the 2025/current response; historical administrative data must come from annual MCA files and formal change notices, not from request-year filenames produced by this endpoint.

## 4. Place-name search

`GET /stname/listPub` is the official method. The website also submits form-encoded POST and `/9095` accepted both in a small A/B test. Use GET to follow the interface specification.

| Parameter | Requirement and safe value | Observed behavior |
|---|---|---|
| `stName` | Name or category anchor | Use a complete standard name or bounded keyword for direct searches. Empty strings can fail over broad or missing regions, but both GET and form-encoded POST succeeded with identical responses as full-category anchors when paired with a narrow six-digit county code and `placeTypeCode`; fetch every page and verify unique IDs against `total`, then fall back to keywords on failure or inconsistency. |
| `placeTypeCode` | Optional category code | Category prefixes such as `215`, `2161`, and `2162` work; returned records use five-digit codes `21500`, `21610`, `21620`. |
| `year` | Optional integer | Omitted or `0` selects an unlabelled current snapshot. The full probe found `2014`, `2018`, `2020`, `2021`, and `2022` nonempty across both test regions and all three categories; `2016` was partially responsive and anomalous. These are responsive candidates, not verified historical editions. Explicit `2025` produced HTTP 500. Probe all other years. |
| `searchType` | Official values `精确` or `模糊` | Only `精确` triggered exact matching. Normalize UI labels before sending. |
| `code` | Optional administrative code | Use the narrowest region: 2-digit province, 4-digit prefecture, 6-digit county, or observed 9-digit township in the current snapshot. Broad province queries may time out or return HTTP 500. |
| `page` | Optional integer | Use 1-based pages. Page 0 aliased page 1 in a small test; do not rely on it. |
| `size` | Optional integer | Sizes 1, 5, 100, and 1,000 worked on a 17-record result. Size 0 behaved as 1. Use 100 conservatively and loop to `total`. |

Exact-match A/B on the same request (`stName=东华门`, `placeTypeCode=215`, `code=110101`, `year=2018`) produced:

| `searchType` sent | `total` | Interpretation |
|---|---:|---|
| `精确` | 0 | True exact match |
| `精确匹配` | 1 | Treated as fuzzy; returned `东华门街道` |
| `模糊` | 1 | Fuzzy |
| `模糊匹配` | 1 | Treated as fuzzy |

Consult the probe log's `record_hash` fields for canonical SHA-256 A/B evidence. The client maps `精确匹配` to `精确` to preserve user intent rather than reproduce the website UI bug.

Expect `records`, `total`, and record fields including `id`, `place_code`, `standard_name`, `ethnic_minorities_writing`, `place_type`, `place_type_code`, `province_name`, `city_name`, `area_name`, `province`, `city`, `area`, and GeoJSON-like `gdm`.

Bind every `id` to the exact year mode used for its search. The current and historical search for `故宫博物院` returned different IDs.

## 5. Place details

`POST /stname/detailsPub`

Send `application/x-www-form-urlencoded` data containing `id`; include `year` even though the official parameter table omits it when reading a historical snapshot. The official website also sends form data and adds `year`.

Do not send JSON. A JSON body derived from the community MCP implementation produced HTTP 400. A form body with a matching ID and year returned an object.

Keep the detail year equal to the search year mode:

- Use omitted year or `0` with IDs from the current search.
- For any responsive candidate (`2014`, `2016`, `2018`, `2020`, `2021`, or `2022` in the tested matrix), use only IDs from the exact same requested-year search; the candidate's presence does not establish historical fidelity.
- Treat JSON `null` as a version mismatch or missing record, not as successful empty detail.

Expect the official documented fields plus observed `multimedia_info` and `pdm`: `area_name`, `city_name`, `old_name`, `ethnic_minorities_writing`, `gdm`, `government_history`, `id`, `place_code`, `place_history`, `place_meaning`, `place_origin`, `place_type`, `place_type_code`, `province_name`, `roman_alphabet_spelling`, `standard_name`, `area`, `city`, and `province`.

## 6. Statistical endpoints

All four use GET:

| Operation | Path | Parameters |
|---|---|---|
| Same name by division | `/datastatis/GroupCountNameByCode` | Required `name`; optional `distCode` |
| Same name by category | `/datastatis/GroupCountNameByType` | Required `name`, `distCode` |
| Same pinyin by division | `/datastatis/GroupCountPinyinByCode` | Required romanized `name`; optional `distCode` |
| Same pinyin by category | `/datastatis/GroupCountPinyinByType` | Required romanized `name`, `distCode` |

Use the detail record's exact `roman_alphabet_spelling`, including tone marks and spacing, for same-pinyin queries. Missing `distCode` on either by-type endpoint returned a body with `status=400`, message `区划代码为空或不合法，注意大小写`, and HTTP 200. Validate both HTTP and body status.

The prose mentions a selected year, but the parameter tables omit `year`. Do not pass undocumented `year` to statistics without an isolated probe; treat these endpoints as current-snapshot statistics by default.

## 7. Category codes

Derive these selectors from the official site's `base/jquery.category.js`; verify them against returned five-digit codes.

| Category | Request prefix | Returned code |
|---|---:|---:|
| Province-level administrative region | `212` | `21200` |
| Prefecture-level administrative region | `213` | `21300` |
| County-level administrative region | `214` | `21400` |
| Township-level administrative region | `215` | `21500` |
| Autonomous-organization area | `216` | children below |
| Administrative village | `2161` | `21610` |
| Community | `2162` | `21620` |

Use the official category script for other codes rather than guessing or extrapolating zero padding.

## 8. Batch recipes

### County details

1. Build the current province-prefecture-county table by the province-first strategy.
2. Search each county's standard name with category `214`, exact mode, and the narrowest code context.
3. Require exact standard name and compatible administrative context.
4. Score code compatibility using `area`, then `place_code` prefix, then `city`/`province`.
5. Fetch details only after a unique candidate remains.
6. Save zero-match and multiple-match cases separately; do not choose the first result.

### Township names and details

1. Split by county code.
2. Probe category `215` with an empty name as a full-category anchor; fetch every page and verify unique IDs against `total`.
3. Cross-check with `乡`, `镇`, `街道`, `地区`, and `苏木` in fuzzy mode, or use them as fallbacks if the anchor fails.
4. Deduplicate by `id`; retain anchor and keyword provenance.
5. Compare current results against the division tree's returned `level=4` nodes when available.
6. Resolve missing names individually with exact searches.

### Villages and communities

1. Split by township code when the current result supplies a 9-digit `area`.
2. Search `村` under category `2161` and `社区` under category `2162`.
3. Split overloaded queries more finely after a timeout or HTTP 500.
4. Preserve all pages and deduplicate by `id`.

### Checkpoints

Write an atomic manifest after each completed page. Key each entry by snapshot, endpoint, normalized parameters, and page. Record raw-file path, SHA-256, retrieval time, HTTP status, service status, reported total, returned count, and unique IDs. Resume only after verifying both the file and hash. Keep rate limits configurable and avoid hard-coded request or sample budgets.

## 9. Verified limitations

- Treat public-service HTTP 500 as ambiguous server failure, invalid snapshot, overly broad query, or invalid empty input; preserve response metadata and narrow the request.
- Treat `xzqh` calendar years as request selectors, not historical labels. The official range is undocumented; collapse identical hashes, use `year-semantics.md`, and reject the 1949–2011 files as historical observations.
- Treat the current search snapshot as unlabelled; do not name it `2025` merely because it was retrieved in 2026 or requested for a 2025 task.
- In the 156-combination place-name probe, `2014`, `2018`, `2020`, `2021`, and `2022` were nonempty for both tested regions and all three tested categories. `2016` was nonempty only for township category `215`; both autonomous-area categories returned structured empty responses in both regions, and the probe county in a prefecture-level city returned only three township anchor records. Treat these only as responsive snapshot candidates, not verified faithful historical editions.
- Compare search and detail fingerprints separately. Across the two tested tasks and two tested regions, `2020=2021` and explicit `2022=year=0 current` for search-ID sets, semantic search tuples, detail-core hashes, and full-detail hashes. Beijing autonomous search records were identical in `2014` and `2018`, but full details differed. Scope every equality claim to the tested region and category.
- Expect current records to use observed 9-digit `area` for township context while historical records may use 6-digit county `area`.
- Avoid national keyword searches for high-frequency suffixes; use administrative partitioning.
- Preserve full raw responses and explicitly report coverage gaps.
