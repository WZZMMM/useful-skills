### Python 脚本示例（兼容 OpenAI SDK）

```python
import os
import time
from openai import OpenAI

# 配置参数
API_KEY = os.getenv("ARK_API_KEY")  # 从环境变量获取 API Key
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL_ID = "doubao-seed-2-0-pro"  # 模型 ID，以实际控制台为准
PDF_PATH = "/path/to/your/document.pdf"  # 替换为本地 PDF 路径
SYSTEM_PROMPT = "你是一个专业的文档分析助手，请仔细阅读上传的 PDF 并回答问题。"
USER_PROMPT = "请总结这份 PDF 的核心内容。"

# 初始化客户端
client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY
)

# ------------------------------
# 步骤 1：上传 PDF 文件
# ------------------------------
print("正在上传 PDF 文件...")
file = client.files.create(
    file=open(PDF_PATH, "rb"),
    purpose="user_data"
)
file_id = file.id
print(f"文件上传成功，File ID: {file_id}")

# ------------------------------
# 步骤 2：等待文件处理完成
# ------------------------------
print("等待文件预处理完成...")
while file.status == "processing":
    time.sleep(2)
    file = client.files.retrieve(file_id)
print(f"文件处理完成，状态: {file.status}")

# ------------------------------
# 步骤 3：调用模型（开启最大思考强度）
# ------------------------------
print("正在调用模型...")
# 注意：此处以 Responses API 为例，若需使用 Chat API，需确认 PDF 传入方式
# Responses API 支持通过 File ID 引用 PDF，且可复用 Chat API 的思考参数
response = client.responses.create(
    model=MODEL_ID,
    input=[
        # System Prompt
        {
            "role": "system",
            "content": [
                {"type": "input_text", "text": SYSTEM_PROMPT}
            ]
        },
        # User Prompt + PDF
        {
            "role": "user",
            "content": [
                {"type": "input_file", "file_id": file_id},  # 引用上传的 PDF
                {"type": "input_text", "text": USER_PROMPT}
            ]
        }
    ],
    # 开启最大思考强度
    thinking={"type": "enabled"},
    reasoning_effort="high",
    stream=True  # 流式输出，可选
)

# 流式输出结果
print("\n模型输出：")
for event in response:
    if event.type == "response.output_text.delta":
        print(event.delta, end="")
    elif event.type == "response.completed":
        print(f"\n\nToken 用量: {event.response.usage}")
```

### 注意事项

1. **模型 ID 确认**：请登录火山引擎方舟控制台，确认 `doubao-seed-2.0-pro` 的准确 Model ID（示例中为占位符）。
2. **API 选择**：若需严格使用 Chat API（文档2），需确认其是否支持 PDF File ID 传入；当前示例基于 Responses API（文档3）实现，更适配大文件/多模态场景。
3. **依赖安装**：运行前需安装 SDK：`pip install openai`。
