#!/usr/bin/env python3
"""测试表格转换"""
import sys
sys.path.insert(0, r'D:\Dmate工作区\MInerUtoMD')

from markdown_optimizer import MarkdownOptimizer

# 测试 HTML 表格转换
html_table = """<table><tr><td rowspan=1 colspan=1>最大观察距离m</td><td rowspan=1 colspan=1>标志的型号a</td></tr><tr><td rowspan=1 colspan=1>0 < Dmax <= 2.5</td><td rowspan=1 colspan=1>1</td></tr><tr><td rowspan=1 colspan=1>2.5 < Dmax <= 4.0</td><td rowspan=1 colspan=1>2</td></tr></table>"""

optimizer = MarkdownOptimizer()
result = optimizer._html_table_to_markdown(html_table)
print("转换结果:")
print(result)
