# My Agent Skills Collection

> This is a subjective retrospective overview. Also see the AI-assisted, comprehensive and concise [INDEX](INDEX.md)

## Core Infrastructure

### OCR: `/mineru-pdf-re` and `/paddle-pdf-re`

- OCR is the most important prerequisite for sharing human-readable knowledge (mostly in PDF / Office document format) with agents. [MinerU](https://mineru.net/) and [PaddleOCR](https://aistudio.baidu.com/paddleocr) are currently the two most powerful OCR tools
- Both provide official MCP tools, but they are not very user-friendly. So I built two skills based on reusable scripts written with reference to their official API documentation
- Prerequisites: Go to the official websites of both projects, obtain API Keys, and set them as environment variables `MINERU_API_KEY` and `PADDLE_API_KEY` respectively, e.g.

  - Windows: Set environment variables in cmd

    ```
    setx MINERU_API_KEY "your-api-key"
    ```

    Verify

    ```
    echo %MINERU_API_KEY%
    ```
  - For other systems, please adapt (with AI assistance). Contributions are welcome
- Updated periodically: `scripts` may need adjustments to accommodate model and API interface updates
- Comparison of the two OCR tools

  > Purely subjective experience. Objectively, benchmarks are basically neck and neck, and I look forward to their continued competition
  >
  > Via official API model calls, as of `MinerU2.5-Pro-2605-1.2B` and `PaddleOCR-VL-1.6-0.9B`
  >

  - MinerU

    - Accuracy seems slightly better, especially for complex mathematical formulas, charts, annotations, and cross-page content
    - Multi-level headings, multi-level lists and other "nested" structures still require post-processing
    - API calls have stricter [quotas](https://mineru.net/apiManage/token): 5000 documents per day, priority parsing for 1000 pages (long queues after exceeding)
  - PaddleOCR

    - Recognition accuracy meets most needs, and is slightly faster
    - Sometimes correctly handles multi-level headings and multi-level lists (sometimes still needs post-processing), but has limited support for cross-page content (initial returned content still seems to be page-by-page recognition) and annotations; complex mathematical formulas sometimes produce unclosed LaTeX syntax
    - API call [quotas](https://ai.baidu.com/ai-doc/AISTUDIO/Xmjclapam) are more lenient: basic (apparently) 3000 pages/day (returns `429` error after exceeding); free [application](https://paddle.wjx.cn/vm/mePnNLR.aspx#) for upgrade increases to at least 20000 pages/day

### LaTeX Beamer: `/econ-slides-beamer`

- This skill can be considered the starting point of my attempt to create a series of skills

  - Initially, it was just a template modified from the [`PekingU` theme template](https://cn.overleaf.com/latex/templates/pku-beamer-theme-advanced/dwhrsfjszcng) that I had been using for a long time
  - About a week after DeepSeek-V4-Pro was released, I connected it to Claude Code. I found that with just the original text and beamer template and no compilation requirements, it successfully ran and produced a PDF in less than 3 minutes, with more details than the original template (such as defining two new commands `\term` and `\scrpt` for better visual effects). I was so shocked that I sat paralyzed — this workflow was too valuable not to save and reuse. Then through a round of vibe coding, I created a new traditional Chinese cyan color scheme (天青, 青雘, etc.) while maintaining the original template's style
  - Finally, Codex designed and generated several other color schemes, including common university theme color schemes + Morandi cool/warm color schemes
- Although the name includes `econ`, it is by no means limited to this. It can be conveniently used for any academic-style LaTeX Beamer, and you can also embed your own preferred templates. Contributions and co-development are welcome
- Although originally designed for course presentations, it can also be used for other task scenarios

  - Presenting others' papers: recommended to complete within the `/econ-pre` workflow (see below) to aid deeper understanding
  - Presenting your own work: you need to provide agent-readable source text (`.pdf` documents require OCR; usually `.docx` can be read directly by the agent with other tools, or converted to `.md` via MinerU) + an outline (reflecting your own understanding)
- For your own work, if you want "one-sentence generation" of slides, the prompt should at least provide input materials, page limits, and template choice, e.g.

  ```
  First do OCR /paddle-ocr-re on @my-paper.pdf, then based on the OCR results and my images @my/path/figs/, /econ-slides-beamer make a slides `pre.tex`, save to the default path, about 20 pages of content excluding title, table of contents and ending pages, Morandi cool color theme
  ```

## Multi-Task Workflows

### Discussing and Presenting Papers: `/econ-pre`

This is a battle-tested, essentially polished workflow skill. It is essentially a skills router that covers most of the task skills that economics doctoral students need to execute in their daily literature reading

> For (empirical paper) replication, I recommend directly referring to Professor Chen ZHU's [paper-replicate-agent-demo](https://github.com/maxwell2732/paper-replicate-agent-demo)

#### Basic Approach and Functionality

Here I only briefly introduce the basic development and usage approach, and along the way introduce its functionality (/ the skills that receive its task routing)

#### Reference Sources

- The `/do-agent` skill provided by Professor Xueheng LI

### Building a Personal Knowledge Base: `/econ-lib`

Convert course materials, professional books, and papers into a "knowledge base" that facilitates the joint accumulation, maintenance, and use by both human researchers and large model agents

Thanks to the huge progress of current large models in **effective** context windows and "intelligence-cost ratio", and the fact that most needs actually do not require activating too much knowledge, I use a concise index that is more in line with human readers' habits and can also be used by agents, rather than strict RAG — this may be refined later

### Exploring Research Questions: `/econ-idea`

### Writing Literature Reviews: `/econ-lit`

## Acknowledgments

- Thanks to my advisor and senior fellow students for providing tremendous help with AI tool accessibility, and for their continuous support and guidance as I explore the use of AI in learning and research
- Thanks to many contributors of skills and/or harnesses in the open-source community. I hope I have clearly identified the sources of secondary development in the descriptions above
- Thanks to the pioneers who use AI tools to empower economics/social science learning and research, especially Professor Chen ZHU (WeChat Official Account @[遗传社科研究](https://mp.weixin.qq.com/s/QwsYZhy14zspKAznX0OHUA)) and Professor Xueheng LI (WeChat Official Account @[AI and Economics](https://mp.weixin.qq.com/s/MjQyl6hfYaaHStuBSZfZCQ)). Their sharing has brought me much inspiration
- Thanks to the first year of my PhD at PKU (only one year so far!), otherwise I would likely not have had the incentive to explore these efficiency-enhancing tools

## License

[MIT License](LICENSE.md)
