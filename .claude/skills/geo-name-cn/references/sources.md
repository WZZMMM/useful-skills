# Sources and precedence

## Primary official sources

Accessed 2026-07-19.

1. Ministry of Civil Affairs, China National Database for Geographical Names, [Interface Service](https://dmfw.mca.gov.cn/interface.html). Treat this as the primary public API documentation.
2. Official embedded chapters under `https://dmfw.mca.gov.cn/baseHtmls/docfile/_1.htm` through `_8.htm`: overview; administrative-division search; place-name search; details; same-name-by-division; same-name-by-type; same-pinyin-by-division; same-pinyin-by-type.
3. Official frontend [category definition](https://dmfw.mca.gov.cn/base/jquery.category.js). Use this only to fill the interface document's missing category-code enumeration.
4. Official frontend [search implementation](https://dmfw.mca.gov.cn/js/search.js?v=20251201) and [detail implementation](https://dmfw.mca.gov.cn/js/detail.js?v=20251201). Use these to interpret the live website's form encoding, `year=0`, and UI parameter values; do not let them override the published `/9095` endpoint contract without an API A/B test.
5. Official frontend [base URL configuration](https://dmfw.mca.gov.cn/common/baseUrl.js), which sets `year: 0`, and the current [Administrative Division Code publication page](https://dmfw.mca.gov.cn/XzqhVersionPublish.html), whose internal table is `Xzqh20251231` and whose notice states a 2025-12-31 cutoff.

## Community references

Accessed from the user-supplied archives on 2026-07-19. Use these as implementation leads only; resolve disagreements through official sources and reproducible probes.

1. linyshdhhcb, [china-geonames-skill](https://github.com/linyshdhhcb/china-geonames-skill). The README declares the MIT License. It summarizes the seven official endpoints but does not test category codes, snapshots, pagination, or failure behavior.
2. linyshdhhcb, [mcp-china-geonames-server](https://github.com/linyshdhhcb/mcp-china-geonames-server). The README declares the MIT License. It wraps the same seven endpoints with `requests` and MCP.

## Material corrections to community examples

- Send details as form-encoded POST. The MCP server sends `json={"id": ...}`; the live `/9095` endpoint returned HTTP 400 for that form on 2026-07-19.
- Add timeouts, retries, pacing, HTTP checks, body-status checks, pagination, deduplication, and checkpointing.
- Normalize true exact matching to `精确`. The live website UI submits `精确匹配`, but the `/9095` A/B test treated that value as fuzzy.
- Keep IDs bound to snapshot years and handle JSON `null`.
- Avoid assuming `year` is honored uniformly across endpoints.

## Evidence log

The skill is operationally self-contained: its client and tests do not import or call any project-external script, and the substantive API findings are embedded in `api-reference.md` and `year-semantics.md`.

The original project run produced optional provenance logs and data files covering: limited endpoint probes (including four-way `searchType` A/B totals and canonical record hashes); bounded empty-name A/B tests; the official-page evidence, full-tree boundary A/B, 77-request/10-response map, and same-year-versus-MCA similarity audit; the complete 1999–2024, 156-combination category-specific place-name year probe; offline and independent client tests; and the 26-snapshot/72-pair place-search versus detail fingerprint comparison. These records are not runtime or documentation dependencies. Re-run the fault-tolerant probe before relying on behavior after a material service update.
