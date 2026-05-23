"""
Pandoc 文档转换模块
"""
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class PandocConverter:
    """Pandoc文档转换器"""
    
    # 支持的输出格式
    SUPPORTED_FORMATS = {
        'docx': 'Word文档 (.docx)',
        'pdf': 'PDF文档 (.pdf)',
        'epub': 'EPUB电子书 (.epub)',
        'html': 'HTML网页 (.html)',
        'md': 'Markdown (.md)',
        'odt': 'OpenDocument文本 (.odt)',
        'rtf': '富文本格式 (.rtf)',
        'tex': 'LaTeX (.tex)',
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化转换器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.pdf_engine = self.config.get('pdf_engine', 'wkhtmltopdf')
        self.word_template = self.config.get('word_template')
        self.extra_args = self.config.get('extra_args', [])
        
        # Pandoc 路径
        self.pandoc_path = self.config.get('pandoc_path', 'pandoc')
        if self.pandoc_path == 'pandoc':
            # 尝试查找 pandoc
            self.pandoc_path = shutil.which('pandoc') or 'pandoc'
    
    def check_installation(self) -> bool:
        """检查Pandoc是否正确安装"""
        try:
            result = subprocess.run(
                [self.pandoc_path, '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info(f"Pandoc版本: {result.stdout.split()[1]}")
                return True
            return False
        except FileNotFoundError:
            logger.error("Pandoc未安装，请从 https://pandoc.org/installing.html 下载安装")
            return False
    
    def convert(
        self,
        input_path: str,
        output_path: str,
        input_format: Optional[str] = None,
        output_format: Optional[str] = None,
        cwd: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        转换文档格式
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            input_format: 输入格式（自动检测）
            output_format: 输出格式（根据输出文件扩展名自动检测）
            cwd: 工作目录（用于解析相对路径资源）
            **kwargs: 额外参数
            
        Returns:
            转换结果字典
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            return {
                'success': False,
                'error': f'输入文件不存在: {input_path}'
            }
        
        # 自动检测格式
        if not input_format:
            input_format = self._detect_format(input_path)
        
        if not output_format:
            output_format = self._detect_format(output_path)
        
        if not output_format:
            return {
                'success': False,
                'error': f'无法识别输出格式: {output_path}'
            }
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 默认工作目录为输入文件所在目录
        if not cwd:
            cwd = str(input_path.parent)
        
        try:
            # 构建命令
            cmd = [
                self.pandoc_path,
                str(input_path),
                '-f', input_format,
                '-t', output_format,
                '-o', str(output_path),
            ]
            
            # PDF引擎
            if output_format == 'pdf':
                cmd.extend(['--pdf-engine', self.pdf_engine])
            
            # Word模板
            if output_format == 'docx' and self.word_template:
                if Path(self.word_template).exists():
                    cmd.extend(['--reference-doc', self.word_template])
            
            # 额外参数
            cmd.extend(self.extra_args)
            
            # 自定义参数
            if 'extra_args' in kwargs:
                cmd.extend(kwargs['extra_args'])
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            logger.info(f"工作目录: {cwd}")
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                cwd=cwd
            )
            
            if result.returncode != 0:
                logger.error(f"Pandoc转换失败: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr
                }
            
            logger.info(f"转换成功: {output_path}")
            
            return {
                'success': True,
                'input_path': str(input_path),
                'output_path': str(output_path),
                'input_format': input_format,
                'output_format': output_format
            }
            
        except Exception as e:
            logger.error(f"转换异常: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def markdown_to_word(
        self,
        md_path: str,
        output_path: str,
        template: Optional[str] = None,
        images_dir: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Markdown转Word
        
        Args:
            md_path: Markdown 文件路径
            output_path: 输出 Word 文件路径
            template: Word 模板路径
            images_dir: 图片目录路径（用于嵌入图片）
            **kwargs: 额外参数
        """
        md_path = Path(md_path)
        output_path = Path(output_path)
        
        extra_args = kwargs.get('extra_args', [])
        
        if template:
            extra_args.extend(['--reference-doc', template])
        
        # 构建资源路径列表
        resource_paths = []
        
        # 添加 Markdown 文件所在目录（图片通常是相对路径）
        resource_paths.append(str(md_path.parent))
        
        # 添加图片目录
        if images_dir and Path(images_dir).exists():
            resource_paths.append(str(images_dir))
        
        # 设置资源搜索路径
        if resource_paths:
            extra_args.extend(['--resource-path', ':'.join(resource_paths)])
        
        kwargs['extra_args'] = extra_args
        
        # 设置工作目录为 Markdown 文件所在目录，确保相对路径图片能被找到
        cwd = md_path.parent
        
        return self.convert(
            md_path,
            output_path,
            input_format='markdown',
            output_format='docx',
            cwd=str(cwd),
            **kwargs
        )
    
    def markdown_to_pdf(
        self,
        md_path: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Markdown转PDF"""
        return self.convert(
            md_path,
            output_path,
            input_format='markdown',
            output_format='pdf',
            **kwargs
        )
    
    def markdown_to_epub(
        self,
        md_path: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Markdown转EPUB"""
        return self.convert(
            md_path,
            output_path,
            input_format='markdown',
            output_format='epub',
            **kwargs
        )
    
    def markdown_to_html(
        self,
        md_path: str,
        output_path: str,
        standalone: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Markdown转HTML"""
        if standalone:
            kwargs['extra_args'] = kwargs.get('extra_args', [])
            kwargs['extra_args'].append('--standalone')
        
        return self.convert(
            md_path,
            output_path,
            input_format='markdown',
            output_format='html',
            **kwargs
        )
    
    def word_to_markdown(
        self,
        docx_path: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Word转Markdown"""
        return self.convert(
            docx_path,
            output_path,
            input_format='docx',
            output_format='markdown',
            **kwargs
        )
    
    def _detect_format(self, file_path: Path) -> Optional[str]:
        """根据文件扩展名检测格式"""
        ext = file_path.suffix.lower()
        
        format_map = {
            '.md': 'markdown',
            '.markdown': 'markdown',
            '.docx': 'docx',
            '.doc': 'doc',
            '.pdf': 'pdf',
            '.epub': 'epub',
            '.html': 'html',
            '.htm': 'html',
            '.odt': 'odt',
            '.rtf': 'rtf',
            '.tex': 'latex',
            '.txt': 'plain',
        }
        
        return format_map.get(ext)
    
    def get_supported_formats(self) -> Dict[str, str]:
        """获取支持的格式列表"""
        return self.SUPPORTED_FORMATS.copy()
