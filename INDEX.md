# Skills Index

## do-agent-brainstorm

- description: Use this skill when the user asks to '/do-agent-brainstorm'. Combines do-agent's output control with multi-agent-brainstorming's structured review process. Runs a multi-stage brainstorming workflow with full file-based tracking: plans, role reviews, decision logs, and final deliverables all saved to a temporary working directory.
- author: WZM

## econ-llm-memo-paper

- description: Generate structured economics paper memos using external LLM APIs (Ark/Doubao, Bailian, ModelScope, SiliconFlow, Volcano Engine). Supports batch processing and multiple output formats.
- author: WZM
- structure:

```
.claude/skills/econ-llm-memo-paper/
├── SKILL.md                    # Skill documentation
├── references/                 # API configuration files
│   ├── Ark-Doubao-API.md       # Ark/Doubao API documentation
│   ├── README_Ark-Doubao.md    # Ark/Doubao setup guide
│   ├── bailian_config.json     # Bailian API config
│   ├── modelscope_config.json  # ModelScope API config
│   ├── siliconflow_config.json # SiliconFlow API config
│   └── volcano_engine_config.json # Volcano Engine config
└── scripts/                    # Python scripts
    ├── memo_paper_single.py    # Single paper memo generation
    └── memo_papers.py          # Batch paper memo generation
```

## econ-memo-paper

- description: Write structured economics paper memos directly inside the current workflow without calling external LLM APIs. Use when the user asks for an academic paper memo, presentation memo, reading memo, Chinese or English economics paper summary, or internal memo from a paper.
- author: WZM
- structure:

```
.claude/skills/econ-memo-paper/
├── SKILL.md                    # Skill documentation
└── references/
    └── memo_format.md          # Memo format guidelines
```

## econ-pre

- description: Complete workflow for producing academic economics paper presentations: read paper, generate memo, research authors, create LaTeX beamer slides, write Chinese speaker notes, and iterate on revisions.
- author: WZM

## econ-pre-agent

- description: Agentic workflow for preparing economics paper presentation materials, including paper reading, memo routing, author research, LaTeX beamer slides, Chinese speaker notes as DOCX via the docx skill, optional extensions, and optional referee reports.
- author: WZM

## econ-slides-beamer

- description: Generate and compile academic economics Beamer slides with revised built-in themes: RedU, Qing, PurpleU, BlueU, GreenU, MorandiCool, and MorandiWarm.
- author: WZM
- structure:

```
.claude/skills/econ-slides-beamer/
├── SKILL.md                    # Skill documentation and usage guide
└── assets/
    ├── BlueU.sty               # BlueU theme style file
    ├── GreenU.sty              # GreenU theme style file
    ├── MorandiCool.sty         # MorandiCool theme style file
    ├── MorandiWarm.sty         # MorandiWarm theme style file
    ├── PurpleU.sty             # PurpleU theme style file
    ├── Qing.sty                # Qing theme style file
    ├── RedU.sty                # RedU theme style file
    ├── template-blueu.tex      # BlueU theme template
    ├── template-greenu.tex     # GreenU theme template
    ├── template-morandicool.tex # MorandiCool theme template
    ├── template-morandiwarm.tex # MorandiWarm theme template
    ├── template-purpleu.tex    # PurpleU theme template
    ├── template-qing.tex       # Qing theme template
    └── template-redu.tex       # RedU theme template
```

## econ-top5-referee

- description: Draft Top 5 economics journal referee reports, editor cover letters, editor-led decision memos, and journal-specific review packages for AER, QJE, RES/REStud, JPE, and ECTA/Econometrica.
- author: WZM
- structure:

```
.claude/skills/econ-top5-referee/
├── SKILL.md                    # Skill documentation
├── agents/
│   └── openai.yaml             # OpenAI agent configuration
└── references/
    ├── aea_referee_guideline.md # AEA referee guidelines
    ├── editor_role_guidance.md  # Editor role guidance
    └── top5_journal_guidance.md # Top 5 journal guidance
```

## mineru-pdf-crop

- description: Crop figures, charts, and tables from the original PDF as standalone PDF files using MinerU Precision Extract layout information. Depends on mineru-pdf-re for layout extraction.
- author: WZM
- structure:

```
.claude/skills/mineru-pdf-crop/
├── SKILL.md                    # Skill documentation
└── scripts/
    └── mineru_pdf_crop.py      # PDF cropping script
```

## mineru-pdf-re

- description: MinerU PDF conversion workflow using official API docs. Supports Precision Extract (full zip) and Agent Lightweight (Markdown only) modes.
- author: WZM
- structure:

```
.claude/skills/mineru-pdf-re/
├── SKILL.md                    # Skill documentation
└── scripts/
    ├── run_mineru_agent_light.py # Lightweight conversion script
    └── run_mineru_precision.py   # Precision extraction script
```

## paddle-pdf-re

- description: PaddleOCR-VL-1.6 async API PDF to Markdown conversion. Supports batch processing with per-PDF output folders containing images and JSON.
- author: WZM
- structure:

```
.claude/skills/paddle-pdf-re/
├── SKILL.md                    # Skill documentation
└── scripts/
    └── run_paddle_ocr_async.py # Async OCR conversion script
```
