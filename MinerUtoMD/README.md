# MinerUtoMD - 文档转换工作流工具

基于 MinerU 和 Pandoc 的智能文档转换工具，支持 PDF 和 Word 文档的高质量转换。

## 功能特性

### 工作流一：PDF 专用
```
PDF → MinerU提取 → Markdown → Pandoc转换 → Word/PDF/EPUB/HTML
```

- 使用 MinerU 提取 PDF 内容为结构化 Markdown
- 自动优化 Markdown 格式
- 支持转换为多种输出格式
- 保留图片和表格

### 工作流二：Word 专用
```
docx → Pandoc转MD → 优化排版 → Pandoc转回规整docx
```

- 将 Word 文档转换为 Markdown
- 优化排版格式
- 可选择只导出 Markdown 或转回 Word
- 支持批量处理

## 安装

### 1. 安装 Pandoc

从 [Pandoc官网](https://pandoc.org/installing.html) 下载并安装。

### 2. 安装 Python 依赖

```bash
# 基础安装
pip install -r requirements.txt

# 或使用 pip 安装
pip install -e .
```

### 3. 安装 MinerU（可选，用于PDF工作流）

```bash
pip install magic-pdf[full]
```

## 使用方法

### 命令行工具

#### 检查依赖

```bash
minerutomd check
```

#### PDF 工作流

```bash
# 基础用法：PDF转Markdown
minerutomd pdf document.pdf

# 指定输出格式
minerutomd pdf document.pdf -f docx -f pdf -f epub

# 指定输出目录
minerutomd pdf document.pdf -o ./output -f docx

# 保留中间文件
minerutomd pdf document.pdf --keep-temp
```

#### Word 工作流

```bash
# 基础用法：Word优化
minerutomd word document.docx

# 只导出Markdown
minerutomd word document.docx --md-only

# 指定输出目录
minerutomd word document.docx -o ./output
```

#### 批量处理

```bash
# 批量处理PDF
minerutomd batch-pdf ./pdfs -f docx -f pdf

# 批量处理Word
minerutomd batch-word ./docs --md-only
```

#### 查看支持的格式

```bash
minerutomd formats
```

### Python API

```python
from workflow import PDFWorkflow, WordWorkflow

# PDF工作流
pdf_workflow = PDFWorkflow()
result = pdf_workflow.run(
    'document.pdf',
    './output',
    output_formats=['md', 'docx', 'pdf']
)

if result['success']:
    print("输出文件:", result['outputs'])

# Word工作流
word_workflow = WordWorkflow()
result = word_workflow.run(
    'document.docx',
    './output',
    export_md_only=False  # True则只导出Markdown
)

if result['success']:
    print("输出文件:", result['outputs'])
```

## 配置文件

编辑 `config.yaml` 自定义行为：

```yaml
# MinerU 配置
mineru:
  output_format: "markdown"
  keep_images: true
  enable_ocr: true
  ocr_lang: "ch"

# Pandoc 配置
pandoc:
  pdf_engine: "wkhtmltopdf"
  extra_args:
    - "--toc"
    - "--toc-depth=3"

# Markdown 优化配置
markdown_optimizer:
  clean_empty_lines: true
  normalize_headers: true
  fix_list_indent: true
  optimize_tables: true

# 输出配置
output:
  directory: "./output"
  overwrite: false
  keep_intermediate: false
```

## 支持的输出格式

| 格式 | 说明 |
|------|------|
| md | Markdown文档 |
| docx | Word文档 |
| pdf | PDF文档 |
| epub | EPUB电子书 |
| html | HTML网页 |
| odt | OpenDocument文本 |
| rtf | 富文本格式 |

## 项目结构

```
MInerUtoMD/
├── __init__.py              # 包初始化
├── main.py                  # 命令行入口
├── workflow.py              # 工作流实现
├── mineru_extractor.py      # MinerU提取模块
├── pandoc_converter.py      # Pandoc转换模块
├── markdown_optimizer.py    # Markdown优化模块
├── config.yaml              # 默认配置
├── requirements.txt         # 依赖列表
├── setup.py                 # 安装配置
└── README.md                # 说明文档
```

## 常见问题

### 1. Pandoc 未找到

确保 Pandoc 已安装并添加到系统 PATH：
```bash
# Windows: 添加到环境变量
# Linux/Mac: 
export PATH=$PATH:/usr/local/bin
```

### 2. MinerU 安装失败

MinerU 依赖较多，建议：
```bash
# 使用conda环境
conda create -n mineru python=3.10
conda activate mineru
pip install magic-pdf[full]
```

### 3. PDF转换中文乱码

确保系统安装了中文字体，或在配置中设置：
```yaml
mineru:
  ocr_lang: "ch"
```

## 依赖说明

- **MinerU**: PDF内容提取，支持扫描件OCR
- **Pandoc**: 通用文档转换工具
- **pypandoc**: Pandoc的Python封装
- **python-docx**: Word文档处理
- **Rich**: 终端美化输出

## 许可证

MIT License

## 更新日志

### v1.0.0 (2026-05-23)
- 初始版本
- 实现PDF工作流
- 实现Word工作流
- 支持批量处理
- 命令行工具
