# 快速开始指南

## 安装步骤

### 1. 安装 Pandoc（必需）

Pandoc 是文档转换的核心工具。

**Windows:**
1. 访问 https://github.com/jgm/pandoc/releases
2. 下载最新的 `pandoc-x.x.x-windows-x86_64.zip`
3. 解压后将 `pandoc.exe` 所在目录添加到系统 PATH

**或使用 Chocolatey:**
```bash
choco install pandoc
```

**或使用 Scoop:**
```bash
scoop install pandoc
```

### 2. 安装 Python 依赖

```bash
# 进入项目目录
cd D:\Dmate工作区\MInerUtoMD

# 安装依赖
pip install -r requirements.txt
```

### 3. 安装 MinerU（可选，用于PDF工作流）

如果需要处理 PDF 文件：

```bash
pip install magic-pdf[full]
```

**注意:** MinerU 依赖较多，建议使用 conda 环境：
```bash
conda create -n mineru python=3.10
conda activate mineru
pip install magic-pdf[full]
```

## 验证安装

运行测试脚本：
```bash
python test_installation.py
```

或使用命令行工具：
```bash
python main.py check
```

## 基本使用

### PDF 工作流

**单个文件：**
```bash
# PDF 转 Markdown
python main.py pdf document.pdf

# PDF 转 Word
python main.py pdf document.pdf -f docx

# PDF 转多种格式
python main.py pdf document.pdf -f docx -f pdf -f epub
```

**批量处理：**
```bash
python main.py batch-pdf ./pdfs -f docx
```

### Word 工作流

**单个文件：**
```bash
# Word 优化（转MD再转回Word）
python main.py word document.docx

# 只导出 Markdown
python main.py word document.docx --md-only
```

**批量处理：**
```bash
python main.py batch-word ./docs
```

## Python API 使用

```python
# 导入工作流
from workflow import PDFWorkflow, WordWorkflow

# PDF 工作流
pdf_wf = PDFWorkflow()
result = pdf_wf.run(
    'document.pdf',
    './output',
    output_formats=['md', 'docx']
)

if result['success']:
    print("输出文件:", result['outputs'])
    # {'md': './output/document.md', 'docx': './output/document.docx'}

# Word 工作流
word_wf = WordWorkflow()
result = word_wf.run(
    'document.docx',
    './output',
    export_md_only=False  # True 则只导出 MD
)

if result['success']:
    print("输出文件:", result['outputs'])
```

## 配置文件

编辑 `config.yaml` 自定义行为：

```yaml
# MinerU 配置
mineru:
  enable_ocr: true        # 启用OCR（扫描件PDF）
  ocr_lang: "ch"          # OCR语言（ch=中文）

# Pandoc 配置
pandoc:
  pdf_engine: "wkhtmltopdf"  # PDF引擎

# Markdown 优化
markdown_optimizer:
  clean_empty_lines: true    # 清理多余空行
  normalize_headers: true    # 规范化标题

# 输出配置
output:
  overwrite: false           # 不覆盖已存在文件
  keep_intermediate: false   # 不保留中间文件
```

## 常见问题

### 1. Pandoc 未找到

**问题:** `Pandoc 未安装或不可用`

**解决:**
- 确认 Pandoc 已安装
- 确认 `pandoc` 命令在 PATH 中
- Windows: 重启命令行窗口或重启电脑

### 2. MinerU 安装失败

**问题:** MinerU 依赖安装失败

**解决:**
- 使用 conda 环境
- 确保 Python 版本 >= 3.8
- Windows: 安装 Visual C++ Build Tools

### 3. PDF 转换中文乱码

**解决:**
- 在配置中设置 `ocr_lang: "ch"`
- 确保系统安装了中文字体

### 4. Word 转换格式丢失

**说明:** 
- Word 转 Markdown 会丢失部分格式（如字体、颜色）
- 这是 Markdown 格式的限制
- 转回 Word 后可手动调整格式

## 输出格式说明

| 格式 | 说明 | 适用场景 |
|------|------|----------|
| md | Markdown | 文档编辑、版本控制 |
| docx | Word | 办公文档、协作 |
| pdf | PDF | 打印、分享 |
| epub | 电子书 | 电子阅读器 |
| html | 网页 | 在线发布 |

## 项目文件说明

```
MInerUtoMD/
├── main.py                  # 命令行入口
├── workflow.py              # 工作流实现
├── mineru_extractor.py      # PDF提取模块
├── pandoc_converter.py      # 格式转换模块
├── markdown_optimizer.py    # Markdown优化模块
├── config.yaml              # 配置文件
├── requirements.txt         # Python依赖
├── test_installation.py     # 安装测试
├── start.bat                # Windows启动脚本
└── README.md                # 详细文档
```

## 下一步

1. 安装 Pandoc
2. 运行 `python test_installation.py` 验证
3. 尝试转换一个 PDF 或 Word 文件
4. 根据需要调整 `config.yaml`

## 获取帮助

```bash
# 查看所有命令
python main.py --help

# 查看具体命令帮助
python main.py pdf --help
python main.py word --help
```
