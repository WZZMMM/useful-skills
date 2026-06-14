---
name: mineru-pdf-crop
description: Crop or extract figures, charts, images, and tables from PDF documents as standalone PDF files using MinerU Precision Extract layout information. Trigger when the user explicitly asks to use MinerU/MinerU crop, or when existing MinerU artifacts should be reused. PDF is the default output format unless the user explicitly asks for JPG. Extracts nested sub-blocks (caption, body, footnote) from layout.json, computes union bbox, and crops complete regions including surrounding titles and notes. Depends on mineru-pdf-re only when usable MinerU Precision Extract artifacts are not already available.
author: WZM
---

# MinerU PDF Crop

Use this skill when the user needs to crop, extract, get, prepare, or save figures, images, charts, tables, or other figure-like/table-like blocks from a PDF document into independent files, and MinerU is explicitly requested or already the required artifact source.

Trigger this skill when:

- The user explicitly says MinerU or `mineru-pdf-crop`.
- Existing project materials already depend on MinerU `layout.json` / Precision Extract output.
- PaddleOCR is unavailable, unsuitable, or explicitly rejected and MinerU is the chosen fallback.

If the user asks for PDF/document figure/table cropping or extraction without naming a backend, prefer `paddle-pdf-crop`.

The user does not need to explicitly say the output should be PDF. Default output is cropped **PDF** files, preserving vector content where possible. Only produce JPG/PNG images when the user explicitly asks for JPG/PNG/raster image output.

Typical triggers include:

- "提取/裁切 PDF 原文中的图表"
- "用 MinerU 提取论文里的图和表"
- "把 MinerU layout 里的表格裁出来"
- "extract/crop figures and tables from the PDF"
- "crop figures and tables using MinerU"
- "save original paper figures/tables as PDF files"
- "prepare Beamer-ready PDF assets from source figures/tables"

## Relationship With `mineru-pdf-re`

This skill needs MinerU Precision Extract artifacts, but it must not call MinerU again when usable artifacts already exist.

Before running any conversion, check for an existing MinerU output folder for the source PDF. Treat the artifact as usable if it contains:

- `layout.json`

Search these locations first:

```text
Output/ocr/mineru/{pdf_stem}_mineru/
{pdf_parent}/{pdf_stem}_mineru/
```

If a usable folder is found, use it directly and do not call `mineru-pdf-re`.

If no usable folder is found, first use `mineru-pdf-re` in Precision Extract mode for the source PDF.

Expected MinerU precision output:

```text
Output/ocr/mineru/{pdf_stem}_mineru/
├─full.md
├─layout.json
├─*_content_list.json
├─*_content_list_v2.json
├─*_model.json
└─images/
```

## How It Works

The script reads MinerU's `layout.json`, which organizes tables and charts as **nested containers**. Each `table` or `chart` block contains sub-blocks:

- `table_caption` / `chart_caption` — title with its own bbox
- `table_body` / `chart_body` — main content with its own bbox
- `table_footnote` — notes with their own bbox (may have multiple)

The script computes the **union bbox** of all sub-blocks to get the complete region (title + body + notes), then crops from the original PDF.

For detailed algorithm documentation, see `Output/docs/ocr-crop.md`.

## Script Naming Rule

When creating or copying the crop script into a project, use exactly:

```text
Output\scripts\extract_and_crop_mineru.py
```

## Default Output

By default save to the MinerU OCR output directory alongside the original recognition results:

```text
Output/ocr/mineru/{pdf_stem}_mineru/
├─{pdf_stem}_mineru_tables.csv
├─{pdf_stem}_mineru_charts.csv
├─manifest.json
├─tables/
│  ├─{pdf}_p{page}_{idx}_table_{fignum}.pdf
│  └─...
└─charts/
   ├─{pdf}_p{page}_{idx}_chart_{fignum}.pdf
   └─...
```

## CSV Fields

Each row records: `index`, `page_idx`, `figure_number`, `union_bbox`, `body_bbox`, `caption_bbox`, `footnote_bbox`, `caption_text`, `footnote_text`.

## Command

```powershell
python Output\scripts\extract_and_crop_mineru.py `
  --pdf Input\paper\paper.pdf `
  --layout Output\ocr\mineru\{stem}_mineru\layout.json `
  --output Output\ocr\mineru\{stem}_mineru `
  --margin 2.0
```

If `--layout` is omitted, the script searches `Output/ocr/mineru/{stem}_mineru/layout.json`.
