---
name: econ-pre
description: "Complete workflow for producing academic economics paper presentations: read paper, generate memo, research authors, create LaTeX beamer slides, write Chinese speaker notes, and iterate on revisions. Use when the user asks to prepare beamer slides, make an academic presentation, or prepare presentation materials for a paper."
author: WZM
---
# Econ Presentation

## Overview

Full pipeline for turning an economics paper into a presentation:
(1) Read & understand the paper, (2) write English memo + Chinese translation,
(3) research author backgrounds, (4) generate LaTeX beamer from one of two theme
templates, (5) produce Chinese speaker notes (DOCX), (6) revise iteratively.

---

## Phase 0: Pre-Flight Check (v0.0.x Planning Stage)

**This phase runs when the skill is first invoked.** Explore the project directory,
identify what materials exist, then report to the user with a checklist. For
**each missing item**, tell the user what to provide before proceeding.

| Required Material                                      | Check                                                                                        |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Paper text (markdown/PDF) in `Input/papers/`         | Read and verify it's accessible, correctly OCR'd                                             |
| Figures & tables as PDF in `Output/beamer/fig-preX/` | List expected figures; flag any missing                                                      |
| Beamer theme `.sty` file                             | Check if PekingU.sty or Qing.sty exists in project; if not, will copy from skill `assets/` |
| Memos (English + Chinese)                              | If absent, ask: "Generate via `/econ-llm-memo-paper` or write directly?"                   |
| Presenter name & affiliation                           | Ask user if not specified                                                                    |

**Do NOT proceed past v0.0.x until all required materials are confirmed.**

---

## Phase 1: Read Paper & Write Memos

### 1a. Read the Paper

Extract: research question, context, motivation; section structure; key findings,
data, methods; figures/tables with **semantic mention order** (when discussed in
text, NOT figure/table number); economics themes (market failures, externalities,
policy instruments); if part of a series, also read editorial/intro paper.

### 1b. Memo (delegate to `/econ-llm-memo-paper`)

Prefer calling `/econ-llm-memo-paper`. Output:

- `./Output/docs/memo_{FirstAuthor}{Year}.md` (English, length per user spec)
- `./Output/docs/memo_{FirstAuthor}{Year}_zh.md` (Chinese translation)
- 3-4 sections from paper structure; append "Key takeaway for economics students"

---

## Phase 2: Research Author Backgrounds (MANDATORY)

For EVERY paper, research ALL authors via web search. Produce `./Output/docs/authors.md`:

**Search sources**: academic profile pages, institutional websites, Wikipedia,
Google Scholar, Baidu Baike (for Chinese authors). Record source URLs.

**Format**:

- **5 or fewer authors**: Each gets a detailed paragraph (position, education,
  research areas, key highlights, source URL)
- **More than 5 authors**: Corresponding author gets full profile; others listed
  by country of primary affiliation. Detailed field-specific notes for lead/key
  co-authors. Every author must have at minimum: name, institution, country.

---

## Phase 3: Generate Beamer Slides

**Delegate to `/econ-latex-beamer`** — this skill handles theme selection, template
copying, preamble, frame structure, content rules, compilation, and revision.

When calling `/econ-latex-beamer`, pass:

- Paper content / memo (from Phase 1)
- Authors info (from Phase 2)
- Figures/tables directory path
- Presenter name & affiliation
- Theme preference (PekingU default, or Qing)
- Output directory: `Output/beamer/`
- Output filename: `{date}_pre{A/B}.tex`

---

## Phase 4: Extensions & Supplementary Research (OPTIONAL — Ask User First)

After the core slides are generated, **ask the user** whether they want
post-publication developments or broader context added. Do NOT assume.

If the user says yes, produce `./Output/docs/pre{A/B}+.md`:

1. **Domestic policy developments**: Search for major legal/regulatory changes
   since publication. Write in Chinese for domestic content.
2. **International frameworks**: Search FAO/WHO definitions, SDG targets, global
   statistics. Write in English, with key terms translated.
3. **All supplementary materials go in `./Output/docs/`**.
4. Add new `\section{Extensions}` with 2–3 content slides at the end (before the
   ending page). Adjust speaker notes accordingly.

---

## Phase 5: Speaker Notes (DOCX)

Generate `./Output/beamer/{date}_pre{A/B}.docx`. Can delegate to the `/docx` skill.

### Format

| Level        | Style                  | Content                                                       |
| ------------ | ---------------------- | ------------------------------------------------------------- |
| Heading 1    | 黑体 large             | Document title (paper reference)                              |
| Heading 2    | 黑体 16pt              | Section names from slides (`\section{...}`)                 |
| Heading 4    | 黑体 12pt              | `p. {PageNum} - {PageTitle}` for EACH content slide         |
| Body         | 宋体 12pt (小四) black | Explanatory text for each page                                |
| `【附注】` | 宋体 12pt bold prefix  | Detailed Q&A prep; MUST copy relevant original English quotes |

### Content Requirements

- **Total**: 8000–10000 Chinese characters
- **Correspondence**: Page-by-page alignment with slides
- **Figure/Table pages**: Include explanation of what the figure shows + copy
  the original paper's Figure/Table Notes verbatim as `【附注】`
- **Q&A prep**: `【附注】` sections should include direct English quotes from
  the paper for authoritative reference
- **Authors page**: Brief introduction only (1 paragraph)

---

## Phase 6: Iterative Revision

After delivering initial versions, expect user feedback. Common revision types:

| Feedback               | Action                                                                         |
| ---------------------- | ------------------------------------------------------------------------------ |
| Theme/color changes    | Delegate to `/econ-latex-beamer`                                             |
| Content overflow       | Delegate to `/econ-latex-beamer`                                             |
| Figure sizing          | Delegate to `/econ-latex-beamer`                                             |
| Author info updates    | Re-search, update authors.md + delegate slide update to `/econ-latex-beamer` |
| Speaker note gaps      | Add entries for new slides, expand 【附注】 quotes                             |
| Page count adjustments | Delegate to `/econ-latex-beamer`                                             |

After each revision round: recompile, verify page count, update work logs.

---

## Quality Checklist

Before delivering any output:

- [ ] Pre-flight check completed at v0.0.x (all materials confirmed present)
- [ ] Authors researched and `./Output/docs/authors.md` written with source URLs
- [ ] Beamer slides generated via `/econ-latex-beamer` (Phase 3 delegated)
- [ ] Speaker notes: 8000–10000 CN chars, all pages covered, 【附注】 with original quotes
- [ ] Extensions (if requested): document in `./Output/docs/`, source URLs present
