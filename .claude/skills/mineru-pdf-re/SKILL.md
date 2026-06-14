---
name: mineru-pdf-re
description: MinerU PDF conversion workflow using official API docs. Supports single-file and batch processing (up to 50 files per API call, auto-chunking for larger directories). Use when explicitly asked to call MinerU to convert PDFs, or when PaddleOCR is not suitable and MinerU is chosen deliberately. Defaults to Precision Extract (token, full zip with Markdown/JSON/images/layout). Agent Lightweight (no token, Markdown only) is available for simple text extraction. Requires generated project scripts to keep the same names as this skill package scripts.
author: WZM
---

# MinerU PDF Re

Use this skill when the user asks to convert PDF files with MinerU.

## Routing Rule

For general PDF-to-Markdown conversion or PDF layout extraction, prefer `paddle-pdf-re` by default.

Use this skill when:

- The user explicitly says MinerU or `mineru-pdf-re`.
- Existing project artifacts or prior workflow requirements already depend on MinerU output.
- PaddleOCR is unavailable, unsuitable, or explicitly rejected and MinerU is the chosen fallback.

If the user explicitly names a converter, always use the named converter.

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

## Batch Processing (Precision Extract)

The Precision Extract script supports batch processing for directories of PDFs using the MinerU v4 native batch API (`/api/v4/file-urls/batch`).

How it works:

1. Collects PDF files from the input directory, applies `--start` / `--limit` for resumable subsets.
2. Chunks files into groups of up to 50 (API limit per request).
3. For each chunk:
   - Requests upload URLs in one API call (returns `batch_id` + `file_urls[]`).
   - Uploads files concurrently (4 workers).
   - Polls `GET /api/v4/extract-results/batch/{batch_id}` until all files reach a terminal state (`done` or `failed`), with per-file progress logging (page counts).
   - Downloads each completed file's ZIP, extracts, and runs post-processing independently.
4. Prints a success/failure summary at the end.

Usage:

```bash
# Single file (unchanged)
python Output\scripts\run_mineru_precision.py --input paper.pdf

# Batch: all PDFs in a directory
python Output\scripts\run_mineru_precision.py --input ./pdfs/

# Batch: skip first 10, process next 20
python Output\scripts\run_mineru_precision.py --input ./pdfs/ --start 10 --limit 20

# Resume a failed single-file upload
python Output\scripts\run_mineru_precision.py --input paper.pdf --batch-id <batch_id>
```

Supported parameters (complete):

| Parameter | Meaning | Default |
|---|---|---|
| `--input`, `-i` | PDF file or directory | required |
| `--output-dir`, `-o` | Output directory | `Output/ocr/mineru` |
| `--batch-id` | Resume from existing batch_id (single-file only) | None |
| `--model-version` | `pipeline` / `vlm` / `MinerU-HTML` | `vlm` |
| `--language` | Document language | `ch` |
| `--is-ocr` | Enable OCR | false |
| `--enable-formula` | Enable formula recognition | true |
| `--enable-table` | Enable table recognition | true |
| `--timeout` | Max seconds to wait per batch | 900 |
| `--poll-interval` | Seconds between status checks | 5 |
| `--start` | Skip first N files in batch mode | 0 |
| `--limit` | Max files to process (0=all) | 0 |
| `--log` | Custom log file path | auto-timestamped |

Limitations:

- Single API call supports up to 50 files. The script auto-chunks larger directories.
- Each file is limited to 200 MB and 200 pages.
- Failed files in a batch do not block other files; they are reported in the summary.

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

After Precision Extract (single file):

1. Confirm `{stem}_mineru/` exists and is nonempty.
2. Confirm `full.md`, at least one JSON file, and `images/` (when images are present) are inside the subfolder.
3. Confirm no timestamped `_output_*` folders remain in the output directory.
4. Confirm no `.pdf` files remain inside `{stem}_mineru/`.
5. Confirm `{stem}_mineru.md` exists in the output directory (parent level) with image references pointing to `{stem}_mineru/images/...`.

After Precision Extract (batch):

1. Confirm the log shows "Batch complete: N succeeded, M failed".
2. For each succeeded file, confirm the same items 1–5 as single-file mode.
3. If any files failed, check the log for per-file error messages (e.g. `err_msg` from the API).

After Agent Lightweight:

- Confirm only the Markdown output was written.
