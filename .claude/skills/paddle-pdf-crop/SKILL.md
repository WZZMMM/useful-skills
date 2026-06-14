---
name: paddle-pdf-crop
description: Crop or extract figures, charts, images, and tables from PDF documents as standalone PDF files using PaddleOCR layout recognition results. Trigger when the user asks to crop/extract/get figures, images, charts, or tables from a PDF/document, even if they do not explicitly request PDF output; PDF is the default output format unless the user explicitly asks for JPG. Prefer this skill by default when no OCR/crop backend is specified. Depends on paddle-pdf-re only when usable PaddleOCR artifacts are not already available.
author: WZM
---

# PaddleOCR PDF Crop

Use this skill when the user needs to crop, extract, get, prepare, or save figures, images, charts, tables, or other figure-like/table-like blocks from a PDF document into independent files, using PaddleOCR recognition results.

Trigger this skill even when the user only says they need the paper's "图", "表", "图表", "figures", "tables", "charts", "images", "visuals", or "Beamer-ready assets" from a PDF/document. The user does not need to explicitly say the output should be PDF.

Output format rule:

- Default output is cropped **PDF** files, preserving vector content where possible.
- Only produce JPG/PNG images when the user explicitly asks for JPG/PNG/raster image output.

Backend routing rule:

- If the user explicitly says PaddleOCR or `paddle-pdf-crop`, use this skill.
- If the user explicitly says MinerU or `mineru-pdf-crop`, use `mineru-pdf-crop`.
- If the user asks for PDF/document figure/table cropping or extraction without naming a backend, prefer this skill.

Typical triggers include:

- "提取/裁切 PDF 原文中的图表（PaddleOCR）"
- "提取论文里的图和表"
- "把文档中的图表裁出来"
- "extract/crop figures and tables using PaddleOCR results"
- "get the paper figures and tables"
- "prepare Beamer-ready assets from the PDF"
- "crop tables from PaddleOCR JSONL"

## Relationship With `paddle-pdf-re`

This skill needs PaddleOCR recognition artifacts, but it must not call PaddleOCR again when usable artifacts already exist.

Before running any conversion, check for an existing PaddleOCR output folder for the source PDF. Treat the artifact as usable if it contains:

- `jsonl.jsonl`

Search these locations first:

```text
Output/ocr/paddle/{pdf_stem}_paddle/
{pdf_parent}/{pdf_stem}_paddle/
```

If a usable folder is found, use it directly and do not call `paddle-pdf-re`.

If no usable folder is found, first use `paddle-pdf-re` for the source PDF.

Expected PaddleOCR output:

```text
Output/ocr/paddle/{pdf_stem}_paddle/
├─jsonl.jsonl
├─img/
└─{pdf_stem}_paddle.md
```

## How It Works

PaddleOCR outputs **flat, spatially independent blocks** with distinct labels:

- `figure_title` — table/figure caption
- `table` — table body
- `chart` — figure/image body
- `vision_footnote` — table/figure notes

Unlike MinerU's nested structure, these blocks must be **grouped by spatial proximity**:

1. **Title→Body matching**: Each `table`/`chart` is assigned to the nearest `figure_title` above it (within 60 px tolerance)
2. **Orphan body absorption**: Bodies without a title are absorbed into the nearest group above if no intervening title exists (handles multi-panel tables like Table 16)
3. **Footnote→Body matching**: Each `vision_footnote` is assigned to the nearest body above it (within 80 px tolerance)
4. **Union bbox**: All matched blocks' coordinates are merged into a single bounding box

Coordinates are in pixels (144 DPI) and must be scaled to PDF points (72 DPI) using `scale = pdf_size / paddle_size ≈ 0.5`.

For detailed algorithm documentation, see `Output/docs/ocr-crop.md`.

## Script Naming Rule

When creating or copying the crop script into a project, use exactly:

```text
Output\scripts\extract_and_crop_paddle.py
```

## Default Output

By default save to the PaddleOCR output directory alongside the original recognition results:

```text
Output/ocr/paddle/{pdf_stem}_paddle/
├─{pdf_stem}_paddle_tables.csv
├─{pdf_stem}_paddle_charts.csv
├─manifest.json
├─tables/
│  ├─{pdf}_p{page}_{idx}_table_{fignum}.pdf
│  └─...
└─charts/
   ├─{pdf}_p{page}_{idx}_chart_{fignum}.pdf
   └─...
```

## CSV Fields

Each row records: `index`, `page_idx`, `figure_number`, `union_bbox`, `body_bboxes`, `caption_bbox`, `footnote_bbox`, `caption_text`, `footnote_text`.

Note: `body_bboxes` is a JSON array (may contain multiple entries for multi-panel tables).

## Command

```powershell
python Output\scripts\extract_and_crop_paddle.py `
  --pdf Input\paper\paper.pdf `
  --jsonl Output\ocr\paddle\{stem}_paddle\jsonl.jsonl `
  --output Output\ocr\paddle\{stem}_paddle `
  --margin 2.0
```

If `--jsonl` is omitted, the script searches `Output/ocr/paddle/{stem}_paddle/jsonl.jsonl`.
