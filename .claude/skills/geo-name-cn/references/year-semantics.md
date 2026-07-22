# Year-parameter semantics

## Scope

The administrative-division endpoint and the place-name endpoints do not share one uniform year model. Treat their results separately. The observations below were reproduced on 2026-07-19 and may change when the service is updated.

## Administrative divisions: `/xzqh/getList`

### What the official site states

The official interface chapter describes `year` only as an optional integer and says omission selects the latest edition. It publishes no lower bound, upper bound, or list of available historical editions.

The current website does not expose a year selector. `common/baseUrl.js` assigns `year: 0`, and `js/search.js` copies that value into requests. The official administrative-code publication page uses the internal table name `Xzqh20251231` and states that the displayed data are current through 2025-12-31.

### Boundary A/B

All comparisons below used the full national tree (`code=00&maxLevel=3`) and canonical response hashes.

| `year` input | Observed result |
|---|---|
| omitted | Current response, exactly equal to requested `2025` |
| `0`, `-1` | Current response |
| `2026`, `9999` | Silently returns the current response |
| empty string, `abc`, `2012.0` | HTTP 400 |
| whitespace-wrapped ` 2012 ` | Parsed as integer `2012` |
| `1948`, `1949`, `2011` | The same oldest observed fallback bucket |
| `1` | Unstable: a shallow probe once returned the fallback bucket, while the full-tree probe returned HTTP 500 |

The parameter is therefore syntactically integer-like, but the official site supplies no contractual numeric range. For reproducible edition selection, describe only `2012–2025` as the empirically effective selector interval. Even within that interval, several years are aliases and none should be assumed historically faithful without an external comparison. The tested boundary values `0`, `-1`, `2026`, and `9999` selected current data; do not generalize those observations to every negative or post-2025 integer. Very low positive values are not stable.

### Complete request-year bucket map

The 77 requests from 1949 through 2025 produced only 10 distinct national-tree responses:

| Requested year(s) | Province | Prefecture | County | Interpretation |
|---|---:|---:|---:|---|
| 1949–2011 | 34 | 331 | 2,744 | One shared fallback/baseline response |
| 2012 | 34 | 332 | 2,756 | One response |
| 2013–2017 | 34 | 333 | 2,780 | One shared response |
| 2018–2019 | 34 | 333 | 2,808 | One shared response |
| 2020 | 34 | 333 | 2,824 | One response |
| 2021 | 34 | 333 | 2,841 | One response |
| 2022 | 34 | 333 | 2,842 | One response |
| 2023 | 34 | 333 | 2,844 | One response |
| 2024 | 34 | 333 | 2,848 | One response |
| 2025 | 34 | 333 | 2,846 | Current response |

The shared `1949–2011` response contains names such as 密云区, 延庆区, 蓟州区, 崇明区, and 龙港市. Those names make a 1949 interpretation impossible. Treat every file labelled 1949–2024 in this experiment as request evidence, not as a historical panel observation.

### External MCA comparison

Compare six-digit code-name pairs rather than counts alone. Against the local Ministry of Civil Affairs 1980–2023 series, the API buckets were generally closest to the 2021/2022 code-name set. Selected Jaccard results:

| Requested year | Same-year MCA | Best 2021/2022 comparison | Gap |
|---:|---:|---:|---:|
| 2011 | 0.836527 | 0.967300 | 0.130773 |
| 2012 | 0.839768 | 0.971348 | 0.131581 |
| 2017 | 0.953360 | 0.979134 | 0.025774 |
| 2019 | 0.980161 | 0.987854 | 0.007693 |
| 2020 | 0.992528 | 0.992837 | 0.000309 |
| 2021 | 0.998131 | 0.998131 | 0 |
| 2022 | 0.997821 | 0.997821 | 0 |
| 2023 | 0.979038 | 0.997200 | 0.018162 |

The sources are not perfectly coextensive: for example, the local 2011/2012 MCA tables contain 31 province-level units, while every API response contains 34. Use similarity only to diagnose clear date mismatch, not as an official equivalence rate. The combination of identical hashes, anachronistic names, and large same-year similarity gaps demonstrates that the early responses are not faithful historical editions.

### Safe use

- Use the 2025/current response for current administrative divisions and label its 2025-12-31 cutoff.
- Preserve both requested year and canonical response hash in every historical probe.
- Collapse identical hashes into response editions before analysis.
- Never build a historical panel directly from filenames that contain request years.
- Use annual MCA tables and formal change notices for historical administrative divisions.

This document embeds the complete observed bucket map, boundary classifications, selected similarity values, and safe-use conclusions, so understanding and using the skill does not depend on project-external scripts or data. `sources.md` separately lists optional project-local audit artifacts for provenance.

## Place-name search and details

`/stname/listPub` and `/stname/detailsPub` have different year behavior from `/xzqh/getList`:

- Omitted year or `year=0` selects the unlabelled current snapshot.
- Explicit `2025` can return HTTP 500 even though `0` returns current data.
- A search result `id` is snapshot-bound. Send the same effective year to the details request; a mismatched year can return JSON `null`.
- A structural HTTP-200 response proves endpoint responsiveness, not historical fidelity. Classify probes as `responsive_nonempty`, `responsive_empty`, or `unavailable_or_inconclusive` and retain canonical record hashes.
- Probe township category `215` separately from autonomous-area categories `2161` and `2162`; support and emptiness may differ by category.

Historical place-name candidates must be independently probed and should never inherit the administrative-tree bucket map.

### Complete 1999–2024 probe result

The bounded matrix covered 26 requested years, Beijing and a prefecture-level city, and categories `215`, `2161`, and `2162`: 156 combinations in total, each retried up to four times.

| Requested year(s) | Township `215` | Autonomous `2161` / `2162` | Interpretation |
|---|---|---|---|
| 2014, 2018, 2020, 2021, 2022 | Nonempty in both regions | Nonempty in both regions | Responsive snapshot candidates only |
| 2016 | Nonempty in both regions | Structured empty (`total=0`) in both regions | Anomalous partial snapshot; the probe county in a prefecture-level city has only 3 township anchor records |
| Other years in 1999–2024 | Unavailable or inconclusive after four attempts | Unavailable or inconclusive after four attempts | Do not record as zero observations |

This matrix establishes endpoint behavior, not temporal fidelity. A nonempty response may still be incomplete, bucketed, or anachronistic. Preserve the requested year, category, region, response status, total, canonical record hash, and same-snapshot detail closure before using any candidate.

### Full-collection fingerprint audit

The completed collection covered 26 place-name snapshots and 72 pairwise comparisons. For both township and autonomous-organization tasks, and for both Beijing and a prefecture-level city:

- requested `2020` and `2021` were identical in search-ID sets, semantic search tuples, detail-core hashes, and full-detail hashes;
- requested `2022` and the unlabelled `year=0` current snapshot (stored under the 2025 task label with an explicit effective-year marker) were likewise identical in all four fingerprints.

This is evidence of aliases or unchanged responses within the tested scopes, not proof that every region or category shares those aliases. A further caution comes from Beijing autonomous organizations: the `2014` and `2018` search records, including IDs and full record payloads, were identical, while the full detail payload hashes differed. Therefore:

- record counts alone are insufficient;
- an identical search ID set or search payload is still insufficient to establish identical details;
- bind details to the requested search year even when IDs happen to be stable;
- retain both core and full hashes for searches and details.

A machine-readable project audit (JSON plus CSV) contains the tested-scope labels needed to prevent global overgeneralization.
