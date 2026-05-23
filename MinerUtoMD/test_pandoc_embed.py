#!/usr/bin/env python3
"""测试 Pandoc 图片嵌入"""
import subprocess
from pathlib import Path

md_path = r"D:\Dmate工作区\MInerUtoMD\.dumate\output\direct_test\GB13495.3-2026消防安全标志第3部分设置要求\auto\GB13495.3-2026消防安全标志第3部分设置要求.md"
images_dir = r"D:\Dmate工作区\MInerUtoMD\.dumate\output\direct_test\GB13495.3-2026消防安全标志第3部分设置要求\auto\images"
output_path = r"D:\Dmate工作区\MInerUtoMD\.dumate\output\test_embed.docx"
pandoc_path = r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\JohnMacFarlane.Pandoc_Microsoft.Winget.Source_8wekyb3d8bbwe\pandoc-3.9.0.2\pandoc.exe"

cmd = [
    pandoc_path,
    md_path,
    '-f', 'markdown',
    '-t', 'docx',
    '-o', output_path,
    '--embed-resources',
    '--resource-path', images_dir,
    '--resource-path', str(Path(md_path).parent)
]

print(f"执行命令: {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True)
print(f"返回码: {result.returncode}")
if result.stderr:
    print(f"错误: {result.stderr}")
if result.returncode == 0:
    print(f"成功: {output_path}")
