# Project File Structure

```
useful-skills/
├── .claude/
│   └── skills/
│       └── econ-slides-beamer/
│           ├── SKILL.md                    # Skill documentation and usage guide
│           └── assets/
│               ├── BlueU.sty               # BlueU theme style file
│               ├── GreenU.sty              # GreenU theme style file
│               ├── MorandiCool.sty         # MorandiCool theme style file
│               ├── MorandiWarm.sty         # MorandiWarm theme style file
│               ├── PurpleU.sty             # PurpleU theme style file
│               ├── Qing.sty                # Qing theme style file
│               ├── RedU.sty                # RedU theme style file
│               ├── template-blueu.tex      # BlueU theme template
│               ├── template-greenu.tex     # GreenU theme template
│               ├── template-morandicool.tex # MorandiCool theme template
│               ├── template-morandiwarm.tex # MorandiWarm theme template
│               ├── template-purpleu.tex    # PurpleU theme template
│               ├── template-qing.tex       # Qing theme template
│               └── template-redu.tex       # RedU theme template
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
