"""
文档转换工作流模块
"""
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

try:
    from .mineru_extractor import MinerUExtractor
    from .pandoc_converter import PandocConverter
    from .markdown_optimizer import MarkdownOptimizer
except ImportError:
    from mineru_extractor import MinerUExtractor
    from pandoc_converter import PandocConverter
    from markdown_optimizer import MarkdownOptimizer

logger = logging.getLogger(__name__)


class PDFWorkflow:
    """PDF工作流：PDF → MD → 多格式"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化工作流
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        mineru_config = self.config.get('mineru', {})
        pandoc_config = self.config.get('pandoc', {})
        
        # 设置 Pandoc 路径
        if 'path' in pandoc_config:
            pandoc_config['pandoc_path'] = pandoc_config['path']
        
        self.mineru = MinerUExtractor(mineru_config)
        self.pandoc = PandocConverter(pandoc_config)
        self.optimizer = MarkdownOptimizer(self.config.get('markdown_optimizer', {}))
    
    def run(
        self,
        pdf_path: str,
        output_dir: str,
        output_formats: List[str] = ['md'],
        keep_intermediate: bool = False,
        enable_formula: bool = True,
        enable_table: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行PDF工作流
        
        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录
            output_formats: 输出格式列表，支持: md, docx, pdf, epub, html
            keep_intermediate: 是否保留中间文件
            enable_formula: 是否启用公式识别
            enable_table: 是否启用表格识别
            **kwargs: 额外参数
            
        Returns:
            工作流结果字典
        """
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_name = pdf_path.stem
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 中间文件目录
        temp_dir = output_dir / f'.temp_{timestamp}'
        temp_dir.mkdir(exist_ok=True)
        
        results = {
            'success': False,
            'input_file': str(pdf_path),
            'output_dir': str(output_dir),
            'outputs': {},
            'errors': []
        }
        
        try:
            # 步骤1: PDF → Markdown
            logger.info(f"[1/3] 提取PDF内容: {pdf_path.name}")
            extract_result = self.mineru.extract(
                str(pdf_path),
                str(temp_dir),
                enable_formula=enable_formula,
                enable_table=enable_table,
                **kwargs
            )
            
            if not extract_result['success']:
                results['errors'].append(f"PDF提取失败: {extract_result['error']}")
                return results
            
            md_path = Path(extract_result['markdown_path'])
            images_dir = extract_result.get('images_dir')
            logger.info(f"✓ Markdown生成: {md_path}")
            if images_dir:
                logger.info(f"✓ 图片目录: {images_dir}")
            
            # 步骤2: 优化Markdown（在原目录进行，保持图片相对路径正确）
            logger.info(f"[2/3] 优化Markdown格式")
            optimized_md_path = md_path.parent / f"{pdf_name}_optimized.md"
            optimize_result = self.optimizer.optimize(
                str(md_path),
                str(optimized_md_path)
            )
            
            if not optimize_result['success']:
                logger.warning(f"Markdown优化失败，使用原始文件: {optimize_result['error']}")
                optimized_md_path = md_path
            
            # 步骤3: 转换为目标格式
            logger.info(f"[3/3] 转换为: {', '.join(output_formats)}")
            
            for fmt in output_formats:
                fmt = fmt.lower()
                
                if fmt == 'md':
                    # 复制Markdown到输出目录
                    output_path = output_dir / f"{pdf_name}.md"
                    shutil.copy2(str(optimized_md_path), str(output_path))
                    results['outputs']['md'] = str(output_path)
                    logger.info(f"✓ Markdown: {output_path}")
                    
                    # 复制图片文件夹到输出目录
                    if images_dir and Path(images_dir).exists():
                        output_images_dir = output_dir / 'images'
                        if output_images_dir.exists():
                            shutil.rmtree(str(output_images_dir))
                        shutil.copytree(str(images_dir), str(output_images_dir))
                        logger.info(f"✓ 图片目录: {output_images_dir}")
                
                elif fmt == 'docx':
                    output_path = output_dir / f"{pdf_name}.docx"
                    result = self.pandoc.markdown_to_word(
                        str(optimized_md_path),
                        str(output_path),
                        images_dir=images_dir
                    )
                    if result['success']:
                        results['outputs']['docx'] = str(output_path)
                        logger.info(f"✓ Word: {output_path}")
                    else:
                        results['errors'].append(f"Word转换失败: {result['error']}")
                
                elif fmt == 'pdf':
                    output_path = output_dir / f"{pdf_name}.pdf"
                    result = self.pandoc.markdown_to_pdf(
                        str(optimized_md_path),
                        str(output_path)
                    )
                    if result['success']:
                        results['outputs']['pdf'] = str(output_path)
                        logger.info(f"✓ PDF: {output_path}")
                    else:
                        results['errors'].append(f"PDF转换失败: {result['error']}")
                
                elif fmt == 'epub':
                    output_path = output_dir / f"{pdf_name}.epub"
                    result = self.pandoc.markdown_to_epub(
                        str(optimized_md_path),
                        str(output_path)
                    )
                    if result['success']:
                        results['outputs']['epub'] = str(output_path)
                        logger.info(f"✓ EPUB: {output_path}")
                    else:
                        results['errors'].append(f"EPUB转换失败: {result['error']}")
                
                elif fmt == 'html':
                    output_path = output_dir / f"{pdf_name}.html"
                    result = self.pandoc.markdown_to_html(
                        str(optimized_md_path),
                        str(output_path)
                    )
                    if result['success']:
                        results['outputs']['html'] = str(output_path)
                        logger.info(f"✓ HTML: {output_path}")
                    else:
                        results['errors'].append(f"HTML转换失败: {result['error']}")
                
                else:
                    logger.warning(f"不支持的格式: {fmt}")
            
            # 复制图片目录（如果存在）
            if extract_result.get('images_dir'):
                images_src = Path(extract_result['images_dir'])
                images_dst = output_dir / 'images'
                if images_src.exists():
                    if images_dst.exists():
                        shutil.rmtree(str(images_dst))
                    shutil.copytree(str(images_src), str(images_dst))
                    results['outputs']['images'] = str(images_dst)
            
            results['success'] = len(results['outputs']) > 0
            
        except Exception as e:
            logger.error(f"工作流执行异常: {str(e)}")
            results['errors'].append(str(e))
        
        finally:
            # 清理临时文件
            if not keep_intermediate and temp_dir.exists():
                shutil.rmtree(str(temp_dir))
        
        return results
    
    def batch_run(
        self,
        pdf_dir: str,
        output_dir: str,
        output_formats: List[str] = ['md'],
        **kwargs
    ) -> Dict[str, Any]:
        """
        批量处理PDF文件
        
        Args:
            pdf_dir: PDF文件目录
            output_dir: 输出目录
            output_formats: 输出格式列表
            **kwargs: 额外参数
            
        Returns:
            批量处理结果
        """
        pdf_dir = Path(pdf_dir)
        output_dir = Path(output_dir)
        
        if not pdf_dir.exists():
            return {
                'success': False,
                'error': f'目录不存在: {pdf_dir}'
            }
        
        pdf_files = list(pdf_dir.glob('*.pdf')) + list(pdf_dir.glob('*.PDF'))
        
        if not pdf_files:
            return {
                'success': False,
                'error': f'目录中没有PDF文件: {pdf_dir}'
            }
        
        results = []
        success_count = 0
        
        for i, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"\n[{i}/{len(pdf_files)}] 处理: {pdf_file.name}")
            
            result = self.run(
                str(pdf_file),
                str(output_dir / pdf_file.stem),
                output_formats,
                **kwargs
            )
            
            results.append({
                'file': str(pdf_file),
                'result': result
            })
            
            if result['success']:
                success_count += 1
        
        return {
            'success': True,
            'total': len(pdf_files),
            'success_count': success_count,
            'failed_count': len(pdf_files) - success_count,
            'results': results
        }


class WordWorkflow:
    """Word工作流：docx → MD → 优化 → docx"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化工作流
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        pandoc_config = self.config.get('pandoc', {})
        
        # 设置 Pandoc 路径
        if 'path' in pandoc_config:
            pandoc_config['pandoc_path'] = pandoc_config['path']
        
        self.pandoc = PandocConverter(pandoc_config)
        self.optimizer = MarkdownOptimizer(self.config.get('markdown_optimizer', {}))
    
    def run(
        self,
        docx_path: str,
        output_dir: str,
        export_md_only: bool = False,
        keep_intermediate: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行Word工作流
        
        Args:
            docx_path: Word文件路径
            output_dir: 输出目录
            export_md_only: 是否只导出Markdown（不转回Word）
            keep_intermediate: 是否保留中间文件
            **kwargs: 额外参数
            
        Returns:
            工作流结果字典
        """
        docx_path = Path(docx_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        docx_name = docx_path.stem
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 中间文件目录
        temp_dir = output_dir / f'.temp_{timestamp}'
        temp_dir.mkdir(exist_ok=True)
        
        results = {
            'success': False,
            'input_file': str(docx_path),
            'output_dir': str(output_dir),
            'outputs': {},
            'errors': []
        }
        
        try:
            # 步骤1: Word → Markdown
            logger.info(f"[1/3] 转换Word为Markdown: {docx_path.name}")
            md_path = temp_dir / f"{docx_name}.md"
            
            result = self.pandoc.word_to_markdown(
                str(docx_path),
                str(md_path)
            )
            
            if not result['success']:
                results['errors'].append(f"Word转Markdown失败: {result['error']}")
                return results
            
            logger.info(f"✓ Markdown生成: {md_path}")
            
            # 步骤2: 优化Markdown
            logger.info(f"[2/3] 优化Markdown格式")
            optimized_md_path = temp_dir / f"{docx_name}_optimized.md"
            
            optimize_result = self.optimizer.optimize(
                str(md_path),
                str(optimized_md_path)
            )
            
            if not optimize_result['success']:
                logger.warning(f"Markdown优化失败，使用原始文件: {optimize_result['error']}")
                optimized_md_path = md_path
            
            # 保存优化后的Markdown到输出目录
            output_md_path = output_dir / f"{docx_name}.md"
            shutil.copy2(str(optimized_md_path), str(output_md_path))
            results['outputs']['md'] = str(output_md_path)
            logger.info(f"✓ 优化后的Markdown: {output_md_path}")
            
            # 步骤3: Markdown → Word（如果需要）
            if not export_md_only:
                logger.info(f"[3/3] 转换回Word格式")
                output_docx_path = output_dir / f"{docx_name}_optimized.docx"
                
                result = self.pandoc.markdown_to_word(
                    str(optimized_md_path),
                    str(output_docx_path)
                )
                
                if result['success']:
                    results['outputs']['docx'] = str(output_docx_path)
                    logger.info(f"✓ 优化后的Word: {output_docx_path}")
                else:
                    results['errors'].append(f"Markdown转Word失败: {result['error']}")
            
            results['success'] = len(results['outputs']) > 0
            
        except Exception as e:
            logger.error(f"工作流执行异常: {str(e)}")
            results['errors'].append(str(e))
        
        finally:
            # 清理临时文件
            if not keep_intermediate and temp_dir.exists():
                shutil.rmtree(str(temp_dir))
        
        return results
    
    def batch_run(
        self,
        docx_dir: str,
        output_dir: str,
        export_md_only: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        批量处理Word文件
        
        Args:
            docx_dir: Word文件目录
            output_dir: 输出目录
            export_md_only: 是否只导出Markdown
            **kwargs: 额外参数
            
        Returns:
            批量处理结果
        """
        docx_dir = Path(docx_dir)
        output_dir = Path(output_dir)
        
        if not docx_dir.exists():
            return {
                'success': False,
                'error': f'目录不存在: {docx_dir}'
            }
        
        docx_files = (
            list(docx_dir.glob('*.docx')) + 
            list(docx_dir.glob('*.DOCX')) +
            list(docx_dir.glob('*.doc')) +
            list(docx_dir.glob('*.DOC'))
        )
        
        if not docx_files:
            return {
                'success': False,
                'error': f'目录中没有Word文件: {docx_dir}'
            }
        
        results = []
        success_count = 0
        
        for i, docx_file in enumerate(docx_files, 1):
            logger.info(f"\n[{i}/{len(docx_files)}] 处理: {docx_file.name}")
            
            result = self.run(
                str(docx_file),
                str(output_dir / docx_file.stem),
                export_md_only,
                **kwargs
            )
            
            results.append({
                'file': str(docx_file),
                'result': result
            })
            
            if result['success']:
                success_count += 1
        
        return {
            'success': True,
            'total': len(docx_files),
            'success_count': success_count,
            'failed_count': len(docx_files) - success_count,
            'results': results
        }
