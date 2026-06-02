---
name: mineru-pdf-re
description: MinerU PDF conversion workflow using official API docs. Use when asked to call MinerU to convert PDFs. Defaults to Precision Extract (token, full zip with Markdown/JSON/images/layout). Agent Lightweight (no token, Markdown only) is available for simple text extraction. Requires generated project scripts to keep the same names as this skill package scripts.
author: WZM
---

# MinerU PDF Conversion

Use this skill when the user asks to convert PDF files with MinerU.

## Mode Selection

Decide from the task requirements:

- **Precision Extract** (default): Use when the user needs layout JSON, bounding boxes, tables/figures/images saved locally, full returned content, high-precision VLM parsing, batch/local-file production parsing, or later PDF figure/table cropping. Also use as the default when the user does not specify a mode.
- **Agent Lightweight**: Use only when the user explicitly requests lightweight/text-only Markdown extraction and does not need local embedded images, JSON, layout information, or full returned artifacts.

Default to Precision Extract unless the user explicitly requests lightweight mode.

## Script Naming Rule

When creating or copying Python scripts into a project, script filenames must exactly match the bundled script names:

```text
Output\scripts\run_mineru_precision.py
Output\scripts\run_mineru_agent_light.py
```

Do not merge Precision Extract and Agent Lightweight into one script. Do not invent alternate script names such as `mineru_client.py`, `run_mineru.py`, or `convert_mineru.py`.

## Precision Extract Rules

Use `scripts/run_mineru_precision.py`.

API workflow from the official docs:

1. Request upload URL with `POST https://mineru.net/api/v4/file-urls/batch`.
2. Upload local file with `PUT {file_url}`.
3. Poll `GET https://mineru.net/api/v4/extract-results/batch/{batch_id}`.
4. Download `full_zip_url`.
5. Extract the ZIP.

Recommended parameters:

```json
{
  "model_version": "vlm",
  "enable_formula": true,
  "enable_table": true,
  "is_ocr": false,
  "language": "ch"
}
```

Authentication:

- Requires `MINERU_API_KEY`.
- Use `Authorization: Bearer {token}`.

Output rule:

- If the user specifies an output directory, use that path. Otherwise default to `Output/ocr/mineru/` (relative to the project working directory).
- Save all returned ZIP contents in exactly one child folder:

```text
{output_dir}/{original_pdf_stem}_mineru/
```

- Do not duplicate `full.md`, `layout.json`, images, or other JSON files into the parent directory.
- The Markdown file to use is inside that folder, normally:

```text
{original_pdf_stem}_mineru/full.md
```

- Layout JSON is inside that folder, normally:

```text
{original_pdf_stem}_mineru/layout.json
```

- Images are inside:

```text
{original_pdf_stem}_mineru/images/
```

Post-processing (mandatory):

1. **Delete timestamped intermediate folders**: Remove any folders matching `{stem}_mineru_output_*` in the output directory. These are temporary extraction artifacts.
2. **Delete PDF files**: Remove any `.pdf` files inside the final `{stem}_mineru/` folder (e.g., `*_origin.pdf`).
3. **Copy `full.md` to parent**: Copy `full.md` from `{stem}_mineru/` to the output directory as `{stem}_mineru.md`. When copying, rewrite image references so they include the subfolder prefix:

```text
](images/...)  ->  ]({stem}_mineru/images/...)
```

This ensures the top-level Markdown file can find images in its sibling subfolder.

Markdown image references (inside the subfolder):

- Inside `{stem}_mineru/full.md`, image links should be `images/...` (relative to the subfolder).
- The copied top-level `{stem}_mineru.md` must use `{stem}_mineru/images/...` (relative to the parent).

Retry/resume:

- If upload succeeds but polling/download fails, keep the `batch_id` from logs and resume with `--batch-id` instead of uploading again.

## Agent Lightweight Rules

Use `scripts/run_mineru_agent_light.py`.

API workflow from the official docs for local files:

1. Request signed upload with `POST https://mineru.net/api/v1/agent/parse/file`.
2. Upload local file with `PUT {file_url}`.
3. Poll `GET https://mineru.net/api/v1/agent/parse/{task_id}`.
4. Download `markdown_url`.

No token is required. Do not pass `Authorization`.

Output rule:

- Save only the Markdown file requested by the user.
- Do not save JSON.
- Do not save local embedded images.
- Do not create a `{stem}_mineru/` folder.

Limits:

- File size <= 10 MB.
- Page count <= 20 pages.
- Single file only.

## Validation

After Precision Extract:

1. Confirm `{stem}_mineru/` exists and is nonempty.
2. Confirm `full.md`, at least one JSON file, and `images/` (when images are present) are inside the subfolder.
3. Confirm no timestamped `_output_*` folders remain in the output directory.
4. Confirm no `.pdf` files remain inside `{stem}_mineru/`.
5. Confirm `{stem}_mineru.md` exists in the output directory (parent level) with image references pointing to `{stem}_mineru/images/...`.

After Agent Lightweight:

- Confirm only the Markdown output was written.
