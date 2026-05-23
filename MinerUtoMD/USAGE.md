# MinerUtoMD 使用指南

## 快速开始

### 方式一：使用 GUI 版本（推荐）

双击运行 `dist\MinerUtoMD.exe`

**功能特点：**
- 现代化深色主题界面
- 支持单个文件和批量处理
- 实时进度显示和日志
- 一键打开输出目录

### 方式二：命令行版本

```bash
# 激活环境
C:\ProgramData\miniforge3\Scripts\activate.bat mineru

# PDF 工作流
python main.py pdf document.pdf -f docx

# Word 工作流
python main.py word document.docx

# 批量处理
python main.py batch-pdf ./pdfs -f docx
```

## 工作流说明

### PDF 工作流
```
PDF → MinerU提取 → Markdown优化 → 多格式输出
```

**支持的输出格式：**
- Markdown (.md)
- Word (.docx)
- PDF (.pdf)
- EPUB (.epub)
- HTML (.html)

**适用场景：**
- PDF 文档转换
- 扫描件 OCR 识别
- 学术论文提取
- 电子书制作

### Word 工作流
```
Word → Markdown → 格式优化 → 规整Word
```

**特点：**
- 自动清理格式
- 统一标题层级
- 优化表格和列表
- 可选择仅导出 Markdown

## GUI 界面说明

### 主界面布局

1. **工作流选择**
   - PDF 工作流：处理 PDF 文件
   - Word 工作流：处理 Word 文档

2. **文件选择**
   - 单个文件模式
   - 批量处理模式

3. **输出设置**
   - 选择输出格式（可多选）
   - 设置输出目录
   - Word 工作流专属：仅导出 Markdown 选项

4. **进度显示**
   - 实时进度条
   - 详细日志输出

5. **操作按钮**
   - 开始转换
   - 打开输出目录
   - 检查环境

## 环境要求

### 必需组件
- **Pandoc 3.9.0.2+**：文档转换核心
- **Python 3.11+**：运行环境（已包含在 conda 环境中）

### PDF 工作流额外要求
- **MinerU 1.3.12+**：PDF 提取
- **PyTorch 2.5.1+ CUDA**：GPU 加速

### 系统要求
- Windows 7+
- NVIDIA GPU（可选，用于加速）

## 常见问题

### 1. GUI 无法启动
- 检查是否安装了 Visual C++ Redistributable
- 尝试以管理员身份运行

### 2. PDF 转换失败
- 确认已安装 MinerU
- 检查 GPU 驱动是否最新
- 查看日志了解详细错误

### 3. 输出格式乱码
- 确保系统安装了中文字体
- 在配置文件中设置 `ocr_lang: "ch"`

### 4. 转换速度慢
- 确认 GPU 加速已启用（检查环境）
- 尝试降低 OCR 精度

## 配置文件

编辑 `config.yaml` 自定义行为：

```yaml
# MinerU 配置
mineru:
  enable_ocr: true        # 启用 OCR
  ocr_lang: "ch"          # OCR 语言

# Pandoc 配置
pandoc:
  pdf_engine: "wkhtmltopdf"

# Markdown 优化
markdown_optimizer:
  clean_empty_lines: true
  normalize_headers: true
```

## 开发者信息

### 项目结构
```
MInerUtoMD/
├── gui.py              # GUI 界面
├── main.py             # 命令行入口
├── workflow.py         # 工作流实现
├── mineru_extractor.py # PDF 提取
├── pandoc_converter.py # 格式转换
├── markdown_optimizer.py # Markdown 优化
├── config.yaml         # 配置文件
└── dist/
    └── MinerUtoMD.exe  # 打包后的可执行文件
```

### 重新打包

```bash
# 安装 PyInstaller
pip install pyinstaller

# 执行打包
build_exe.bat
```

## 更新日志

### v1.0.0 (2026-05-23)
- 初始版本
- PDF 和 Word 双工作流
- 现代化 GUI 界面
- GPU 加速支持
- 批量处理功能
