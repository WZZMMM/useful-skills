---
name: paddle-pdf-re
description: PaddleOCR-VL-1.6 async PDF conversion workflow. Prefer this skill by default when converting PDFs to Markdown or when layout information is needed, unless the user explicitly asks for another converter. Uses the project script Output\scripts\run_paddle_ocr_async.py and saves Markdown, local images, and raw JSONL/JSON artifacts.
author: WZM
---

# Paddle PDF Re

Use this skill by default when the user asks to convert PDF files to Markdown, extract PDF layout information, or obtain PDF parsing JSON.

If the user explicitly asks for a named converter, follow that request:

- If the user says PaddleOCR or `paddle-pdf-re`, use this skill.
- If the user says MinerU or `mineru-pdf-re`, use `mineru-pdf-re`.
- If the user does not specify a converter, prefer PaddleOCR for PDF-to-Markdown conversion and layout extraction.

## Mode Selection

Use PaddleOCR-VL async conversion when the task needs any of the following:

- Markdown converted from one or more PDF files.
- Layout parsing results, block/category information, page-level JSON, or later figure/table cropping.
- Local image files referenced from Markdown.
- Batch conversion with resumable indexing.

For simple Markdown-only conversion, still use this skill by default unless the user explicitly requests MinerU Agent Lightweight or another converter.

## Script Naming Rule

When creating or revising the PaddleOCR project script, the filename must exactly be:

```text
Output\scripts\run_paddle_ocr_async.py
```

Do not invent alternate script names such as `run_paddle.py`, `paddle_ocr.py`, `convert_pdf.py`, or `test_run_paddle_ocr_async.py` for formal conversion.

Run the script through the same path:

```bash
python Output\scripts\run_paddle_ocr_async.py ...
```

If the project already has this script, revise that file instead of creating a replacement.

## API Workflow

Use PaddleOCR-VL-1.6 with the async jobs API:

1. Submit the PDF with `POST https://paddleocr.aistudio-app.com/api/v2/ocr/jobs`.
2. Poll job state with `GET https://paddleocr.aistudio-app.com/api/v2/ocr/jobs/{job_id}`.
3. Download the returned JSONL result.
4. Save raw JSONL/JSON layout artifacts.
5. Download referenced images into a local child folder.
6. Merge page Markdown into one top-level Markdown file and rewrite image references to local relative paths.

Recommended payload:

```json
{
  "model": "PaddleOCR-VL-1.6",
  "optionalPayload": {
    "useDocOrientationClassify": false,
    "useDocUnwarping": false,
    "useChartRecognition": false
  }
}
```

Image correction defaults:

- `useDocOrientationClassify` (方向矫正): **OFF** by default. Enable with `--orientation` when input images may be rotated 90/180/270 degrees.
- `useDocUnwarping` (扭曲矫正): **OFF** by default. Enable with `--unwarping` when input images have wrinkles, skew, or physical distortion.
- `useChartRecognition` (图表识别): **OFF** by default. Enable with `--chart-recognition` to parse charts (bar, pie, etc.) into table form.

These are off because most academic PDFs are already well-oriented digital documents; enabling them adds processing time with no benefit for clean PDFs.

Authentication:

- Requires `PADDLE_API_KEY`.
- Use `Authorization: bearer {token}`.
- Do not hardcode API keys in scripts or logs.

## Output Rules

If the user specifies an output directory, use that path. Otherwise default to:

```text
Output/ocr/paddle/
```

For each input PDF, save:

```text
{output_dir}/{original_pdf_stem}_paddle.md
{output_dir}/{original_pdf_stem}_paddle/jsonl.jsonl
{output_dir}/{original_pdf_stem}_paddle/img/
```

Top-level Markdown image references must point to the sibling child folder:

```text
![image]({original_pdf_stem}_paddle/img/img-in-chart-box-001.jpg)
![image]({original_pdf_stem}_paddle/img/img-in-image-box-001.png)
```

All images returned by the API are downloaded and kept, including `img_in_chart_box_*` (charts/graphs), `img_in_image_box_*` (vector graphics, diagrams, mathematical figures), and any other prefixes. All underscores in image filenames are replaced with hyphens (e.g. `img_in_chart_box_001.jpg` becomes `img-in-chart-box-001.jpg`).

Do not leave remote image URLs in the final Markdown when local images were requested or are needed by downstream tasks.

## Page Limit Handling

The PaddleOCR API processes at most 100 pages per request. PDFs exceeding this limit are **automatically split** into chunks, each submitted as a separate API job, and the results are merged back into a single set of output artifacts. The split/merge is transparent — the final deliverables are identical in structure to a single-chunk conversion.

To adjust the chunk size (e.g. for testing or tighter limits):

```bash
python Output\scripts\run_paddle_ocr_async.py --input large_book.pdf --chunk-pages 50
```

## Usage

```bash
# Single PDF, default output directory
python Output\scripts\run_paddle_ocr_async.py --input paper.pdf

# Batch conversion
python Output\scripts\run_paddle_ocr_async.py --input ./pdfs/ --workers 3

# Custom output directory
python Output\scripts\run_paddle_ocr_async.py --input paper.pdf --output Output/refs/converted

# Resume a subset of files
python Output\scripts\run_paddle_ocr_async.py --input ./pdfs/ --start 10 --limit 20

# Large PDF: custom page chunk size (default 100)
python Output\scripts\run_paddle_ocr_async.py --input large_book.pdf --chunk-pages 50

# Enable image correction for scanned/photographed documents
python Output\scripts\run_paddle_ocr_async.py --input scan.pdf --orientation --unwarping

# Enable chart recognition
python Output\scripts\run_paddle_ocr_async.py --input report.pdf --chart-recognition

# Disable layout detection (VL model handles everything)
python Output\scripts\run_paddle_ocr_async.py --input paper.pdf --layout-detection false

# Fine-tune VL model parameters
python Output\scripts\run_paddle_ocr_async.py --input paper.pdf --repetition-penalty 1.2 --temperature 0.3
```

Supported parameters (basic):

| Parameter | Meaning | Default |
|---|---|---|
| `--input`, `-i` | PDF file or directory | required |
| `--output`, `-o` | Output directory | `Output/ocr/paddle` |
| `--api-key` | API key | `PADDLE_API_KEY` |
| `--workers`, `-w` | Parallel workers | `3` |
| `--start` | Skip first N files | `0` |
| `--limit` | Max files to process, `0` = all | `0` |
| `--chunk-pages` | Max pages per API request; larger PDFs auto-split | `100` |

Image correction (all OFF by default):

| Parameter | API field | Meaning |
|---|---|---|
| `--orientation` | `useDocOrientationClassify` | Enable 0/90/180/270 rotation detection |
| `--unwarping` | `useDocUnwarping` | Enable wrinkle/skew correction |
| `--chart-recognition` | `useChartRecognition` | Enable chart-to-table parsing |

Layout detection:

| Parameter | API field | Meaning |
|---|---|---|
| `--layout-detection BOOL` | `useLayoutDetection` | Enable/disable layout detection (API default if omitted) |
| `--layout-threshold FLOAT` | `layoutThreshold` | Region filter threshold |
| `--layout-nms BOOL` | `layoutNms` | Enable NMS post-processing |
| `--layout-unclip-ratio FLOAT` | `layoutUnclipRatio` | Expansion ratio |
| `--layout-merge-mode STR` | `layoutMergeBboxesMode` | Overlap box merge mode |
| `--layout-shape-mode STR` | `layoutShapeMode` | Geometry: `rect`/`quad`/`poly`/`auto` |

VL model tuning:

| Parameter | API field | Meaning |
|---|---|---|
| `--prompt-label STR` | `promptLabel` | Prompt type: `ocr`/`formula`/`table`/`chart` (layout-off only) |
| `--repetition-penalty FLOAT` | `repetitionPenalty` | Increase when text repeats |
| `--temperature FLOAT` | `temperature` | Decrease for stability, increase if missing content |
| `--top-p FLOAT` | `topP` | Decrease for more conservative results |
| `--min-pixels FLOAT` | `minPixels` | Minimum image pixel count |
| `--max-pixels FLOAT` | `maxPixels` | Maximum image pixel count |

Output formatting:

| Parameter | API field | Meaning |
|---|---|---|
| `--show-formula-number BOOL` | `showFormulaNumber` | Include formula numbers in Markdown |
| `--restructure-pages BOOL` | `restructurePages` | Restructure multi-page results |
| `--merge-tables BOOL` | `mergeTables` | Merge cross-page tables (layout-off only) |
| `--relevel-titles BOOL` | `relevelTitles` | Identify heading levels (layout-off only) |
| `--prettify-markdown BOOL` | `prettifyMarkdown` | Prettify Markdown output |

## Validation

After conversion:

1. Confirm `{stem}_paddle.md` exists and is nonempty.
2. Confirm `{stem}_paddle/jsonl.jsonl` exists and contains page-level parsing results.
3. Confirm local image references in Markdown point to `{stem}_paddle/img/...` when images are present.
4. Confirm referenced local image files exist.
5. Confirm the Markdown is long enough for the source PDF and includes expected major sections such as References or Bibliography when the PDF is an academic paper.
6. For layout-dependent tasks, confirm the raw JSONL includes layout parsing fields before using it for cropping or block analysis.
7. For split PDFs (>100 pages), confirm the merged Markdown covers the full page range and that no `{stem}_tmp/` directory remains.
