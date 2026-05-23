#!/usr/bin/env python3
"""测试更新后的 MinerU 提取器"""
import os
import sys

# 设置环境变量
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HOME'] = 'C:/hf_cache'

# 添加项目路径
sys.path.insert(0, r'D:\Dmate工作区\MInerUtoMD')

from mineru_extractor import MinerUExtractor

# 创建提取器
extractor = MinerUExtractor({
    'enable_formula': True,
    'enable_table': False,
    'backend': 'pipeline',
    'ocr_lang': 'ch'
})

print(f"MinerU 版本: {extractor.version}")
print(f"CLI 路径: {extractor.cli_path}")
print(f"检查安装: {extractor.check_installation()}")

# 测试提取
result = extractor.extract(
    r'D:\Dmate工作区\MInerUtoMD\.dumate\inbox\国企钢筋制作场标准化图册.pdf',
    r'D:\Dmate工作区\MInerUtoMD\.dumate\output\test_v3',
    start_page=0,
    end_page=2
)

print(f"\n提取结果: {result}")
