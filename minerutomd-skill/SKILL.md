---
name: minerutomd
description: >
  基于 MinerU 和 Pandoc 的智能文档转换工具。支持 PDF 转 Word/Markdown/HTML/EPUB，
  具备 OCR、公式识别、表格识别功能。适用于学术论文、技术文档、标准规范等 PDF 文档的格式转换。
license: MIT
---

# MinerUtoMD

智能文档转换工具，基于 MinerU 3.x 和 Pandoc 实现高质量的 PDF 文档转换。

### When to apply

- 用户需要将 **PDF 转换为 Word (.docx)** 文档
- 用户需要将 **PDF 转换为 Markdown** 格式
- 用户需要将 **PDF 转换为 HTML/EPUB** 格式
- PDF 包含**数学公式**需要识别和保留
- PDF 包含**复杂表格**需要识别和转换
- PDF 是**扫描件**需要 OCR 识别
- 用户提到 `.pdf` 文件并希望转换为其他格式

### When NOT to apply

- 用户需要从零创建 PDF → 使用 `pdf` skill
- 用户需要编辑 PDF 内容 → 使用 `pdf` skill
- 用户需要合并/拆分 PDF → 使用 `pdf` skill
- 用户需要处理 Word 文档 → 使用 `docx` skill

---

## Environment Requirements

**必须预先安装以下环境：**

| 依赖 | 版本 | 安装方式 |
|------|------|----------|
| Miniforge/Conda | latest | https://github.com/conda-forge/miniforge/releases |
| MinerU | 3.1.15+ | `conda create -n mineru2 python=3.10 && pip install mineru[full]` |
| Pandoc | 3.0+ | https://pandoc.org/installing.html |

**环境路径配置：**

```python
# MinerU 环境
MINERU_PYTHON = r"C:\ProgramData\miniforge3\envs\mineru2\python.exe"
MINERU_CLI = r"C:\ProgramData\miniforge3\envs\mineru2\Scripts\mineru.exe"

# Pandoc
PANDOC_PATH = r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\JohnMacFarlane.Pandoc_Microsoft.Winget.Source_8wekyb3d8bbwe\pandoc-3.9.0.2\pandoc.exe"
```

**模型缓存目录：**

```python
# HuggingFace 缓存（需要设置短路径避免 Windows 260 字符限制）
HF_HOME = "C:/hf_cache"

# ModelScope 缓存
MODELSCOPE_CACHE = "C:/Users/Administrator/.cache/modelscope/OpenDataLab/PDF-Extract-Kit-1.0/models"
```

---

## Route Table

| 用户意图 | 命令 | 说明 |
|----------|------|------|
| PDF 转 Word | `python main.py pdf input.pdf -f docx` | 包含图片嵌入 |
| PDF 转 Markdown | `python main.py pdf input.pdf -f md` | 包含图片文件夹 |
| PDF 转 HTML | `python main.py pdf input.pdf -f html` | 独立 HTML 文件 |
| PDF 转 EPUB | `python main.py pdf input.pdf -f epub` | 电子书格式 |
| 多格式输出 | `python main.py pdf input.pdf -f md -f docx` | 同时输出多种格式 |
| 启用公式识别 | `python main.py pdf input.pdf --formula` | 默认启用 |
| 启用表格识别 | `python main.py pdf input.py --table` | 默认禁用 |
| 批量处理 | `python main.py batch-pdf ./pdfs/ -f docx` | 处理整个目录 |

---

## Usage Examples

### 1. 基础 PDF 转 Word

```bash
python main.py pdf document.pdf -f docx -o ./output/
```

### 2. 启用公式和表格识别

```bash
python main.py pdf document.pdf -f docx --formula --table -o ./output/
```

### 3. 同时输出 Markdown 和 Word

```bash
python main.py pdf document.pdf -f md -f docx -o ./output/
```

### 4. 批量处理 PDF 目录

```bash
python main.py batch-pdf ./pdfs/ -f docx -o ./output/
```

### 5. 指定页码范围

```bash
python main.py pdf document.pdf -f docx --start 0 --end 10
```

---

## Output Structure

```
output/
├── document.md          # Markdown 文件
├── document.docx        # Word 文档（图片已嵌入）
├── images/              # 图片文件夹（Markdown 使用）
│   ├── xxx.jpg
│   └── ...
└── .temp_xxx/           # 临时文件（可删除）
```

---

## Key Features

### 公式识别

- 支持 LaTeX 公式识别
- 公式转换为标准 Markdown 格式
- 在 Word 中正确渲染

### 表格识别

- 自动检测表格结构
- HTML 表格转换为 Markdown 表格
- 支持合并单元格（rowspan/colspan）

### 图片处理

- 自动提取 PDF 中的图片
- 图片嵌入到 Word 文档中
- Markdown 文件引用相对路径图片

### OCR 支持

- 中文 OCR 支持
- 扫描件 PDF 自动识别
- 保持原文档排版

---

## Troubleshooting

### 问题：HuggingFace 无法访问

**解决方案：** 设置镜像环境变量

```python
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HOME'] = 'C:/hf_cache'
```

### 问题：Windows 路径长度限制

**解决方案：** 使用短路径缓存目录

```python
os.environ['HF_HOME'] = 'C:/hf_cache'
```

### 问题：模型下载失败

**解决方案：** 从 ModelScope 复制模型到 HF 缓存

```bash
# 运行模型复制脚本
python scripts/copy_models.py
```

### 问题：表格显示为纯文本

**解决方案：** 确保启用了表格识别

```bash
python main.py pdf document.pdf --table
```

---

## API Reference

### Python API

```python
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HOME'] = 'C:/hf_cache'

from workflow import PDFWorkflow

workflow = PDFWorkflow({
    'mineru': {
        'enable_formula': True,
        'enable_table': True,
        'backend': 'pipeline'
    },
    'pandoc': {
        'path': '/path/to/pandoc'
    }
})

result = workflow.run(
    'input.pdf',
    './output/',
    ['md', 'docx'],
    enable_formula=True,
    enable_table=True
)

print(result['outputs'])
```

---

## Performance Notes

| 文档类型 | 页数 | 处理时间 | 内存占用 |
|----------|------|----------|----------|
| 纯文本 PDF | 10页 | ~30秒 | ~2GB |
| 图文混排 | 20页 | ~2分钟 | ~4GB |
| 扫描件 | 10页 | ~3分钟 | ~6GB |
| 复杂表格 | 15页 | ~2分钟 | ~4GB |

**建议：** 处理大型文档时，建议分批处理或增加内存。
