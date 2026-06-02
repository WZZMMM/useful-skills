---
name: econ-slides-beamer
description: "Generate and compile academic economics Beamer slides with revised built-in themes: RedU, Qing, PurpleU, BlueU, GreenU, MorandiCool, and MorandiWarm. "
author: WZM
---
# Econ Slides Beamer

Generate complete LaTeX Beamer presentations from structured economics-paper content using an expanded revised theme set.

## Overview

Use this skill to:

- create seminar slides from a paper, memo, outline, or prior Beamer source;
- generate one selected theme or multiple theme variants for comparison;
- compile Beamer decks with XeLaTeX;
- preserve a no-footer style while retaining the top smoothbars navigation strip;
- place PDF figures and tables on bounded plain frames.

Required toolchain:

- XeLaTeX
- `ctex`, `xeCJK`, `fontspec`
- PDF figure/table assets when visual pages are required

## Step 0: Pre-Flight

Confirm:

| Item             | Check                                                         |
| ---------------- | ------------------------------------------------------------- |
| Content source   | Paper text, memo, structured notes, or existing Beamer source |
| Figures/tables   | PDF assets in `fig/` or another known directory             |
| Presenter info   | Name, affiliation, and contact line for title/ending pages    |
| Theme request    | One theme or all revised themes                               |
| Output directory | Usually `Output/beamer/<deck-name>/`                        |
| Compiler         | XeLaTeX available                                             |

If a prior Beamer source already exists, preserve its content structure unless the user requests rewriting.

## Step 1: Choose Theme and Copy Assets

Available resources:

| Theme       | .sty file           | Template                     | Palette                                               |
| ----------- | ------------------- | ---------------------------- | ----------------------------------------------------- |
| RedU        | `RedU.sty`        | `template-redu.tex`        | red university theme; red/deep red/warm gray; no blue |
| Qing        | `Qing.sty`        | `template-qing.tex`        | traditional Chinese*tian qing* (天青) palette       |
| PurpleU     | `PurpleU.sty`     | `template-purpleu.tex`     | purple academic palette                               |
| BlueU       | `BlueU.sty`       | `template-blueu.tex`       | formal blue academic palette                          |
| GreenU      | `GreenU.sty`      | `template-greenu.tex`      | green academic palette                                |
| MorandiCool | `MorandiCool.sty` | `template-morandicool.tex` | cool Morandi palette; deep warm emphasis              |
| MorandiWarm | `MorandiWarm.sty` | `template-morandiwarm.tex` | warm Morandi palette; deep cool emphasis              |

Copy assets:

```text
assets/{Theme}.sty -> {output_dir}/{Theme}.sty
assets/template-{theme_lower}.tex -> {output_dir}/{filename}.tex
```

For a comparison run, generate one source per theme:

```text
main-RedU.tex
main-Qing.tex
main-PurpleU.tex
main-BlueU.tex
main-GreenU.tex
main-MorandiCool.tex
main-MorandiWarm.tex
```

## Step 2: Preamble and Fonts

Use the selected template preamble. It defines the original typography system:

- English/main font: Times New Roman
- Main CJK font: KaiTi
- `\HeiTi`: SimHei
- `\FangSong`: STFangsong
- `\huawenxingkai`: STXingkai
- `\yasong`: FZYaSong-DB-GBK
- `\yankai`: Slideqiuhong Regular
- `\chalkd`: Times New Roman with AutoFakeBold, used for normal/alert/frame-title text

Do not replace this font stack unless the user explicitly requests a typography revision.

## Step 3: Navigation and Footer

The revised themes must:

- retain the top smoothbars navigation strip through `\useoutertheme[footline=authorinstitutetitle]{smoothbars}`;
- remove the bottom footer through `\setbeamertemplate{footline}{}`;
- not remove the navigation bar.

Do not add a manual footer.

## Step 4: Commands

Every template defines:

| Command         | Use                                                     |
| --------------- | ------------------------------------------------------- |
| `\term{...}`  | content emphasis: key mechanisms, findings, and numbers |
| `\scrpt{...}` | parenthetical citations only                            |

Use `\term{}` for emphasis. Do not use `\scrpt{}` for ordinary emphasis.

## Step 5: Frame Structure

Recommended order:

1. Title page
2. `\section{Overview}`
3. Authors frame
4. Overview frame with `\textbf{Research question}`, `\textbf{Context}`, and `\textbf{Key finding}`
5. Three to six substantive sections
6. One ending page

When adapting an existing deck, check that there is exactly one ending page and exactly one `\end{document}`.

## Step 6: Figures and Tables

Use one PDF asset per plain frame:

```latex
\begin{frame}[plain]
\centering
\includegraphics[width=0.88\paperwidth,height=0.86\paperheight,keepaspectratio]{fig/example.pdf}
\end{frame}
```

Rules:

- one figure/table per page;
- no captions, numbers, or notes on figure/table pages;
- place figures/tables by semantic mention order in the paper;
- if an asset still looks too large, reduce to `width=0.84\paperwidth,height=0.82\paperheight`.

## Step 7: Title and Ending Pages

Title page follows the selected template:

```latex
\author{AuthorLine \\ (\textit{Journal}, Year)}
\title{\textbf{Title}}
\subtitle{}
\institute{汇报人：{ \yankai 方鸿渐}}
\date{\today}
```

Each template includes a complete ending page. Keep only one:

```latex
% ============================================================
% FIN
% ============================================================
\begin{frame}[plain]
    \begin{center}
\vspace{3em}
{\LARGE \color{themeaccent}\textbf{Thank You for Your Attention!}}

\vspace{3em}

{\color{halfgray}
{\yankai 方鸿渐}
\footnotesize
\quad 克莱登大学\ 哲学博士 \quad | \quad
Clayton University\ PhD \\
微信：fanghongjian1898 \quad 邮箱：\texttt{fanghongjian1898@clayton.edu}
}
    \end{center}
\end{frame}
```

## Step 8: Compile

Run twice:

```bash
cd <output_dir>
xelatex -interaction=nonstopmode -halt-on-error main-Theme.tex
xelatex -interaction=nonstopmode -halt-on-error main-Theme.tex
```

Save logs under `Output/logs/`.

## Quality Checklist

- [ ] Correct theme `.sty` copied
- [ ] Matching template or generated source uses the revised preamble
- [ ] Bottom footer removed
- [ ] Smoothbars navigation retained
- [ ] Exactly one ending page
- [ ] Every figure/table frame uses `[plain]`
- [ ] Figure/table dimensions are bounded with `keepaspectratio`
- [ ] `\term{}` used for content emphasis
- [ ] `\scrpt{}` used only for citations
- [ ] XeLaTeX compiles successfully twice

## Assets

- `assets/RedU.sty`, `assets/template-redu.tex`
- `assets/Qing.sty`, `assets/template-qing.tex`
- `assets/PurpleU.sty`, `assets/template-purpleu.tex`
- `assets/BlueU.sty`, `assets/template-blueu.tex`
- `assets/GreenU.sty`, `assets/template-greenu.tex`
- `assets/MorandiCool.sty`, `assets/template-morandicool.tex`
- `assets/MorandiWarm.sty`, `assets/template-morandiwarm.tex`
