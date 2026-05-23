#!/usr/bin/env python3
"""测试 HTML 表格转换"""
import subprocess

# 测试 Markdown 包含 HTML 表格
test_md = """
# 测试表格

这是一个表格：

<table>
<tr><th>列1</th><th>列2</th></tr>
<tr><td>数据1</td><td>数据2</td></tr>
<tr><td>数据3</td><td>数据4</td></tr>
</table>
"""

pandoc_path = r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\JohnMacFarlane.Pandoc_Microsoft.Winget.Source_8wekyb3d8bbwe\pandoc-3.9.0.2\pandoc.exe"

# 写入测试文件
with open(r"D:\Dmate工作区\MInerUtoMD\test_table.md", "w", encoding="utf-8") as f:
    f.write(test_md)

cmd = [
    pandoc_path,
    r"D:\Dmate工作区\MInerUtoMD\test_table.md",
    "-f", "markdown",
    "-t", "docx",
    "-o", r"D:\Dmate工作区\MInerUtoMD\test_table.docx"
]

print(f"执行命令: {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True)
print(f"返回码: {result.returncode}")
if result.stderr:
    print(f"错误: {result.stderr}")
else:
    print("成功！")
