---
name: econ-pre
description: "Complete agentic workflow for preparing economics paper presentation materials: paper reading, memo routing, author research, LaTeX beamer slides via econ-slides-beamer, Chinese speaker notes as DOCX via the docx skill, optional extensions, and optional referee reports via econ-top5-referee. Use when the user asks to prepare presentation materials, slides, memos, speaker notes, Word/DOCX speaking notes, or a combined presentation/referee package for an economics paper."
author: WZM
---

# Econ Pre

Orchestrate the complete economics paper presentation workflow with context-protecting subagents and explicit file outputs, following the execution discipline of `do-agent`.

## Execution Mode

Run: explore -> think -> plan -> track -> execute -> review -> revise -> deliver.

At the start, get the current Beijing date/time and create a temporary workspace:

`agent_tasks/{short_task_description}_yyyyddmmhh/`

If the folder exists, create a non-overwriting variant. The first local output must be:

`agent_tasks/{short_task_description}_yyyyddmmhh/plan.md`

The plan must include at least four phases:

1. information collection and workflow planning
2. implementation and integration
3. review and feedback on outputs
4. revision based on review feedback

Do not ask the user to approve the plan. Ask only for missing facts that block execution, such as an absent paper path or unspecified presenter identity when it cannot be inferred.

## Subagent Rules

Use parallel subagents where tasks are separable. Give each subagent explicit input files and output files. Each subagent must save complete results locally and return only a brief status summary. Do not paste full subagent outputs into the main context.

Suitable parallel tasks include:

- paper-structure extraction
- memo drafting or memo variants
- author background research
- figure/table inventory
- slide outline review
- speaker-note review
- referee reports when requested

Use no more than 10 subagents in a stage unless the user explicitly asks for a broader run.

## Pre-Flight Check

Explore the project directory and verify:

- paper text or PDF in `Input/papers/` or a user-provided path
- figures/tables in `Output/beamer/{paper_filename}/fig/` or another known path
- beamer theme files or availability via `econ-slides-beamer`
- existing memo files in `Output/docs/`
- `docx` skill availability for Word speaker notes
- presenter name and affiliation
- requested deliverables: memo, slides, speaker notes, referee reports, extensions

If materials are missing but recoverable from the paper or other workspace files, proceed and create them. If a required input is absent, report exactly what is missing.

## Task Routing

### Memo

If the user asks to use an external model/provider or API, call `econ-llm-memo-paper`. Otherwise call `econ-memo-paper` or run memo-writing subagents directly under the rules above. For presentation workflows, default outputs are:

- `Output/docs/memo_{FirstAuthor}{Year}.md`
- `Output/docs/memo_{FirstAuthor}{Year}_zh.md`

### Referee Reports

If the user asks for referee reports, review letters, Top 5 or AER/QJE/RES/JPE/ECTA-style reports, editor letters, editorial synthesis, deliberation, or journal recommendations as part of the package, call `econ-top5-referee` as a nested editor-led workflow. Let `econ-top5-referee` manage its own journal matrix, editor subagent, referee subagents, quality audit, final decision memo, and cross-journal comparison when multiple journals are requested.

For complex presentation packages, pass the paper path, memo, author information, journal context, review-round context if known, and requested number of referee reports. Integrate only the editor's concise outputs into the presentation workflow unless the user asks to inspect full referee files.

### Author Research

Research all authors using web sources. Prefer academic profile pages, institutional pages, Google Scholar, Wikipedia, and Baidu Baike for Chinese authors when relevant. Save:

`Output/docs/authors.md`

For five or fewer authors, write a detailed paragraph for each. For more than five, fully profile the corresponding/lead author and list all others with institution and country.

### Slides

Call `econ-slides-beamer` for LaTeX beamer generation, theme handling, template copying, frame rules, compilation, and slide revisions. Unless the user specifies otherwise, use `{paper_filename}` (the original paper's filename without extension) as the subfolder name. Pass:

- paper content and memo
- author information
- figures/tables directory `Output/beamer/{paper_filename}/fig/`
- presenter name and affiliation
- theme preference, default PekingU unless user requests Qing
- output directory `Output/beamer/{paper_filename}/`
- filename `main.tex`

After successful compilation, copy the compiled PDF to `Output/docs/pre/` and rename it to `{paper_filename}_Beamer.pdf`.

When slides include formulas from the paper, add equation numbers with LaTeX `\tag{}` only for formulas that are numbered in the original paper. Preserve the original equation numbering. Do not invent tags for formulas that are unnumbered in the paper.

### Speaker Notes

Write Chinese speaker notes aligned page-by-page with the slides, then call `docx` to create the final Word document. Unless the user specifies otherwise, save:

`Output/docs/pre/{paper_filename}_Notes.docx`

Target 8000-10000 Chinese characters unless the user requests another length.

#### Format

| Level | Style | Content |
|-------|-------|---------|
| Heading 1 | large | Document title (paper reference) |
| Heading 2 | 16pt | Section names from slides (`\section{...}`) |
| Heading 4 | 12pt | `p. {PageNum} - {PageTitle}` for EACH content slide |
| Body | 12pt black | Explanatory text for each page |
| `【附注】` | 12pt bold prefix | Detailed Q&A prep; MUST copy relevant original English quotes |

#### Content Requirements

- **Total**: 8000-10000 Chinese characters
- **Correspondence**: Page-by-page alignment with slides
- **Figure/Table pages**: Include explanation of what the figure shows + copy the original paper's Figure/Table Notes verbatim as `【附注】`
- **Q&A prep**: `【附注】` sections should include direct English quotes from the paper for authoritative reference
- **Authors page**: Brief introduction only (1 paragraph)
- **Formula pages**: Do not reproduce the mathematical formula unless the user explicitly asks. Instead, identify the formula by slide/page number and, when available, the original equation number shown in the slide, then explain the formula's economic meaning in words.

When calling `docx`, pass the prepared note content and require a structured Word document with the heading levels above, readable Chinese body text with appendix-note blocks preserved, and page-by-page alignment with the final compiled slides.

Validate the created `.docx` according to the `docx` skill's validation guidance when the required tooling is available. If tooling is unavailable, report that validation could not be run while still saving the requested `.docx` when possible.

### Extensions

Do not add post-publication or broader policy extensions unless requested. If requested, research and save:

`Output/docs/pre{A/B}+.md`

Content areas for extensions:

1. **Domestic policy developments**: Search for major legal/regulatory changes since publication. Write in Chinese for domestic content.
2. **International frameworks**: Search FAO/WHO definitions, SDG targets, global statistics. Write in English, with key terms translated.
3. All supplementary materials go in `Output/docs/`.

Then add 2-3 extension slides before the ending page and update speaker notes.

## Review and Revision

After generating first outputs, run review subagents or direct review passes for:

- factual fidelity to the paper
- slide structure, page count, and figure order
- speaker-note coverage, Chinese readability, and DOCX structure
- compilation success and missing assets
- consistency across memo, slides, notes, and referee reports if included

Common revision patterns:

| Feedback | Action |
|----------|--------|
| Theme/color changes | Delegate to `econ-slides-beamer` |
| Content overflow | Delegate to `econ-slides-beamer` |
| Figure sizing | Delegate to `econ-slides-beamer` |
| Author info updates | Re-search, update authors.md + delegate slide update to `econ-slides-beamer` |
| Speaker note gaps | Add entries for new slides, expand 【附注】 quotes |
| Page count adjustments | Delegate to `econ-slides-beamer` |

Apply revisions, recompile slides when changed, and update affected documents. Preserve unrelated user changes in the workspace.

## Delivery Checklist

Before final response, verify:

- `plan.md` exists in the temporary agent workspace
- memo route was correct: `econ-memo-paper` for internal writing or `econ-llm-memo-paper` for explicit external LLM use
- `Output/docs/authors.md` exists with source URLs
- slides were generated through `econ-slides-beamer`, compiled, and the PDF copied to `Output/docs/pre/{paper_filename}_Beamer.pdf`
- slides quality: correct theme `.sty` copied, bottom footer removed, smoothbars navigation retained, exactly one ending page, every figure/table frame uses `[plain]`, `\term{}` used for emphasis, XeLaTeX compiles successfully twice
- speaker notes were generated through `docx` as `Output/docs/pre/{paper_filename}_Notes.docx` and cover each content slide
- speaker notes quality: 8000-10000 CN chars, all pages covered, 【附注】 with original English quotes
- requested referee reports, journal-specific editor decision memos, and any cross-journal comparison were produced through the editor-led `econ-top5-referee` workflow
- final response lists output paths and any verification failures
