#!/usr/bin/env python3
"""Test MinerU with formula recognition using HF mirror"""
import os
import subprocess
import sys

# Set HuggingFace mirror and short cache path
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HOME'] = 'C:/hf_cache'  # Short path to avoid Windows path length limit

# Run mineru command
cmd = [
    r'C:\ProgramData\miniforge3\envs\mineru2\Scripts\mineru.exe',
    '-p', r'D:\Dmate工作区\MInerUtoMD\.dumate\inbox\国企钢筋制作场标准化图册.pdf',
    '-o', r'D:\Dmate工作区\MInerUtoMD\.dumate\output\test_formula',
    '-b', 'pipeline',
    '-f', 'true',
    '-t', 'false',
    '--start', '0',
    '--end', '2'
]

print(f"HF_ENDPOINT: {os.environ.get('HF_ENDPOINT')}")
print(f"Running: {' '.join(cmd)}")

result = subprocess.run(cmd, env=os.environ)
sys.exit(result.returncode)
