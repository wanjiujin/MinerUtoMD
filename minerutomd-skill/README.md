# MinerUtoMD 安装指南

## 系统要求

- Windows 10/11 64位
- 至少 16GB 内存（推荐 32GB）
- 至少 20GB 可用磁盘空间（模型缓存）
- NVIDIA GPU（可选，用于加速）

## 安装步骤

### 1. 安装 Miniforge

下载并安装 Miniforge：
https://github.com/conda-forge/miniforge/releases

### 2. 创建 MinerU 环境

```bash
# 创建 Python 3.10 环境
conda create -n mineru2 python=3.10 -y
conda activate mineru2

# 安装 MinerU
pip install mineru[full]
```

### 3. 安装 Pandoc

下载并安装 Pandoc：
https://pandoc.org/installing.html

或使用 winget：
```bash
winget install --id JohnMacFarlane.Pandoc
```

### 4. 配置环境变量

创建或编辑 `C:\Users\<用户名>\magic-pdf.json`：

```json
{
    "device-mode": "cuda",
    "models-dir": "C:/Users/Administrator/.cache/modelscope/OpenDataLab/PDF-Extract-Kit-1.0/models",
    "layout-config": {"model": "doclayout_yolo"},
    "formula-config": {"enable": true},
    "table-config": {"enable": true},
    "config_version": "1.0.0"
}
```

### 5. 下载模型

首次运行时会自动下载模型（约 10GB），或手动复制：

```bash
# 设置 HuggingFace 镜像
set HF_ENDPOINT=https://hf-mirror.com
set HF_HOME=C:/hf_cache

# 运行一次 MinerU 初始化
mineru -p test.pdf -o ./output
```

### 6. 验证安装

```bash
# 检查 MinerU
mineru --version

# 检查 Pandoc
pandoc --version

# 测试转换
python main.py pdf test.pdf -f docx
```

## 目录结构

```
minerutomd/
├── SKILL.md              # Skill 说明文档
├── README.md             # 安装指南
└── scripts/
    ├── main.py           # 命令行入口
    ├── workflow.py       # 工作流实现
    ├── mineru_extractor.py   # PDF 提取模块
    ├── pandoc_converter.py   # 格式转换模块
    ├── markdown_optimizer.py # Markdown 优化模块
    ├── copy_models.py    # 模型复制脚本
    └── config.yaml       # 配置文件
```

## 常见问题

### Q: HuggingFace 无法访问？

A: 设置镜像环境变量：
```bash
set HF_ENDPOINT=https://hf-mirror.com
set HF_HOME=C:/hf_cache
```

### Q: Windows 路径长度限制？

A: 使用短路径缓存目录：
```bash
set HF_HOME=C:/hf_cache
```

### Q: 模型下载失败？

A: 运行模型复制脚本：
```bash
python scripts/copy_models.py
```

### Q: 内存不足？

A: 减少批处理页数或增加虚拟内存。

## 更新日志

- v1.0.0 (2026-05-23)
  - 初始版本
  - 支持 PDF 转 Word/Markdown/HTML/EPUB
  - 支持公式识别和表格识别
  - 支持图片嵌入到 Word
