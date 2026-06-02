# 火山引擎 (Ark) Doubao API 使用说明

## 概述

本文档介绍如何使用火山引擎方舟 (Ark) 平台的 Doubao 系列模型 API 进行学术论文 Memo 生成。

## API 配置

### Base URL

```
https://ark.cn-beijing.volces.com/api/v3
```

### 认证方式

使用 Bearer Token 认证，需要在请求头中添加：

```
Authorization: Bearer YOUR_API_KEY
```

### API Key 获取

1. 登录 [火山引擎控制台](https://console.volcengine.com/ark)
2. 进入方舟平台
3. 在 API Key 管理页面创建或获取 API Key
4. 将 API Key 设置为环境变量 `ARK_API_KEY` 或保存到 `.env` 文件

## 可用模型

| 模型名称 | Model ID | 特点 |
|---------|----------|------|
| Doubao-Seed-2.0-Lite | `doubao-seed-2-0-lite-260215` | 轻量版，速度快，成本低 |
| Doubao-Seed-2.0-Mini | `doubao-seed-2-0-mini-260215` | 中等规模，平衡性能与成本 |
| Doubao-Seed-2.0-Pro | `doubao-seed-2-0-pro-260215` | 专业版，最强性能 |

## API 调用方式

### 文件上传

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key="YOUR_API_KEY"
)

# 上传文件
with open("paper.pdf", "rb") as f:
    file = client.files.create(
        file=f,
        purpose="user_data"
    )

file_id = file.id
```

### 生成响应 (Responses API)

```python
response = client.responses.create(
    model="doubao-seed-2-0-lite-260215",
    input=[
        {
            "role": "system",
            "content": [
                {"type": "input_text", "text": "系统提示词"}
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "input_file", "file_id": file_id},
                {"type": "input_text", "text": "用户提示"}
            ]
        }
    ],
    stream=True,
    extra_body={
        "thinking": {"type": "enabled"}
    }
)

# 流式处理响应
for event in response:
    if event.type == "response.output_text.delta":
        print(event.delta, end="")
```

### 思考模式

Doubao-Seed 系列支持思考模式，通过 `extra_body` 参数启用：

```python
extra_body={
    "thinking": {"type": "enabled"}
}
```

思考内容通过以下事件类型返回：
- `response.reasoning_summary_text.delta`: 思考内容增量
- `response.reasoning_summary_text.done`: 思考内容完成

## 脚本使用

### 交互模式

直接运行脚本不带参数，将进入交互模式，依次询问各项参数：

```bash
python volcano_engine_llm.py
```

交互模式会显示可用模型列表供选择，并提示输入各项参数（括号内为默认值，直接回车使用默认值）。

### 命令行模式

```bash
# 完整参数
python volcano_engine_llm.py JDE 202603 Memo doubao-seed-2-0-lite-260215 D:\output --wait=60 --retries=3

# 最小参数（使用默认值）
python volcano_engine_llm.py JDE 202603

# 指定 prompt 和模型
python volcano_engine_llm.py JDE 202603 Memo doubao-seed-2-0-pro-260215

# 重新处理所有论文（不跳过已处理的）
python volcano_engine_llm.py JDE 202603 Memo doubao-seed-2-0-lite-260215 --no-skip

# 自定义等待时间和重试次数
python volcano_engine_llm.py JDE 202603 Memo doubao-seed-2-0-lite-260215 --wait=120 --retries=5
```

### 参数说明

| 参数 | 位置 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| journal_abbr | 1 | ✅* | JDE | 期刊缩写 |
| issue | 2 | ✅* | - | 期数 (如 202603) |
| prompt_name | 3 | ❌ | Memo | 任务 prompt 名称 |
| model_id | 4 | ❌ | doubao-seed-2-0-lite | 模型 ID |
| output_path | 5 | ❌ | Output/{prompt_name} | 自定义输出目录 |
| --no-skip | 标志 | ❌ | - | 不跳过已处理的论文（默认跳过） |
| --wait=N | 选项 | ❌ | 60 | 论文处理完成后等待 N 秒（避免速率限制） |
| --retries=N | 选项 | ❌ | 3 | 失败后最大重试次数 |

*交互模式下可不提供，脚本会依次询问

### 速率限制与重试机制

脚本内置了以下机制应对 API 限制：

1. **等待机制**：每篇论文处理完成后等待指定时间（默认 60 秒），避免触发 TPM/RPM 限制
2. **重试机制**：遇到可重试错误（timeout、rate limit、5xx 错误等）自动重试，重试前等待时间递增
3. **智能跳过**：只跳过成功处理的论文，失败论文会被重新处理

### 断点续传

脚本支持断点续传功能：
- **默认行为**：跳过已在输出文件中成功处理的论文
- **跨提供商续传**：同一模型的不同提供商写入同一文件，自动续用已有产出
- **时间戳记录**：每个 memo 前添加时间戳和模型 ID 注释
- **追写模式**：新内容追加到文件末尾，不覆盖已有内容
- **智能识别**：只跳过有实际内容的论文，错误记录会被重新处理

### 输出格式

每个论文的 memo 前会有以下注释：

```html
<!-- Paper: xxx.pdf -->
<!-- Timestamp: 2026-03-22 01:38:25 -->
<!-- Model: doubao-seed-2-0-lite-260215 -->
<!-- Tokens: input=12345, output=2345, total=14690, reasoning=1234 -->
```

### Token 用量记录

脚本会自动记录每篇论文的 token 用量：
- **终端输出**：处理完成后显示 token 用量（input/output/total/reasoning）
- **日志文件**：记录详细的 token 用量信息
- **Memo 文件**：每篇论文开头添加 `<!-- Tokens: ... -->` 注释

### 输出文件

- **Memo 文件**: `{journal}-{issue}_{model_suffix}.md`
- **日志文件**: `Output/Logs/volcano_engine_llm_{timestamp}.log`

### 期刊目录查找

脚本会自动查找期刊目录，支持以下格式：
- `10_JDE/JDE-202603/` (推荐格式)
- `10_{Journal}/{Journal}-{issue}/`

查找逻辑：
1. 首先在项目根目录下查找以 `10_` 开头且包含期刊缩写的目录
2. 如果找不到，尝试直接匹配期刊缩写
3. 都找不到则使用默认路径 `10_{journal_abbr}`

### 思考内容格式

思考内容以 HTML 可折叠框格式保存：

```html
<div style="border: 2px solid #dddddd; border-radius: 10px;">
  <details open style="padding: 5px;">
    <summary>已深度思考</summary>
    思考内容...
  </details>
</div>
```

## 注意事项

1. **API Key 安全**: 不要将 API Key 硬编码在脚本中，使用环境变量或 `.env` 文件
2. **文件大小限制**: 单个 PDF 文件建议不超过 50MB
3. **并发限制**: 建议顺序处理文件，避免并发请求
4. **费用控制**: 不同模型收费标准不同，Pro 模型费用最高
5. **速率限制**: 建议保持默认的 60 秒等待时间，避免触发限制

### 中文路径与特殊字符

PowerShell 7+ 完全支持中文路径。使用建议：

```powershell
# 方式1：用引号包裹（推荐）
python volcano_engine_llm.py JDE 202603 Memo doubao-seed-2-0-lite "E:\your_project_root\output"

# 方式2：使用正斜杠（Windows 也支持）
python volcano_engine_llm.py JDE 202603 Memo doubao-seed-2-0-lite "E:/your_project_root/output"

# 方式3：使用相对路径
python volcano_engine_llm.py JDE 202603 Memo doubao-seed-2-0-lite "..\..\CustomOutput"
```

**说明**：
- PowerShell 中反斜杠 `\` 不是转义符（转义符是反引号 `` ` ``）
- 用引号包裹路径是最安全的方式，既能处理中文，也能避免潜在问题

## 错误处理

常见错误及解决方案：

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| 401 Unauthorized | API Key 无效或格式错误 | 检查 API Key 是否正确 |
| 429 Too Many Requests | 请求频率过高 | 增加 `--wait` 参数值 |
| 500 Internal Server Error | 服务器错误 | 脚本会自动重试 |
| Timeout | 处理时间过长 | 增加 `--retries` 参数值，脚本会自动重试 |
| Connection Error | 网络问题 | 检查网络连接，禁用代理 |
| File processing failed | 文件上传失败 | 检查 PDF 文件是否损坏 |

## 参考链接

- [火山引擎方舟平台](https://www.volcengine.com/product/ark)
- [API 文档](https://www.volcengine.com/docs/82379/1263279)
- [模型介绍](https://www.volcengine.com/docs/82379/1298454)
