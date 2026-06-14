---
name: econ-top5-referee
description: Draft Top 5 economics journal referee reports, editor cover letters, editor-led decision memos, and journal-specific review packages for AER, QJE, RES/REStud, JPE, and ECTA/Econometrica. Use when the user asks for economics referee reports, review reports, journal review letters, Top 5 journal fit, AER/QJE/RES/JPE/ECTA-style refereeing, multiple independent reviewer reports, one report per journal, multiple reports for one journal, editorial synthesis, editor decision letters, or publication recommendations for economics papers.
author: WZM
---

# Econ Top 5 Referee

Produce fair, decisive, scientifically grounded referee and editorial materials for economics papers targeting Top 5 journals: AER, QJE, RES/REStud, JPE, and ECTA/Econometrica.

The main/orchestrating agent may read these references as needed before launching subagents:

- `references/top5_journal_guidance.md` for journal-specific standards and aliases
- `references/aea_referee_guideline.md` for general economics referee report discipline
- `references/editor_role_guidance.md` for editor-led synthesis and decision memos


## Subagent File-Input Isolation

Enforce strict file-input boundaries for every subagent. The main/orchestrating agent may read this skill's reference files and create `editor_brief.md`, but referee and editor subagents must not read reference files, memos, author files, slides, plans, prior notes, web pages, or any other workspace files outside their explicitly allowed inputs.

Referee subagents:

- must read the paper original specified by the user, which may be a PDF, OCR text, or Markdown conversion
- must read the corresponding journal-specific `editor_brief.md` written by the editor subagent
- must not read skill references, other referee reports, memos, author research, slide files, notes, plans, web pages, or any other file
- receive output-path instructions in the subagent prompt; journal standards, reviewer profile, and review-round context should come from `editor_brief.md` whenever possible
- write their assigned report files, but do not read any files other than the paper original and the corresponding `editor_brief.md`

Editor subagent:

- for triage/editor brief, must read only the paper original
- for quality audit, decision memo, decision letter, or cross-journal comparison, must read only the paper original and all referee opinion files for the relevant review package
- must not read skill references, memos, author research, slide files, plans, web pages, or any other file
- receive journal standards, editor duties, and requested output structure only in the subagent prompt, not as extra input files

If a referee subagent needs information from a forbidden file, the main/orchestrating agent must either place the necessary instruction in `editor_brief.md` before launching the referee or withhold that information. Do not relax the file boundary.
## Operating Rules

1. Identify the paper, requested journal(s), review round, target language, anonymity requirements, final deliverable directory, and number of reports per journal.
2. Default to AER if the user does not specify a journal.
3. Accept flexible combinations: one AER report; one report for each Top 5 journal; three JPE reports and one QJE report; an editor-only desk assessment; or any other explicit matrix.
4. Normalize journal aliases: AER, QJE, RES/REStud, JPE, ECTA/Econometrica.
5. If conflict-of-interest information is available, surface any conflict immediately. If not available, do not invent one.
6. Separate advice to the editor from comments to authors. The editor-facing letter may be franker and may include ethics or confidential concerns; the author-facing report must remain professional and evidence-based.
7. Make a clear recommendation when requested: accept, conditional accept, revise and resubmit, reject, desk reject, or seek another opinion.
8. Do not require changes that are not necessary for publishability at the specified journal. Label optional improvements as suggestions.
9. Avoid copy-editing except when writing quality blocks interpretation. Do not demand broad robustness exercises without explaining why the result would change publishability.
10. When producing an editorial decision, do not mechanically average referee recommendations. The editor must make an independent assessment of contribution, credibility, journal fit, and the review file.


## Temporary Workspace and Process Documents

Process documents must be saved under a project-local temporary workspace in `/agent_tasks/`, following the `do-agent` and `econ-pre` convention.

If this skill runs standalone:

1. Get the current Beijing date/time.
2. Create `agent_tasks/{short_task_description}_yyyyddmmhh/` as the temporary workspace.
3. If that folder already exists, create a non-overwriting variant.
4. Save the review matrix and all process documents in this workspace.

If this skill is nested inside a larger multi-step/multi-agent workflow, such as `do-agent` or `econ-pre`, reuse the already-created temporary workspace passed by the parent workflow. Do not create a second top-level `agent_tasks/` directory unless no parent workspace exists.

Use these process-document paths inside the temporary workspace:

- `{workspace}/top5_referee_plan.md`
- `{workspace}/review_matrix.md`
- `{workspace}/{Journal}/editor_brief.md`
- `{workspace}/{Journal}/referee_{N}.md`
- `{workspace}/{Journal}/cover_letter_{N}.md`
- `{workspace}/{Journal}/editor_quality_audit.md`
- `{workspace}/{Journal}/editor_decision_memo.md`
- `{workspace}/{Journal}/decision_letter.md` when requested
- `{workspace}/top5_comparison.md` when multiple journals are requested

Final user-facing deliverables must be saved to the user-specified location. If the user does not specify a final location, save them under `Output/docs/review/`. Subagent input/output paths should still use the temporary workspace. In particular, `editor_brief.md` must live in the temporary workspace because referee subagents must read it.

## Final Deliverables

Keep process files in the temporary workspace, then prepare final user-facing files in the requested final directory. If the user does not specify a final directory, use:

`Output/docs/review/`

Default final filenames:

- one referee report: `refereeA_{Author}{Year}.md`
- multiple referee reports: `refereeA_{Author}{Year}.md`, `refereeB_{Author}{Year}.md`, `refereeC_{Author}{Year}.md`, etc.
- editor synthesis/opinion: `editor_{Author}{Year}.md`
- Top 5 or multiple-journal comparison: `comparison_{Author}{Year}.md`

When multiple journals are requested, include the journal abbreviation before the author-year token unless the user specifies another naming scheme:

- `refereeA_AER_{Author}{Year}.md`
- `refereeA_QJE_{Author}{Year}.md`
- `editor_AER_{Author}{Year}.md`
- `editor_QJE_{Author}{Year}.md`
- `comparison_top5_{Author}{Year}.md`

Final referee files should contain the complete referee opinion intended for delivery. Final editor files should contain the editor's overall evaluation, deliberation, decision recommendation, and any decision-letter text requested by the user. Confidential cover-letter content may be included or separated according to the user's request.
## Journal Request Matrix

Before launching subagents, create a review matrix and save it as `{workspace}/review_matrix.md`. Each row should contain:

- journal: `AER`, `QJE`, `RES`, `JPE`, or `ECTA`
- report_count: number of independent referee reports
- referee_profiles: profile list or `auto`
- editor_output: yes/no
- decision_letter: yes/no
- output_prefix
- final_deliverable_dir, default `Output/docs/review/`

Defaults:

- no journal specified -> `AER`, `report_count = 1`, `editor_output = yes`
- user says `Top 5` or `each journal` -> one report each for AER, QJE, RES, JPE, and ECTA, plus a cross-journal editor comparison
- user says `multiple reports` without a number -> three reports for the specified/default journal
- user asks `editor only`, `desk review`, or `overall evaluation` -> no referee reports unless requested; produce editor brief and decision memo

## Editor-Led Workflow

This skill can run as a standalone multi-subagent editorial workflow or as a nested component inside `econ-pre`.

Use an editor subagent whenever the user requests an editorial decision, overall evaluation, deliberation, multiple reports, multiple journals, or an integrated review package. The editor subagent is not a referee; it manages assignments, audits report quality, and writes the final synthesis.

Default process outputs are saved in the temporary workspace under `{workspace}/{Journal}/`. Final user-facing referee and editor opinions must be saved to the user-specified final directory, or `Output/docs/review/` by default, using the naming rules in Final Deliverables.

### Stage 1: Editor Triage and Brief

Assign one editor subagent to read only the paper original enough to decide the review strategy. Pass journal standards and editor-role instructions inline in the prompt. For each journal row, it must write `{workspace}/{Journal}/editor_brief.md` with:

- manuscript summary and claimed contribution
- target journal standard and likely bar
- whether desk review, full review, or additional expertise is appropriate
- referee profiles to assign
- specific questions for each referee
- journal-specific quality rules from `top5_journal_guidance.md`
- conflict, ethics, data, replication, disclosure, RCT/IRB, and AI-use checks to flag

### Stage 2: Independent Referee Reports

Run referee subagents in parallel wherever possible. Each subagent must independently read the paper original and the corresponding journal-specific `editor_brief.md`, then write its own output file. Do not draft one report and vary the wording.

Assign reviewer profiles when useful, for example:

- empirical identification and data referee
- theory/model referee
- contribution/literature referee
- econometrics/proof referee
- policy/external validity referee
- broad general-interest editor-like referee, only if needed in addition to the editor

Each referee subagent receives exactly two input files: the paper original and the corresponding journal-specific `{workspace}/{Journal}/editor_brief.md`. Process output paths in `{workspace}/{Journal}/` must be provided inline in the prompt; final deliverable paths are prepared after process reports are complete. Each saves complete reports locally and returns only a short status summary to the main agent.

For ECTA, structure the author-facing report as `Summary`, `Essential Points`, and `Suggestions` unless the user asks otherwise. For other journals, use the standard Top 5 report package.

### Stage 3: Editor Quality Audit

After referee files exist, the editor subagent reads only the paper original and all referee opinion files for the relevant package, including referee reports and confidential cover letters. It writes `{workspace}/{Journal}/editor_quality_audit.md` checking:

- whether each report is professional and evidence-based
- whether it applies the specified journal's standard rather than generic acceptability
- whether serious objections are tied to publishability at that journal
- whether R&R recommendations specify what would make the paper publishable
- whether optional suggestions are mislabeled as requirements
- whether any report is vague, internally inconsistent, overly demanding, or outside expertise
- whether another referee or specialist opinion is needed

If a report is not usable, request a targeted revision from that referee subagent when possible. If not possible, mark the limitation in the audit.

### Stage 4: Editor Decision and Deliberation

For each journal, the editor subagent writes `{workspace}/{Journal}/editor_decision_memo.md` using only the paper original and the referee opinion files. The main/orchestrating agent must provide any journal-specific standards or editor-role instructions inline in the prompt. Include:

1. manuscript and review file
2. editorial summary
3. target journal fit and bar
4. referee consensus and disagreement
5. independent editorial assessment
6. decision recommendation
7. required changes for publishability
8. optional suggestions
9. ethics, data, replication, disclosure, RCT/IRB, and AI-use flags
10. draft decision letter when requested

The editor's decision may differ from individual referees. Explain why.

### Stage 5: Cross-Journal Comparison

When multiple journals are requested, the editor subagent writes `{workspace}/top5_comparison.md` using only the paper original and all referee opinion files from the requested journals. Summarize:

- likely fit for each requested journal
- relative strengths and weaknesses under each journal's bar
- recommendation by journal
- whether the paper is a better fit for another Top 5 journal or a field journal
- common required revisions across journals
- journal-specific requirements that should not be generalized

## Referee Report Package

For each referee, write two separable sections or files unless the user requests only one:

1. **Confidential cover letter to the editor/coeditor**
   - concise summary of the paper's contribution
   - target-journal fit
   - main strengths and weaknesses
   - publishability assessment
   - recommendation and reasoning
   - confidential concerns, conflicts, ethics issues, data/replication issues, or need for specialist opinion if relevant

2. **Report to the authors**
   - concise summary of claimed results and contribution
   - assessment of importance for the target journal
   - problems that render the paper unpublishable and unlikely to be fixed; leave empty for an R&R recommendation
   - problems that currently block publication but could be corrected
   - suggestions or issues that do not block publication
   - brief closing paragraph that matches the recommendation tone

## Evaluation Standard

Judge the paper by publishability at the specified journal, not by whether it can be made closer to the referee's preferred paper. For empirical papers, tie identification, data, measurement, robustness, and interpretation concerns to the claimed contribution. For theory papers, identify actual proof errors, counterexamples, incoherence, or missing assumptions rather than stating disbelief. For all papers, weigh ambition and contribution against flaws.

## Quality Checklist

Before final delivery, verify:

- temporary workspace under `agent_tasks/` exists or parent workflow workspace was reused
- review matrix and all process documents were saved under the temporary workspace
- final deliverable directory was user-specified or defaulted to `Output/docs/review/`
- final referee and editor files were saved with names like `refereeA_{Author}{Year}.md` and `editor_{Author}{Year}.md`
- all requested journal/report combinations in the matrix were produced
- unspecified journal requests defaulted to AER
- editor subagent produced `{workspace}/{Journal}/editor_brief.md` and `{workspace}/{Journal}/editor_decision_memo.md` when required
- referee recommendations are explicit and consistent across cover letter and report
- serious objections explain why they matter for publishability at the specified journal
- R&R reports specify what a satisfactory correction would look like
- optional suggestions are clearly labeled as optional
- editor quality audit flags weak or unusable reports
- final editor decision is decisive and not a vote count
- referee subagents read only the paper original and corresponding `editor_brief.md`; editor subagents read only the paper original and referee opinion files
- multiple-journal requests include a cross-journal comparison







