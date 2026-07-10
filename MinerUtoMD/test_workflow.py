#!/usr/bin/env python3
"""测试完整工作流"""
import os
import sys
from pathlib import Path

# 设置环境变量
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HOME'] = 'C:/hf_cache'

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from doc_workflow import PDFWorkflow

# 创建工作流
workflow = PDFWorkflow({
    'mineru': {
        'enable_formula': True,
        'enable_table': False,
        'backend': 'pipeline',
        'ocr_lang': 'ch'
    },
    'pandoc': {
        'path': r'C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\JohnMacFarlane.Pandoc_Microsoft.Winget.Source_8wekyb3d8bbwe\pandoc-3.9.0.2\pandoc.exe'
    }
})

# 测试工作流
result = workflow.run(
    r'D:\Dmate工作区\MInerUtoMD\.dumate\inbox\国企钢筋制作场标准化图册.pdf',
    r'D:\Dmate工作区\MInerUtoMD\.dumate\output\workflow_test',
    output_formats=['md', 'docx'],
    enable_formula=True,
    enable_table=False,
    start_page=0,
    end_page=2
)

print(f"\n工作流结果: {result}")
