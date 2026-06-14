# 我的智能体技能包

> 这是一份主观的回顾说明，另参见AI辅助生成的、全面而简明的[INDEX](INDEX_zh.md)

## 重要基础设施

### OCR: `/mineru-pdf-re` 和 `/paddle-pdf-re`

- OCR是把人类阅读友好的知识（大多以PDF / Office文档的格式）与智能体共享最重要前提，[MinerU](https://mineru.net/)和[PaddleOCR](https://aistudio.baidu.com/paddleocr)是当前最强大的两款OCR工具。

- 二者官方均提供了MCP工具，但不太好用，于是在参考官方API文档写的可复用脚本基础上，做成了两个skills。

- 前置条件：到两个项目官网，获取API Key，分别设置为环境变量`MINERU_API_KEY`和`PADDLE_API_KEY`，具体如

  - Windows系统：在cmd中，设置环境变量

    ```
    setx MINERU_API_KEY "your-api-key"
    ```

    查看

    ```
    echo %MINERU_API_KEY%
    ```

  - 其他系统请（与AI一起）做适配调整，也欢迎共同完善。

- 不定期更新：需要调整`scripts`以适应模型和API接口的更新。

- 两款OCR工具对比

  > 纯主观经验，客观看benchmark基本上是难分伯仲了，也期待二者继续你追我赶
  >
  > 通过官方API调用模型，截至`MinerU2.5-Pro-2605-1.2B`和`PaddleOCR-VL-1.6-0.9B`

  - MinerU
    - 精确度似乎更好一点，尤其是对复杂的数学公式、图表、注释和跨页内容；
    - 多级标题、多级列表等“嵌套”结构，仍需后处理；
    - API调用有更严格的[配额](https://mineru.net/apiManage/token)：每日5000份，优先解析1000页（超出以后会长时间排队）。

  - PaddleOCR
    - 识别精确度可以满足绝大多数需求，且稍快一点；
    - 有时可以正确处理多级标题、多级列表（有时仍然需要后处理），但对跨页内容（返回的初始内容，似乎仍是分页识别）、注释的支持有限，复杂的数学公式有时出现latex语法不闭合；
    - API调用[配额](https://ai.baidu.com/ai-doc/AISTUDIO/Xmjclapam)更宽松：基础（似乎是）3000页/日（超出以后会报错`429`），免费[申请](https://paddle.wjx.cn/vm/mePnNLR.aspx#)提升后至少20000页/日。

### PDF图片裁切：`mineru-pdf-crop`和`paddle-pdf-crop`

- 基于先进OCR工具的后处理：MinerU和PaddleOCR的副产物均包含提供版面信息的`.json`文件。
- 使用场景：需要论文原文的`.pdf`格式图表，比如用于LaTex Beamer中，希望插入矢量图。
- 本质上是要定位图表边界框。如果没有前置的先进OCR，agent很可能也会试图使用`PyMuPDF`等工具来实现类似的效果，但定位精确度有限，且很难精准、稳健地识别和提取图表标题、注释等附带信息。

### LaTex Beamer: `/econ-slides-beamer`

- 这个技能是我尝试创建一系列技能的起点

  - 最初只有在[`PekingU`主题模板](https://cn.overleaf.com/latex/templates/pku-beamer-theme-advanced/dwhrsfjszcng)基础上修改并长期使用的模板
  - DeepSeek-V4-Pro发布后一周左右的某日，将其接入Claude Code，发现只给原文和beamer模板、没有要求编译，不到3min成功跑通并给出了PDF，且比最初模板有了更多细节（比如定义了 `\term`和 `\scrpt`这两个新命令来实现更好的视觉效果），震惊瘫坐，不保存复用太可惜了；然后一通vibe coding，新建了一个中国传统青色系（天青、青雘等）配色，仍然保持了原模板的样式
  - 最后由Codex设计并生成了其他几种配色方案，包括高校常见主题色系+莫兰迪冷/暖色系

- 虽然命名带`econ`，但完全不局限于此，只要是需要制作学术风格的LaTex Beamer均可便捷实现，也可内置自己偏好的模板，也欢迎共享共建

- 虽然最初是用于应对课程汇报，但也可以用于其他任务场景

  - 汇报他人论文：**建议在`/econ-pre`工作流（见后文）中完成**，以辅助加深理解
  - 汇报自己成果：需要提供智能体可读的原文（`.pdf`文档要OCR；通常对`.docx`智能体可以直接用其他工具读取，也可以调用MinerU转为`.md`）+ 一份大纲（体现自己的理解）

- 对自己的成果，如果想要“一句话生成”slides，建议prompt至少需要提供输入材料、页数限制、模板选择，比如

  ```
  先对 @my-paper.pdf 做OCR /paddle-ocr-re ，然后基于OCR结果和我的图片 @my/path/figs/  ， /econ-slides-beamer 做一份slides `pre.tex`，保存到默认路径下，除标题、目录和结尾页以外的正文在20页左右，莫兰迪冷色主题
  ```

### DOI: `crossref-openalex`



## 多任务工作流

### 讨论和汇报文献：`/econ-pre`

这是一个久经考验、基本上打磨成熟的工作流skill，本质上是一个skills路由，基本上涵盖了经济学博士生日常**读文献**需要执行的各项任务技能

> 除了（实证论文的）复现，建议直接参考朱晨老师的[paper-replicate-agent-demo](https://github.com/maxwell2732/paper-replicate-agent-demo)

#### 基本思路与功能

> 此处仅简要说明基本的开发思路，讨论如何使用（质言之，我试图划定的边界），顺便介绍其功能 （本质上即接收其任务路由的skills）。请参见 [econ-pre-demo]()

做pre是本科生和研究生，对博士生而言

#### 参考来源

- 李学恒老师提供的`/do-agent`技能

### 建立专属知识库：`/econ-lib`

将课程资料、专业书籍和论文，转换为便于人类研究者和大模型智能体共同积累、维护和使用的“知识库”

得益于当前大模型在**有效**上下文窗口和“智价比”的巨大进步，以及大多数需求下实际需要激活的知识并不会太多，使用了更符合人类读者习惯、也能为智能体所用的简明索引，而不是严格的RAG——后续可能会完善这一点

### 探索研究问题：`/econ-idea`

仍在开发测试中

### 写作文献综述：`/econ-lit`

仍在开发测试中

## 致谢

- 感谢我导和师姐师兄，为我在AI工具可得性上提供了巨大的帮助，为我探索学习和科研中的AI使用提供了持续的支持和指导
- 感谢开源社区很多skills 和 / 或 harness的贡献者，我希望在前述说明中已经明确了二次开发的来源
- 感谢使用AI工具赋能经济学/社会科学学习和研究的先行者们，尤其是朱晨老师（微信公众号@[遗传社科研究](https://mp.weixin.qq.com/s/QwsYZhy14zspKAznX0OHUA)）和李学恒老师（微信公众号@[AI and Economics](https://mp.weixin.qq.com/s/MjQyl6hfYaaHStuBSZfZCQ)），ta们的分享给我带来了很多启发
- 感谢在PKU读博第一年（居然才一年！），否则我很可能没有激励去探索这些效率提升工具

## 许可

 [MIT License](LICENSE.md) 
