# 技能索引

## do-agent-brainstorm

- description: 当用户请求 '/do-agent-brainstorm' 时使用此技能。结合 do-agent 的输出控制和 multi-agent-brainstorming 的结构化审查流程。运行多阶段头脑风暴工作流，包含完整的文件跟踪：计划、角色审查、决策日志和最终交付物。
- author: WZM

## crossref-openalex

- description: 综合利用 CrossRef 和 OpenAlex 将论文参考文献列表转换为带唯一标识符的 .md、.json 和 .ris 文件。通过 CrossRef 和 OpenAlex API 为 OCR 提取的参考文献添加 DOI、ISBN、URL 标识符。
- author: WZM
- structure:

```
.claude/skills/crossref-openalex/
├── SKILL.md                    # 技能文档
├── assets/                     # （保留）
├── references/
│   └── api_reference.md        # CrossRef 和 OpenAlex API 参考
└── scripts/
    ├── generate_v31.py         # 主交付物生成器（MD/JSON/RIS）
    └── search_unmatched.py     # OpenAlex 搜索未匹配参考文献
```

## econ-llm-memo-paper

- description: 使用外部 LLM API（Ark/豆包、百炼、ModelScope、SiliconFlow、火山引擎）生成结构化经济学论文备忘录。支持批量处理和多种输出格式。
- author: WZM
- structure:

```
.claude/skills/econ-llm-memo-paper/
├── SKILL.md                    # 技能文档
├── references/                 # API 配置文件
│   ├── Ark-Doubao-API.md       # Ark/豆包 API 文档
│   ├── README_Ark-Doubao.md    # Ark/豆包 设置指南
│   ├── bailian_config.json     # 百炼 API 配置
│   ├── modelscope_config.json  # ModelScope API 配置
│   ├── siliconflow_config.json # SiliconFlow API 配置
│   └── volcano_engine_config.json # 火山引擎配置
└── scripts/                    # Python 脚本
    ├── memo_paper_single.py    # 单篇论文备忘录生成
    └── memo_papers.py          # 批量论文备忘录生成
```

## econ-memo-paper

- description: 在当前工作流中直接编写结构化经济学论文备忘录，无需调用外部 LLM API。当用户请求学术论文备忘录、演示备忘录、阅读笔记、中英文经济学论文摘要时使用。
- author: WZM
- structure:

```
.claude/skills/econ-memo-paper/
├── SKILL.md                    # 技能文档
└── references/
    └── memo_format.md          # 备忘录格式指南
```

## econ-pre

- description: 完整的智能体工作流，用于准备经济学论文演示材料：论文阅读、备忘录路由、作者研究、通过 econ-slides-beamer 生成 LaTeX Beamer 幻灯片、通过 docx 技能生成中文演讲备注 DOCX、可选扩展和通过 econ-top5-referee 生成审稿报告。
- author: WZM

## econ-slides-beamer

- description: 使用修订版内置主题（RedU、Qing、PurpleU、BlueU、GreenU、MorandiCool 和 MorandiWarm）生成和编译学术 LaTeX Beamer 幻灯片。
- author: WZM
- structure:

```
.claude/skills/econ-slides-beamer/
├── SKILL.md                    # 技能文档和使用指南
└── assets/
    ├── BlueU.sty               # BlueU 主题样式文件
    ├── GreenU.sty              # GreenU 主题样式文件
    ├── MorandiCool.sty         # MorandiCool 主题样式文件
    ├── MorandiWarm.sty         # MorandiWarm 主题样式文件
    ├── PurpleU.sty             # PurpleU 主题样式文件
    ├── Qing.sty                # Qing 主题样式文件
    ├── RedU.sty                # RedU 主题样式文件
    ├── template-blueu.tex      # BlueU 主题模板
    ├── template-greenu.tex     # GreenU 主题模板
    ├── template-morandicool.tex # MorandiCool 主题模板
    ├── template-morandiwarm.tex # MorandiWarm 主题模板
    ├── template-purpleu.tex    # PurpleU 主题模板
    ├── template-qing.tex       # Qing 主题模板
    ├── template-redu.tex       # RedU 主题模板
    └── fig/
        └── fig1.pdf            # 示例 treatment-control 图
```

## econ-top5-referee

- description: 起草 Top 5 经济学期刊审稿报告、编辑封面信、编辑主导的决策备忘录和特定期刊评审包，覆盖 AER、QJE、RES/REStud、JPE 和 ECTA/Econometrica。
- author: WZM
- structure:

```
.claude/skills/econ-top5-referee/
├── SKILL.md                    # 技能文档
├── agents/
│   └── openai.yaml             # OpenAI 智能体配置
└── references/
    ├── aea_referee_guideline.md # AEA 审稿指南
    ├── editor_role_guidance.md  # 编辑角色指南
    └── top5_journal_guidance.md # Top 5 期刊指南
```

## mineru-pdf-crop

- description: 使用 MinerU 精确提取的布局信息，从原始 PDF 中裁剪图表和表格为独立 PDF 文件。依赖 mineru-pdf-re 进行布局提取。
- author: WZM
- structure:

```
.claude/skills/mineru-pdf-crop/
├── SKILL.md                    # 技能文档
└── scripts/
    ├── extract_and_crop_mineru.py # 基于 MinerU 布局的 PDF 裁剪脚本
    └── mineru_pdf_crop.py      # PDF 裁剪脚本
```

## mineru-pdf-re

- description: 使用官方 API 文档的 MinerU PDF 转换工作流。支持精确提取（完整 zip）和智能体轻量级（仅 Markdown）模式。
- author: WZM
- structure:

```
.claude/skills/mineru-pdf-re/
├── SKILL.md                    # 技能文档
├── references/
│   └── MinerU-API-Doc.md       # MinerU 云端解析 API 文档
└── scripts/
    ├── run_mineru_agent_light.py # 轻量级转换脚本
    └── run_mineru_precision.py   # 精确提取脚本
```

## paddle-pdf-crop

- description: 使用 PaddleOCR 布局识别结果，从 PDF 文档中裁剪或提取图表、图片和表格为独立 PDF 文件。依赖 paddle-pdf-re 进行布局提取。
- author: WZM
- structure:

```
.claude/skills/paddle-pdf-crop/
├── SKILL.md                    # 技能文档
└── scripts/
    └── extract_and_crop_paddle.py # 基于 PaddleOCR 布局的 PDF 裁剪脚本
```

## paddle-pdf-re

- description: PaddleOCR-VL-1.6 异步 API PDF 转 Markdown 技能。支持批量转换，每个 PDF 输出一个带图片和 JSON 的子文件夹。
- author: WZM
- structure:

```
.claude/skills/paddle-pdf-re/
├── SKILL.md                    # 技能文档
├── references/
│   ├── PaddleOCR-VL-1.5_API-Doc.md # PaddleOCR-VL-1.5 API 文档
│   └── PaddleOCR-VL-1.6_API-Doc.md # PaddleOCR-VL-1.6 API 文档
└── scripts/
    └── run_paddle_ocr_async.py # 异步 OCR 转换脚本
```
