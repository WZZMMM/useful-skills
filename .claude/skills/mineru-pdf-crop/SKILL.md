---
name: mineru-pdf-crop
description: Crop figures, charts, and tables from the original PDF as standalone PDF files using MinerU Precision Extract layout information. Use when a user needs to crop figures/tables/charts from a PDF source, especially for Beamer/report assets, and needs manifests linking source page/coordinates, figure/table number, MinerU image path, and cropped PDF filename. Depends on mineru-pdf-re only when usable MinerU Precision Extract artifacts are not already available.
author: WZM
---
# MinerU PDF Crop

Use this skill when the user needs to crop figures, tables, charts, or other figure-like blocks from the original PDF into independent PDF files. Typical triggers include:

- "提取/裁切 PDF 原文中的图表"
- "extract/crop figures and tables from the PDF"
- "save original paper figures/tables as PDF files"
- "prepare Beamer-ready PDF assets from source figures/tables"

## Relationship With `mineru-pdf-re`

This skill needs MinerU Precision Extract artifacts, but it must not call MinerU again when usable artifacts already exist.

Before running any conversion, check for an existing MinerU output folder for the source PDF. Treat the artifact as usable if it contains:

- `layout.json`
- at least one `*content_list*.json`
- `images/` when image/table/chart entries reference local images

Search these locations first:

```text
Output/ocr/mineru/{pdf_stem}_mineru/
{pdf_parent}/{pdf_stem}_mineru/
```

If a usable folder is found, use it directly and do not call `mineru-pdf-re`.

If no usable folder is found, first use `mineru-pdf-re` in Precision Extract mode for the source PDF. Cropping requires layout JSON and local image metadata, so Agent Lightweight is not sufficient.

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

## Script Naming Rule

When creating or copying the crop script into a project, use exactly:

```text
Output\scripts\mineru_pdf_crop.py
```

Do not create alternate formal crop script names.

## Default Output

By default save cropped PDF assets to:

```text
Output/beamer/img_{original_pdf_stem}_mineru/
```

The output folder includes `manifest.csv`, `manifest.json`, and one cropped PDF per detected `table`, `chart`, or `image`.

## Manifest Fields

Each row records `page`, `source_bbox`, `content_bbox`, `figure_table_number`, `mineru_image`, and `cropped_pdf`.

## Command

```powershell
python Output\scripts\mineru_pdf_crop.py `
  --pdf Input\paper\paper.pdf `
  --mineru-dir Output\ocr\mineru\paper_mineru `
  --output Output\beamer\img_paper_mineru
```

If `--mineru-dir` is omitted, the script searches `Output/ocr/mineru/{stem}_mineru` and the equivalent folder beside the PDF.
