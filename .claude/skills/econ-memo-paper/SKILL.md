---
name: econ-memo-paper
description: Write structured economics paper memos directly inside the current workflow without calling external LLM APIs. Use when the user asks for an academic paper memo, presentation memo, reading memo, Chinese or English economics paper summary, or internal memo from a paper, unless the user explicitly asks to use an external model/provider handled by econ-llm-memo-paper.
author: WZM
---

# Econ Memo Paper

Write a rigorous memo for an economics paper using the materials available in the workspace.

This skill is the internal-writing counterpart to `econ-llm-memo-paper`; it does not call external LLM APIs unless the user explicitly requests that route.

## Route Selection

Use this skill when the user wants Codex/subagents to write the memo directly. Use `econ-llm-memo-paper` instead when the user specifies an external provider/model, asks to call APIs, or provides instructions like "use Doubao/SiliconFlow/Bailian/ModelScope".

When the user asks for multiple memos, independent memos, or memo variants, run parallel subagents. Give each subagent the paper path, memo focus, required language, and output path. Each subagent must save the memo locally and return only status. Do not make one memo and lightly rewrite it into variants.

For a single long or difficult paper, prefer a subagent for the first full memo draft when context protection matters, then review and revise in the main agent.

## Inputs

Collect or infer:

- paper file path, preferably PDF or OCR/Markdown in `Input/papers/`
- target language: English, Chinese, or bilingual
- target length and audience
- output directory, default `Output/docs/`
- whether the memo is for slides, class discussion, literature review, or referee preparation
- whether inputs are multiple papers or multiple versions of one paper

Ask only for missing inputs that cannot be inferred from the workspace.

## Required Memo Format

Before drafting a memo, read `references/memo_format.md`. The memo must include the sections required there unless the user explicitly overrides the format.

Default format from the reference:

1. `Authors (Year, JAbbr.)` heading with Title and DOI
2. Research Question
3. Background
4. Data
5. Method
6. Contribution
7. Core Ref
8. Results
9. Conclusion
10. Comments
11. Comparison, when multiple papers or versions require it

Default style is English, bulleted Markdown, 300-600 words per paper. If the user requests Chinese, bilingual output, or a different length, preserve the required sections while adapting language and depth.

## Reading Protocol

Read enough of the paper to recover:

- research question, motivation, and economic mechanism
- contribution relative to literature
- model, data, empirical strategy, identification, or theoretical structure
- main results and how figures/tables support them
- assumptions, threats to validity, limitations, and external validity
- policy or welfare implications when relevant
- definitions and notation needed for a reader to follow the memo
- core references and how the paper positions itself against them

Do not hallucinate details that are not in the paper. If a claim is inferred rather than stated, mark it as an inference.

## Output Paths

Default English memo path: `Output/docs/memo_{FirstAuthor}{Year}.md`.
Default Chinese memo path: `Output/docs/memo_{FirstAuthor}{Year}_zh.md`.

For multiple papers, create one memo file per paper unless the user requests a combined file. For multiple versions of one paper, create one memo based on the latest version and include the version comparison section.

## Presentation-Preparation Notes

When called from `econ-pre-agent`, preserve the required memo sections and also emphasize material useful for slides:

- divide content into 3-4 presentation sections matching the paper structure
- list figures/tables by semantic mention order, not numeric order alone
- flag equations or diagrams that need visual explanation
- produce concise slide-ready bullets only after the analytic memo is complete

## Review Checklist

Before delivery, verify:

- the memo follows `references/memo_format.md`
- all required sections are present, including Core Ref and Comparison when applicable
- the memo states the paper's actual contribution rather than only topic area
- methods and identification/proof logic are explained, not merely named
- key results include direction, magnitude, and interpretation when available
- limitations are substantive and tied to the design
- output files are saved at the requested paths
- external LLM routing was used only when explicitly requested
