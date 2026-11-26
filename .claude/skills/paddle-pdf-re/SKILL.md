---
name: paddle-pdf-re
description: PaddleOCR-VL-1.6 async PDF conversion workflow. Prefer this skill by default for PDF-to-Markdown conversion and layout extraction. Produces Markdown with printed-page comments, linked footnotes and local images. Retains raw JSONL or JSON when requested.
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

Keep the bundled `paddle_artifacts.py`, `paddle_folios.py`, `paddle_footnotes.py` and `paddle_appendices.py` alongside the converter. When installing in a new project, copy all five Python files from the skill's `scripts/` into `Output/scripts/`. When updating an existing project-specific converter, retain its output and image paths, apply the shared page renderer before rewriting image links, and classify appendix pages after merging all chunks.

## API Workflow

Use PaddleOCR-VL-1.6 with the async jobs API:

1. Submit the PDF with `POST https://paddleocr.aistudio-app.com/api/v2/ocr/jobs`.
2. Poll job state with `GET https://paddleocr.aistudio-app.com/api/v2/ocr/jobs/{job_id}`.
3. Download the returned JSONL result.
4. Stage the downloaded JSONL for page and footnote extraction.
5. Download referenced images into a local child folder.
6. Merge the annotated pages, rewrite image links, validate the Markdown and local images, and publish the document. Clean up the raw OCR results produced by this conversion after success. Use `--keep-raw` when the user requests raw JSONL, JSON, layout artifacts for later use, or another explicit retention policy.

Recommended payload:

```json
{
  "model": "PaddleOCR-VL-1.6",
  "optionalPayload": {
    "useDocOrientationClassify": false,
    "useDocUnwarping": false,
    "useChartRecognition": false,
    "markdownIgnoreLabels": ["number", "footnote", "header", "header_image", "footer", "footer_image", "aside_text"]
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
{output_dir}/{original_pdf_stem}_paddle/img/
```

Top-level Markdown image references must point to the sibling child folder:

```text
![image]({original_pdf_stem}_paddle/img/img-in-chart-box-001.jpg)
![image]({original_pdf_stem}_paddle/img/img-in-image-box-001.png)
```

All images returned by the API are downloaded and kept, including `img_in_chart_box_*` (charts/graphs), `img_in_image_box_*` (vector graphics, diagrams, mathematical figures), and any other prefixes. All underscores in image filenames are replaced with hyphens (e.g. `img_in_chart_box_001.jpg` becomes `img-in-chart-box-001.jpg`).

Do not leave remote image URLs in the final Markdown when local images were requested or are needed by downstream tasks.

For a completed default conversion, keep the Markdown and image assets. Remove this run's raw JSONL and any raw JSON intermediates created during parsing only after the finished Markdown and image links pass validation. Keep downloaded raw data available if processing fails. Cleanup is scoped to the current conversion. The bundled converter writes its raw output to `{output_dir}/{original_pdf_stem}_paddle/jsonl.jsonl`; `--keep-raw` preserves that file.

### Printed pages and footnotes

Begin every physical page, including blank pages, with a standalone HTML comment followed by a blank line before any content. Use the printed folio visible in the footer or header. For example, a journal article starting on printed page 1741 begins with:

```markdown
<!-- Original PDF p.1741 Begins -->
```

Read the folio from the page layout (`prunedResult.parsing_res_list`). Keep Roman numerals and printed prefixes when recognized. When the printed number is missing, illegible or ambiguous, use `<!-- Original PDF p.unknown Begins -->`. Never substitute the physical page index or interpolate a missing number. Exclude running headers and their images from the visible text.

### PDFs with appendices

Determine the section at the **start of each physical page**. A main-text page begins with `<!-- Original PDF p.{page} Begins -->`. An appendix page begins with `<!-- Original PDF Appendix p.{page} Begins -->`. Put exactly one comment on a line of its own before any page content, including on pages of a standalone appendix PDF. If an appendix starts halfway down a main-text page, keep that page's main-text marker. Mark subsequent pages that begin in the appendix.

Read the printed folio separately for every appendix page. Preserve a restart at 1 as well as numbering that continues from the article, Roman numerals, and printed appendix prefixes such as A-3. For example, in a PDF combining an article and its separately paginated appendix, successive pages may start with:

```markdown
<!-- Original PDF p.277 Begins -->

<!-- Original PDF Appendix p.1 Begins -->
```

When the section is known but the printed appendix folio is missing or ambiguous, write `<!-- Original PDF Appendix p.unknown Begins -->`. A reference to an online appendix in the text or table of contents does not establish an appendix boundary. Use the actual appendix title, page layout, and surrounding pages; check the source PDF when a boundary is ambiguous. A bibliography belonging to a standalone supplement stays in the appendix. For joined attachments, verify the last body page, the first appendix page, and any later return to main material. Footnote IDs remain scoped to the physical page across the whole PDF, including when appendix folios restart.

### Footnotes

The request filters footnotes and running furniture from the service's Markdown. Recover note text from the unfiltered page layout, including footnotes already present in older Markdown payloads. Match an explicit body marker with its note on the same source page, and use standard Markdown references and definitions. Namespace IDs by the physical page's position across all chunks so that repeated printed page numbers or restarted footnote numbers stay distinct. A note with no reliable match stays visible on its source page. Preserve mathematical exponents, citations and table notation during matching. Layout detection should be enabled for material that needs printed pagination or footnotes.

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

# Retain raw page layout when requested
python Output\scripts\run_paddle_ocr_async.py --input paper.pdf --keep-raw

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
| `--keep-raw` | Retain the raw OCR JSONL after successful conversion | off |

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
2. When raw output was requested, confirm `{stem}_paddle/jsonl.jsonl` exists and contains page results. For a successful default run, confirm that its generated raw OCR files have been removed.
3. Confirm local image references in Markdown point to `{stem}_paddle/img/...` when images are present.
4. Confirm referenced local image files exist.
5. Confirm the Markdown is long enough for the source PDF and includes expected major sections such as References or Bibliography when the PDF is an academic paper.
6. For layout-dependent tasks, check layout fields while processing the raw JSONL. Pass `--keep-raw` if the deliverable includes these results.
7. For split PDFs (>100 pages), confirm the merged Markdown covers the full page range and that no `{stem}_tmp/` directory remains.
8. Count page-start comments against the number of page results across every JSONL record and chunk. Spot-check printed folios in the source, including front matter and journal pagination.
9. Confirm each generated footnote reference resolves to one definition. Check restarted numbering, unmatched notes, and that running headers are absent from the visible Markdown.
10. For appendices, check that every page beginning in an appendix has exactly one `<!-- Original PDF Appendix p.{page} Begins -->` marker. Verify its printed folio against the PDF on both sides of each section or pagination change.
