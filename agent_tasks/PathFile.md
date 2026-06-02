# Project File Structure

```
useful-skills/
├── .claude/
│   └── skills/
│       ├── do-agent-brainstorm/
│       │   └── SKILL.md                    # Multi-stage brainstorming workflow
│       ├── econ-llm-memo-paper/
│       │   ├── SKILL.md                    # LLM-based paper memo generation
│       │   ├── references/                 # API configs and documentation
│       │   └── scripts/                    # Python scripts for memo generation
│       ├── econ-memo-paper/
│       │   ├── SKILL.md                    # Direct paper memo writing
│       │   └── references/                 # Memo format guidelines
│       ├── econ-pre/
│       │   └── SKILL.md                    # Complete presentation workflow
│       ├── econ-pre-agent/
│       │   └── SKILL.md                    # Agentic presentation workflow
│       ├── econ-slides-beamer/
│       │   ├── SKILL.md                    # Beamer slides with 7 themes
│       │   └── assets/                     # Theme files and templates
│       ├── econ-top5-referee/
│       │   ├── SKILL.md                    # Top 5 journal referee reports
│       │   ├── agents/                     # OpenAI agent config
│       │   └── references/                 # Journal guidelines
│       ├── mineru-pdf-crop/
│       │   ├── SKILL.md                    # PDF figure/table cropping
│       │   └── scripts/                    # Cropping scripts
│       ├── mineru-pdf-re/
│       │   ├── SKILL.md                    # MinerU PDF conversion
│       │   └── scripts/                    # Conversion scripts
│       └── paddle-pdf-re/
│           ├── SKILL.md                    # PaddleOCR-VL PDF conversion
│           └── scripts/                    # Async OCR scripts
├── agent_tasks/
│   ├── ChangeLog.md                        # Version change log
│   ├── PathFile.md                         # This file - project structure
│   └── Walkthrough.md                      # Project walkthrough and reflection
├── AGENTS.md                               # Symlink to CLAUDE.md
├── CLAUDE.md                               # Project instructions and guidelines
├── INDEX.md                                # English skill index
├── INDEX_zh.md                             # Chinese skill index
├── README.md                               # English README
└── README_zh.md                            # Chinese README
```

## File Descriptions

### Root Files
- `CLAUDE.md`: Main project instructions for Claude Code, including push guidelines, privacy checks, and version control rules
- `AGENTS.md`: Symlink to CLAUDE.md for agent compatibility
- `README.md`: English documentation translated from README_zh.md
- `README_zh.md`: Chinese documentation maintained by user
- `INDEX.md`: English skill index with descriptions and structure
- `INDEX_zh.md`: Chinese skill index

### `.claude/skills/econ-slides-beamer/`
- `SKILL.md`: Complete documentation for the econ-slides-beamer skill, including usage instructions, theme descriptions, and quality checklist
- `assets/`: Contains 7 theme style files (.sty) and 7 corresponding template files (.tex)

### `agent_tasks/`
- `ChangeLog.md`: Tracks all version changes with dates
- `PathFile.md`: This file - documents project structure
- `Walkthrough.md`: Detailed walkthrough of project execution and reflection
