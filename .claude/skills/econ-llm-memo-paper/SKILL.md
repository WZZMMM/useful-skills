---
name: econ-llm-memo-paper
description: >
  Generate academic paper memos by calling LLM APIs for specific PDF files.
  Supports multiple papers and multiple models simultaneously with concurrency control (default max 8).
  Use when the user provides specific PDF file paths and wants to generate memos using external LLM APIs.
  Triggered by phrases like "给这些论文写memo", "memo for these papers", "用Doubao给paper.pdf写memo",
  "generate memo for paper1.pdf and paper2.pdf", etc. This skill works with direct file paths,
  NOT journal+issue combinations.
author: WZM
---

# Econ LLM Memo Paper

Generate academic paper memos for specific PDF files by calling external LLM APIs (VolcanoEngine/Ark, SiliconFlow, Bailian, ModelScope). Supports multiple papers and multiple models with concurrency control.

## When to Use

- User provides specific PDF file paths (NOT journal+issue)
- User wants to generate memos for one or more papers using LLM APIs
- User specifies which provider/model to use

## Workflow

### Step 1: Gather Required Information

Extract from user input:
1. **PDF file paths** - One or more PDF files (required)
2. **Model specifications** - provider/model_id pairs (required)
   - Format: `provider/model_id` (e.g., `volcano_engine/doubao-seed-2-0-pro-260215`)
   - Or just `provider` to use the default model
3. **Prompt name** (default: Memo, maps to `Prompts/{name}.md`)
4. **Concurrency limit** (default: 8)

If missing, ask the user. If models not specified, show available options and ask.

### Step 2: Verify Prerequisites

1. PDF files exist at given paths
2. API keys are set for the specified providers:

| Provider | Env Variable | Config |
|----------|-------------|--------|
| volcano_engine | `ARK_API_KEY` | `references/volcano_engine_config.json` |
| siliconflow | `SILICONFLOW_API_KEY` | `references/siliconflow_config.json` |
| bailian | `BAILIAN_API_KEY` | `references/bailian_config.json` |
| modelscope | `MODELSCOPE_API_KEY` | `references/modelscope_config.json` |

If API key missing, tell the user to set the environment variable.

### Step 3: Run the Orchestrator

Scripts live in this skill's `scripts/` directory. Use `memo_papers.py` as the entry point.

```bash
python "{skill_scripts}/memo_papers.py" \
  "{pdf_path1}" "{pdf_path2}" ... \
  --model {provider1}/{model_id1} {provider2}/{model_id2} \
  [--prompt {prompt_name}] \
  [--concurrent N] \
  [--wait N]
```

**Run from project root:** `E:\your_project_root\JournalIssues`

Or run worker directly for a single paper:
```bash
python "{skill_scripts}/memo_paper_single.py" \
  "{pdf_path}" {provider} {model_id} \
  [prompt_name] [journal_abbr] [output_dir]
```

### Step 4: Monitor and Report

- Output files: `Output/Memo/{pdf_stem}_{model_suffix}.md`
- Logs: `Output/Logs/memo_paper_{timestamp}.log`
- Thinking content saved in collapsible HTML format
- Token usage recorded in each file's header comment

## Output Naming

Each paper-model combination produces a separate file:
- `{pdf_stem}_{model_suffix}.md`
- `pdf_stem`: PDF filename without extension
- `model_suffix`: Model ID (last segment after `/`)

Example: `Wang and Wang (2026, JDE).pdf` + `doubao-seed-2-0-pro-260215`
-> `Wang and Wang (2026, JDE)_doubao-seed-2-0-pro-260215.md`

## Concurrency Control

- Default max concurrent tasks: 8
- Controlled by `--concurrent N` flag
- Small delay (`--wait`, default 5s) between task launches to avoid API rate limits
- Each worker uploads its own PDF and cleans up after completion

## Resume Support

- Already processed papers (with valid content) are skipped
- Error-marked files are re-processed
- Cross-model: different models produce separate files

## Available Models

Load from `references/{provider}_config.json` to see available models and defaults. Run:
```bash
python "{skill_scripts}/memo_papers.py" --list-models
python "{skill_scripts}/memo_papers.py" --list-providers
```

## Error Handling

- Retry on transient errors (timeout, rate limit, 5xx) with backoff
- API key errors: prompt user to set environment variable
- File not found: report specific missing file
- File upload timeout: report and fail
