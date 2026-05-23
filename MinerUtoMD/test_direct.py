#!/usr/bin/env python3
"""测试 MinerU 直接调用"""
import os
import subprocess

# 设置环境变量
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HOME'] = 'C:/hf_cache'

cmd = [
    r'C:\ProgramData\miniforge3\envs\mineru2\Scripts\mineru.exe',
    '-p', r'C:/Users/Administrator/Downloads/GB13495.3-2026消防安全标志第3部分设置要求.pdf',
    '-o', r'D:\Dmate工作区\MInerUtoMD\.dumate\output\direct_test',
    '-b', 'pipeline',
    '-f', 'true',
    '-t', 'true',
    '-l', 'ch'
]

print(f"执行命令: {' '.join(cmd)}")
result = subprocess.run(cmd, env=os.environ)
print(f"返回码: {result.returncode}")
