# My Agent Skills Collection

## `econ-slides-beamer`

- This skill can be considered the starting point of my attempt to create a series of skills
- Initially, it was just a template modified from the [`PekingU` theme template](https://cn.overleaf.com/latex/templates/pku-beamer-theme-advanced/dwhrsfjszcng) that I had been using for a long time
- About a week after DeepSeek-V4-Pro was released, I connected it to Claude Code. I found that with just a template and no compilation requirements, it successfully ran and produced a PDF in less than 3 minutes, with more details than the original template (such as defining two new commands `\term` and `\scrpt`). I was so shocked that I sat paralyzed - this workflow was too valuable not to save and reuse. Then through a round of vibe coding, I created a new traditional Chinese cyan color scheme (天青, 青雘, etc.) while maintaining the original template's style
- Finally, I generated several other color schemes in Codex

## `mineru-pdf-re` and `paddle-pdf-re`

- [MinerU](https://mineru.net/) and [PaddleOCR](https://aistudio.baidu.com/paddleocr) are currently the two most powerful OCR tools
- Both provide high-precision PDF-to-Markdown conversion capabilities
- These skills encapsulate their API usage workflows for easy invocation in Claude Code

