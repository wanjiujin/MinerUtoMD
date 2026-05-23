"""
Markdown 优化模块
"""
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class MarkdownOptimizer:
    """Markdown优化器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化优化器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.clean_empty_lines = self.config.get('clean_empty_lines', True)
        self.normalize_headers = self.config.get('normalize_headers', True)
        self.fix_list_indent = self.config.get('fix_list_indent', True)
        self.optimize_tables = self.config.get('optimize_tables', True)
        self.remove_html_tags = self.config.get('remove_html_tags', False)
    
    def optimize(
        self,
        md_path: str,
        output_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        优化Markdown文件
        
        Args:
            md_path: 输入Markdown文件路径
            output_path: 输出路径（默认覆盖原文件）
            **kwargs: 额外参数
            
        Returns:
            优化结果字典
        """
        md_path = Path(md_path)
        
        if not md_path.exists():
            return {
                'success': False,
                'error': f'文件不存在: {md_path}'
            }
        
        try:
            # 读取文件
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 应用优化
            if self.clean_empty_lines:
                content = self._clean_empty_lines(content)
            
            if self.normalize_headers:
                content = self._normalize_headers(content)
            
            if self.fix_list_indent:
                content = self._fix_list_indent(content)
            
            if self.optimize_tables:
                content = self._optimize_tables(content)
            
            if self.remove_html_tags:
                content = self._remove_html_tags(content)
            
            # 确定输出路径
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = md_path
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Markdown优化完成: {output_path}")
            
            return {
                'success': True,
                'input_path': str(md_path),
                'output_path': str(output_path),
                'original_length': len(original_content),
                'optimized_length': len(content)
            }
            
        except Exception as e:
            logger.error(f"优化失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _clean_empty_lines(self, content: str) -> str:
        """清理多余空行"""
        # 移除行尾空格
        lines = [line.rstrip() for line in content.split('\n')]
        
        # 合并连续多个空行为最多2个
        result = []
        empty_count = 0
        
        for line in lines:
            if line == '':
                empty_count += 1
                if empty_count <= 2:
                    result.append(line)
            else:
                empty_count = 0
                result.append(line)
        
        # 移除开头和结尾的空行
        while result and result[0] == '':
            result.pop(0)
        while result and result[-1] == '':
            result.pop()
        
        return '\n'.join(result) + '\n'
    
    def _normalize_headers(self, content: str) -> str:
        """规范化标题层级"""
        lines = content.split('\n')
        result = []
        
        # 检测最小标题层级
        min_level = 6
        for line in lines:
            match = re.match(r'^(#{1,6})\s', line)
            if match:
                level = len(match.group(1))
                min_level = min(min_level, level)
        
        # 如果最小层级大于1，提升所有标题
        if min_level > 1:
            shift = min_level - 1
            for line in lines:
                match = re.match(r'^(#{1,6})\s(.*)$', line)
                if match:
                    level = len(match.group(1))
                    title = match.group(2)
                    new_level = max(1, level - shift)
                    result.append('#' * new_level + ' ' + title)
                else:
                    result.append(line)
        else:
            result = lines
        
        return '\n'.join(result)
    
    def _fix_list_indent(self, content: str) -> str:
        """修复列表缩进"""
        lines = content.split('\n')
        result = []
        
        for line in lines:
            # 无序列表
            match = re.match(r'^(\s*)[-*+]\s', line)
            if match:
                indent = match.group(1)
                # 确保缩进是4的倍数
                indent_level = len(indent) // 4
                new_indent = '    ' * indent_level
                line = new_indent + line.lstrip()
            
            # 有序列表
            match = re.match(r'^(\s*)\d+\.\s', line)
            if match:
                indent = match.group(1)
                indent_level = len(indent) // 4
                new_indent = '    ' * indent_level
                line = new_indent + line.lstrip()
            
            result.append(line)
        
        return '\n'.join(result)
    
    def _optimize_tables(self, content: str) -> str:
        """优化表格格式 - 将 HTML 表格转换为 Markdown 表格"""
        # 先转换 HTML 表格为 Markdown 表格
        content = self._convert_html_tables(content)
        
        # 确保表格分隔行格式正确
        lines = content.split('\n')
        result = []
        
        for i, line in enumerate(lines):
            # 检测表格分隔行
            if re.match(r'^\s*\|?[-\s:|]+\|?\s*$', line):
                # 规范化分隔行
                parts = line.split('|')
                parts = [p.strip() for p in parts if p.strip()]
                
                # 确保每个单元格至少3个字符
                normalized = []
                for part in parts:
                    if ':' in part:
                        # 对齐标记
                        if part.startswith(':') and part.endswith(':'):
                            normalized.append(':---:')
                        elif part.startswith(':'):
                            normalized.append(':---')
                        else:
                            normalized.append('---:')
                    else:
                        normalized.append('---')
                
                line = '| ' + ' | '.join(normalized) + ' |'
            
            result.append(line)
        
        return '\n'.join(result)
    
    def _convert_html_tables(self, content: str) -> str:
        """将 HTML 表格转换为 Markdown 表格"""
        # 匹配 <table>...</table>
        def replace_table(match):
            table_html = match.group(0)
            md_table = self._html_table_to_markdown(table_html)
            # 确保表格前后有空行
            if md_table:
                return '\n\n' + md_table + '\n\n'
            return ''
        
        # 使用非贪婪匹配
        content = re.sub(r'<table>.*?</table>', replace_table, content, flags=re.DOTALL | re.IGNORECASE)
        return content
    
    def _html_table_to_markdown(self, html: str) -> str:
        """将单个 HTML 表格转换为 Markdown 表格"""
        rows = []
        
        # 提取所有行
        tr_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
        td_pattern = re.compile(r'<t[dh][^>]*>(.*?)</t[dh]>', re.DOTALL | re.IGNORECASE)
        
        for tr_match in tr_pattern.finditer(html):
            row = []
            for td_match in td_pattern.finditer(tr_match.group(1)):
                cell = td_match.group(1).strip()
                # 清理单元格内的 HTML 标签
                cell = re.sub(r'<[^>]+>', '', cell)
                # 清理多余空白
                cell = re.sub(r'\s+', ' ', cell)
                # 转义管道符
                cell = cell.replace('|', '\\|')
                row.append(cell)
            
            if row:
                rows.append(row)
        
        if not rows:
            return ''
        
        # 确定列数
        max_cols = max(len(row) for row in rows)
        
        # 补齐列数
        for row in rows:
            while len(row) < max_cols:
                row.append('')
        
        # 构建 Markdown 表格
        result = []
        
        # 表头行
        if rows:
            result.append('| ' + ' | '.join(rows[0]) + ' |')
            # 分隔行
            result.append('| ' + ' | '.join(['---'] * max_cols) + ' |')
            # 数据行
            for row in rows[1:]:
                result.append('| ' + ' | '.join(row) + ' |')
        
        return '\n'.join(result)
    
    def _remove_html_tags(self, content: str) -> str:
        """移除HTML标签"""
        # 移除HTML标签，但保留内容
        content = re.sub(r'<[^>]+>', '', content)
        return content
    
    def extract_text_only(self, content: str) -> str:
        """
        提取纯文本（移除所有Markdown格式）
        
        Args:
            content: Markdown内容
            
        Returns:
            纯文本内容
        """
        # 移除标题标记
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        
        # 移除粗体和斜体
        content = re.sub(r'\*\*?([^\*]+)\*\*?', r'\1', content)
        content = re.sub(r'__?([^_]+)__?', r'\1', content)
        
        # 移除链接，保留文本
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        
        # 移除图片
        content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', content)
        
        # 移除代码块标记
        content = re.sub(r'```[\w]*\n?', '', content)
        content = re.sub(r'`([^`]+)`', r'\1', content)
        
        # 移除列表标记
        content = re.sub(r'^\s*[-*+]\s+', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*\d+\.\s+', '', content, flags=re.MULTILINE)
        
        # 移除引用标记
        content = re.sub(r'^\s*>\s+', '', content, flags=re.MULTILINE)
        
        # 移除水平线
        content = re.sub(r'^[-*_]{3,}\s*$', '', content, flags=re.MULTILINE)
        
        return content
