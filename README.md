# MinerUtoMD

基于 MinerU 和 Pandoc 的智能文档转换工具。

## 功能特性

- **PDF 转 Word/Markdown/HTML/EPUB** - 多格式输出
- **公式识别** - 支持 LaTeX 公式识别和转换
- **表格识别** - 自动检测和转换表格结构
- **图片嵌入** - 图片自动嵌入到 Word 文档
- **OCR 支持** - 中文 OCR，支持扫描件 PDF
- **批量处理** - 支持批量转换整个目录

## 项目结构

```
MinerUtoMD/
├── main.py                   # 命令行入口
├── gui.py                    # GUI 界面
├── workflow.py               # 工作流实现
├── mineru_extractor.py       # PDF 提取模块
├── pandoc_converter.py       # 格式转换模块
├── markdown_optimizer.py     # Markdown 优化模块
├── config.yaml               # 配置文件
├── dist/
│   └── MinerUtoMD.exe        # 打包后的可执行文件
└── 开发与打包指南.md          # 开发文档

minerutomd-skill/
├── SKILL.md                  # Skill 主文档
├── README.md                 # 安装指南
└── scripts/                  # 核心脚本
    ├── main.py
    ├── workflow.py
    ├── mineru_extractor.py
    ├── pandoc_converter.py
    ├── markdown_optimizer.py
    ├── copy_models.py
    └── config.yaml
```

## 快速开始

### 环境要求

- Windows 10/11 64位
- Python 3.10+
- MinerU 3.1.15+
- Pandoc 3.0+

### 安装

1. 安装 MinerU 环境：
```bash
conda create -n mineru2 python=3.10
conda activate mineru2
pip install mineru[full]
```

2. 安装 Pandoc：
```bash
winget install --id JohnMacFarlane.Pandoc
```

### 使用方法

#### 命令行

```bash
# PDF 转 Word
python main.py pdf document.pdf -f docx

# PDF 转 Markdown
python main.py pdf document.pdf -f md

# 启用公式和表格识别
python main.py pdf document.pdf --formula --table

# 批量处理
python main.py batch-pdf ./pdfs/ -f docx
```

#### GUI

双击运行 `MinerUtoMD/dist/MinerUtoMD.exe`

## Skill 使用

将 `minerutomd-skill` 文件夹复制到 DuMate skill 目录：

```
C:\Users\<用户名>\AppData\Roaming\qianfan-desktop-app\qianfan_desk_xdg\<workspace_id>\data\skills\
```

重启 DuMate 后即可使用。

## 技术栈

- **MinerU 3.1.15** - PDF 提取和 OCR
- **Pandoc 3.9.0.2** - 文档格式转换
- **PyTorch 2.12.0** - 深度学习框架
- **tkinter** - GUI 界面

## 许可证

MIT License

## 相关链接

- [MinerU 官方仓库](https://github.com/opendatalab/MinerU)
- [Pandoc 官网](https://pandoc.org/)
