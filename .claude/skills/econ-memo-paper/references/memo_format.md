# Memo Format Reference

Use this reference when writing memos with `econ-memo-paper`. The source prompt is `Input/prompts/Memo.md`; this version is condensed for agent use. The memo must include all required sections below unless the user explicitly requests a different format.

## Role and Defaults

Write as an economics PhD student. Default memo style:

- English
- bulleted Markdown
- 300-600 words per paper unless the user asks for another length
- short, precise, and close to the paper's own wording, refined when necessary

## Multiple Inputs

First distinguish input type:

- Multiple papers: write one memo for each paper.
- Multiple versions of the same paper: write one memo, primarily based on the latest version, with chronological comparison of changes.

If multiple papers have overlapping authors, include a comparison section in each memo. If there is no meaningful overlap or relationship, omit comparison only when the prompt allows it; otherwise state that no relevant comparison is apparent.

## Required Structure

Use this heading form:

`## Authors (Year, JAbbr.)`

Use authors' last names and journal abbreviation when available.

Immediately include:

- `Title: ...`
- `DOI: ...` or `DOI: None`

Then include these sections in order.

### Research Question

Use the abstract and the full introduction. State the question as the paper frames it, not merely the broad topic.

### Background

Condense the introduction, context, motivation, and institutional background. Explain why the question matters.

### Data

List all data used, with sources, units, period, geography, sample construction, and key variables when available.

### Method

For reduced-form papers, explain the identification strategy such as IV, DID, RDD, event study, randomized design, or other design. Include treatment/control logic and key estimating equation intuition when important.

For structural or theoretical papers, explain the model, estimation or calibration, and how counterfactual or causal inference is implemented.

If important variables are constructed in nontrivial ways, summarize their formulation or implementation.

### Contribution

Explain how the paper improves existing research and why it is valuable. Break contribution into concrete points rather than generic claims.

### Core Ref

Identify 1-5 core references from the paper. Core references are usually cited and discussed multiple times, are closely related, or provide the theoretical foundation, antecedent empirical evidence, formalization, extension, or critique.

Use one bullet per reference with this pattern:

- Authors (Year): how the reference is related -> what is new in this paper

### Results

Report specific empirical or theoretical results. Include magnitudes, directions, and mechanisms when available. Cover core results plus robustness, heterogeneity, mechanisms, extensions, and supporting analyses that strengthen the main argument.

### Conclusion

Summarize the broader conclusions that answer the research question. Include side findings or broader implications when the authors discuss them.

### Comments

Summarize strengths, limitations, caveats, and further research directions, especially from the conclusion and discussion sections. Add concise reader comments only when grounded in the paper.

### Comparison

Include when there are multiple attached papers or multiple versions.

For multiple related papers, use one bullet for each other paper:

- OtherPaper (Year JAbbr.) -> ThisPaper (Year JAbbr.): what is in the other paper -> what this paper adds or changes

For multiple versions, use one bullet for each update:

- Earlier version -> Updated version: what changed or improved

## Quality Checks

Before saving, verify:

- all required sections are present
- word count matches the requested range unless overridden
- DOI is present or explicitly `None`
- data and method are not vague labels only
- results include specific findings rather than only topic summaries
- core references describe both relationship and novelty
- comparison logic is included when multiple inputs require it
