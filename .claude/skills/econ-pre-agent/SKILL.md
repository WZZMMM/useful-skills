---
name: econ-pre-agent
description: Agentic workflow for preparing economics paper presentation materials, including paper reading, memo routing, author research, LaTeX beamer slides, Chinese speaker notes as DOCX via the docx skill, optional extensions, and optional referee reports. Use when the user asks to prepare presentation materials, slides, memos, speaker notes, Word/DOCX speaking notes, or a combined presentation/referee package for an economics paper.
author: WZM
---

# Econ Pre Agent

Orchestrate the complete economics paper presentation workflow with context-protecting subagents and explicit file outputs. This skill modernizes `econ-pre` using the execution discipline of `do-agent`.

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
- beamer theme files or availability via `econ-latex-beamer`
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

Call `econ-latex-beamer` for LaTeX beamer generation, theme handling, template copying, frame rules, compilation, and slide revisions. Unless the user specifies otherwise, use `{paper_filename}` (the original paper's filename without extension) as the subfolder name. Pass:

- paper content and memo
- author information
- figures/tables directory `Output/beamer/{paper_filename}/fig/`
- presenter name and affiliation
- theme preference, default PekingU unless user requests Qing
- output directory `Output/beamer/{paper_filename}/`
- filename `main.tex`

After successful compilation, copy the compiled PDF to `Output/docs/pre/` and rename it to `{paper_filename}_Beamer.pdf`.

### Speaker Notes

Write Chinese speaker notes aligned page-by-page with the slides, then call `docx` to create the final Word document. Unless the user specifies otherwise, save:

`Output/docs/pre/{paper_filename}_Notes.docx`

Target 8000-10000 Chinese characters unless the user requests another length. Use headings by section and page. For figure/table pages, explain what the visual shows and include relevant original notes or quotes as an appendix-note block when available.

When calling `docx`, pass the prepared note content and require a structured Word document with:

- Heading 1 for the document title and paper reference
- Heading 2 for slide sections
- Heading 4 or equivalent compact headings for each slide/page title
- readable Chinese body text with appendix-note blocks preserved
- page-by-page alignment with the final compiled slides

Validate the created `.docx` according to the `docx` skill's validation guidance when the required tooling is available. If tooling is unavailable, report that validation could not be run while still saving the requested `.docx` when possible.

### Extensions

Do not add post-publication or broader policy extensions unless requested. If requested, research and save:

`Output/docs/pre{A/B}+.md`

Then add 2-3 extension slides before the ending page and update speaker notes.

## Review and Revision

After generating first outputs, run review subagents or direct review passes for:

- factual fidelity to the paper
- slide structure, page count, and figure order
- speaker-note coverage, Chinese readability, and DOCX structure
- compilation success and missing assets
- consistency across memo, slides, notes, and referee reports if included

Apply revisions, recompile slides when changed, and update affected documents. Preserve unrelated user changes in the workspace.

## Delivery Checklist

Before final response, verify:

- `plan.md` exists in the temporary agent workspace
- memo route was correct: `econ-memo-paper` for internal writing or `econ-llm-memo-paper` for explicit external LLM use
- `Output/docs/authors.md` exists with source URLs
- slides were generated through `econ-latex-beamer`, compiled, and the PDF copied to `Output/docs/pre/{paper_filename}_Beamer.pdf`
- speaker notes were generated through `docx` as `Output/docs/pre/{paper_filename}_Notes.docx` and cover each content slide
- requested referee reports, journal-specific editor decision memos, and any cross-journal comparison were produced through the editor-led `econ-top5-referee` workflow
- final response lists output paths and any verification failures






