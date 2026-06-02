---
name: paddle-pdf-re
description: PaddleOCR-VL-1.6 异步 API PDF 转 Markdown 技能。基于异步 jobs API，支持批量转换，每个 PDF 输出一个带 `_paddle` 后缀的 .md 文件和一个同名子文件夹（存放图片和 JSON），图片以相对路径引用。
author: WZM
---

# PaddleOCR-VL-1.6 异步 PDF→Markdown 技能

## 概述

使用 PaddleOCR-VL-1.6 的**异步 jobs API** 将 PDF 转换为 Markdown。每个 PDF 产出：
- 一个 `{stem}_paddle.md` 文件
- 一个 `{stem}_paddle/` 子文件夹，存放图片和原始 JSON 结果

## 核心流程

```
提交 PDF → 轮询状态 → 下载结果 → 下载图片到子文件夹 → 保存 JSON → 合并为 {stem}_paddle.md
```

## 输出结构

默认输出到 `Output/ocr/paddle/`：

```
Output/ocr/paddle/
├── paper_a_paddle.md           # Markdown，图片以相对路径引用子文件夹
├── paper_a_paddle/
│   ├── jsonl.jsonl             # PaddleOCR 原始 JSONL 结果
│   └── img/
│       ├── img_in_chart_box_001.jpg
│       ├── img_in_chart_box_002.jpg
│       └── ...
├── paper_b_paddle.md
└── paper_b_paddle/
    ├── jsonl.jsonl
    └── img/
        └── ...
```

MD 文件中的图片引用格式：
```markdown
![image](paper_a_paddle/img/img_in_chart_box_001.jpg)
```

## 脚本路径硬性要求

当需要为项目创建或修订 PaddleOCR 异步转换脚本时，脚本必须保存为项目根目录下的相对路径，且只能使用这个文件名：

```
Output\scripts\run_paddle_ocr_async.py
```

不得生成到项目根目录、`Output/temp/`、其他脚本文件名，或任何临时文件名。不得创建同功能脚本如 `run_paddle.py`、`paddle_ocr.py`、`convert_pdf.py`、`test_run_paddle_ocr_async.py` 来执行正式转换。运行脚本时也必须使用与该路径一致的命令：

```bash
python Output\scripts\run_paddle_ocr_async.py ...
```

这一路径和文件名需要保持稳定，以匹配项目中已允许的命令规则。若项目中已经存在该脚本，只能在此文件上修订，不要新增替代脚本。

## API 调用

### Step 1: 提交 Job

```python
JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"

headers = {"Authorization": f"bearer {api_key}"}
data = {
    "model": "PaddleOCR-VL-1.6",
    "optionalPayload": json.dumps({
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useChartRecognition": False,
    })
}
with open(pdf_path, "rb") as f:
    resp = requests.post(JOB_URL, headers=headers, data=data, files={"file": f})
job_id = resp.json()["data"]["jobId"]
```

### Step 2: 轮询状态

```python
while True:
    resp = requests.get(f"{JOB_URL}/{job_id}", headers=headers)
    data = resp.json()["data"]
    if data["state"] == "done":
        jsonl_url = data["resultUrl"]["jsonUrl"]
        break
    elif data["state"] == "failed":
        raise Exception(f"Job failed: {data.get('errorMsg')}")
    time.sleep(5)
```

### Step 3: 下载、保存、合并

```python
resp = requests.get(jsonl_url)
# Save raw JSONL to subfolder
subfolder = output_dir / f"{stem}_paddle"
(subfolder / "img").mkdir(parents=True, exist_ok=True)
with open(subfolder / "jsonl.jsonl", "w", encoding="utf-8") as f:
    f.write(resp.text)

md_parts, all_images = [], {}
for line in resp.text.strip().split('\n'):
    if not line.strip():
        continue
    result = json.loads(line)["result"]
    for page in result.get("layoutParsingResults", []):
        text = page.get("markdown", {}).get("text", "")
        if text:
            md_parts.append(text)
        all_images.update(page.get("markdown", {}).get("images", {}))

# Download images to subfolder/img/
merged_md = "\n\n".join(md_parts)
for rel_path, remote_url in all_images.items():
    local_name = Path(rel_path).name
    local_path = subfolder / "img" / local_name
    if not local_path.exists():
        img_resp = requests.get(remote_url)
        if img_resp.status_code == 200:
            with open(local_path, "wb") as f:
                f.write(img_resp.content)
    # Replace with relative path including subfolder
    merged_md = merged_md.replace(rel_path, f"{stem}_paddle/img/{local_name}")
```

## 使用方法

```bash
# 单文件（默认输出到 Output/ocr/paddle/）
python Output\scripts\run_paddle_ocr_async.py --input paper.pdf

# 批量转换
python Output\scripts\run_paddle_ocr_async.py --input ./pdfs/ --workers 3

# 指定输出目录
python Output\scripts\run_paddle_ocr_async.py --input paper.pdf --output Output/refs/converted

# 断点续传
python Output\scripts\run_paddle_ocr_async.py --input ./pdfs/ --start 10 --limit 20
```

### 环境变量

```bash
export PADDLE_API_KEY=your_token_here
```

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--input`, `-i` | PDF 文件或目录（必填） | — |
| `--output`, `-o` | 输出目录 | `Output/ocr/paddle` |
| `--api-key` | API Key | 环境变量 `PADDLE_API_KEY` |
| `--workers`, `-w` | 并行线程数 | 3 |
| `--start` | 跳过前 N 个文件 | 0 |
| `--limit` | 最多处理 N 个文件（0=全部） | 0 |

## 完整性验证

转换完成后，执行以下检查：

```python
def check_completeness(md_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    issues = []
    lines = content.split('\n')
    if len(lines) < 100:
        issues.append(f"文件过短: {len(lines)} 行")

    if 'references' not in content.lower() and 'bibliography' not in content.lower():
        issues.append("未找到 References/Bibliography 部分")

    # Check relative image paths exist
    import re
    img_refs = re.findall(r'!\[.*?\]\((.*?)\)', content)
    for ref in img_refs:
        if ref.startswith('http'):
            issues.append(f"图片仍为远程 URL: {ref}")

    return issues
```
