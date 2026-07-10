"""
文档转换工作流模块
"""
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from .mineru_extractor import MinerUExtractor
    from .pandoc_converter import PandocConverter
    from .markdown_optimizer import MarkdownOptimizer
    from .quality_checker import check_outputs
    from .task_manifest import TaskManifest
except ImportError:
    from mineru_extractor import MinerUExtractor
    from pandoc_converter import PandocConverter
    from markdown_optimizer import MarkdownOptimizer
    from quality_checker import check_outputs
    from task_manifest import TaskManifest

# 水印去除为可选功能
try:
    from .watermark_remover import WatermarkRemover
    HAS_WATERMARK_REMOVER = True
except ImportError:
    try:
        from watermark_remover import WatermarkRemover
        HAS_WATERMARK_REMOVER = True
    except ImportError:
        WatermarkRemover = None
        HAS_WATERMARK_REMOVER = False

logger = logging.getLogger(__name__)


def _cleanup_temp_dir(temp_dir: Path, retries: int = 3, delay: float = 1.0) -> None:
    if not temp_dir.exists():
        return

    for attempt in range(1, retries + 1):
        try:
            shutil.rmtree(str(temp_dir))
            return
        except PermissionError as exc:
            if attempt >= retries:
                logger.warning(f"临时目录清理失败，可能有外部进程仍在占用文件: {temp_dir} ({exc})")
                return
            time.sleep(delay)
        except OSError as exc:
            logger.warning(f"临时目录清理失败: {temp_dir} ({exc})")
            return


def _unique_files(directory: Path, patterns: List[str]) -> List[Path]:
    files = {}
    for pattern in patterns:
        for path in directory.glob(pattern):
            key = str(path.resolve()).lower()
            files[key] = path
    return sorted(files.values(), key=lambda item: item.name.lower())


def _safe_output_path(output_dir: Path, input_path: Path, suffix: str, fallback_suffix: str = "_optimized") -> Path:
    output_path = output_dir / f"{input_path.stem}{suffix}"
    try:
        if output_path.resolve() == input_path.resolve():
            output_path = output_dir / f"{input_path.stem}{fallback_suffix}{suffix}"
    except OSError:
        pass
    return output_path


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
        
        # 水印去除为可选功能
        if HAS_WATERMARK_REMOVER:
            self.watermark_remover = WatermarkRemover(self.config.get('watermark_remover', {}))
        else:
            self.watermark_remover = None
    
    def run(
        self,
        pdf_path: str,
        output_dir: str,
        output_formats: Optional[List[str]] = None,
        keep_intermediate: bool = False,
        enable_formula: bool = True,
        enable_table: bool = False,
        remove_watermark: bool = False,
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
            remove_watermark: 是否去除水印
            **kwargs: 额外参数
            
        Returns:
            工作流结果字典
        """
        if output_formats is None:
            output_formats = ['md']
        
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
            step_times = {}
            total_start = datetime.now()
            
            # 步骤0: 水印去除（如果启用且有依赖）
            actual_pdf_path = pdf_path
            if remove_watermark:
                step_start = datetime.now()
                if not HAS_WATERMARK_REMOVER or self.watermark_remover is None:
                    logger.warning("水印去除功能不可用：缺少 opencv-python 或 pymupdf 依赖")
                else:
                    logger.info(f"[0/3] 去除PDF水印: {pdf_path.name}")
                    watermarked_pdf = temp_dir / f"{pdf_name}_no_watermark.pdf"
                    wm_result = self.watermark_remover.remove_watermark_from_pdf(
                        str(pdf_path),
                        str(watermarked_pdf)
                    )
                    if wm_result['success']:
                        actual_pdf_path = watermarked_pdf
                        logger.info(f"✓ 水印去除成功，处理了 {wm_result.get('processed_pages', 0)} 页")
                    else:
                        logger.warning(f"水印去除失败: {wm_result.get('error', '未知错误')}，使用原始PDF")
                step_times['watermark'] = (datetime.now() - step_start).total_seconds()
            
            # 步骤1: PDF → Markdown
            step_start = datetime.now()
            logger.info(f"[1/3] 提取PDF内容: {pdf_path.name}")
            extract_result = self.mineru.extract(
                str(actual_pdf_path),
                str(temp_dir),
                enable_formula=enable_formula,
                enable_table=enable_table,
                **kwargs
            )
            step_times['mineru_extract'] = (datetime.now() - step_start).total_seconds()
            
            if not extract_result['success']:
                error_msg = extract_result.get('error', '未知错误')
                logger.error(f"PDF提取失败: {error_msg}")
                results['errors'].append(f"PDF提取失败: {error_msg}")
                return results
            
            logger.info(f"✓ PDF提取成功 (耗时{step_times['mineru_extract']:.1f}秒)")
            
            md_path = Path(extract_result['markdown_path'])
            images_dir = extract_result.get('images_dir')
            logger.info(f"✓ Markdown生成: {md_path}")
            if images_dir:
                logger.info(f"✓ 图片目录: {images_dir}")
            
            # 步骤2: 优化Markdown（在原目录进行，保持图片相对路径正确）
            step_start = datetime.now()
            logger.info(f"[2/3] 优化Markdown格式")
            optimized_md_path = md_path.parent / f"{pdf_name}_optimized.md"
            optimize_result = self.optimizer.optimize(
                str(md_path),
                str(optimized_md_path)
            )
            step_times['markdown_optimize'] = (datetime.now() - step_start).total_seconds()
            
            if not optimize_result['success']:
                logger.warning(f"Markdown优化失败，使用原始文件: {optimize_result['error']}")
                optimized_md_path = md_path
            else:
                logger.info(f"✓ Markdown优化完成 (耗时{step_times['markdown_optimize']:.1f}秒)")
            
            # 步骤3: 转换为目标格式
            step_start = datetime.now()
            logger.info(f"[3/3] 转换为: {', '.join(output_formats)}")
            
            for fmt in output_formats:
                fmt = fmt.lower()
                fmt_start = datetime.now()
                
                if fmt == 'md':
                    # 复制Markdown到输出目录
                    output_path = output_dir / f"{pdf_name}.md"
                    shutil.copy2(str(optimized_md_path), str(output_path))
                    
                    # 复制图片文件夹到输出目录（统一命名为 images）
                    if images_dir and Path(images_dir).exists():
                        output_images_dir = output_dir / 'images'
                        shutil.copytree(str(images_dir), str(output_images_dir), dirs_exist_ok=True)
                        logger.info(f"✓ 图片目录: {output_images_dir}")
                    
                    # 修正 Markdown 中的图片路径，确保与输出目录结构匹配
                    # MinerU 可能生成 images/xxx.jpg 或 auto/images/xxx.jpg
                    # 统一为 images/xxx.jpg（与 Obsidian 兼容）
                    self._fix_markdown_image_paths(str(output_path), str(output_dir))
                    
                    results['outputs']['md'] = str(output_path)
                    logger.info(f"✓ Markdown: {output_path}")
                
                elif fmt == 'docx':
                    output_path = output_dir / f"{pdf_name}.docx"
                    result = self.pandoc.markdown_to_word(
                        str(optimized_md_path),
                        str(output_path),
                        images_dir=images_dir
                    )
                    if result['success']:
                        results['outputs']['docx'] = str(output_path)
                        logger.info(f"✓ Word: {output_path} (耗时{(datetime.now()-fmt_start).total_seconds():.1f}秒)")
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
                        logger.info(f"✓ PDF: {output_path} (耗时{(datetime.now()-fmt_start).total_seconds():.1f}秒)")
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
                        logger.info(f"✓ EPUB: {output_path} (耗时{(datetime.now()-fmt_start).total_seconds():.1f}秒)")
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
                        logger.info(f"✓ HTML: {output_path} (耗时{(datetime.now()-fmt_start).total_seconds():.1f}秒)")
                    else:
                        results['errors'].append(f"HTML转换失败: {result['error']}")
                
                else:
                    logger.warning(f"不支持的格式: {fmt}")
            
            step_times['format_conversion'] = (datetime.now() - step_start).total_seconds()
            
            # 复制图片目录（如果存在）
            if extract_result.get('images_dir'):
                images_src = Path(extract_result['images_dir'])
                images_dst = output_dir / 'images'
                if images_src.exists():
                    shutil.copytree(str(images_src), str(images_dst), dirs_exist_ok=True)
                    results['outputs']['images'] = str(images_dst)
            
            results['success'] = len(results['outputs']) > 0
            if results['outputs']:
                write_report = self.config.get('output', {}).get('write_quality_report', False)
                results['quality'] = check_outputs(results['outputs'], str(output_dir), write_report=write_report)
                if not results['quality']['ok']:
                    results['errors'].append('输出质量检查发现问题，请查看日志')
            total_time = (datetime.now() - total_start).total_seconds()
            
            # 输出各步骤耗时统计
            logger.info(f"=== 处理完成，总耗时: {total_time:.1f}秒 ===")
            for step, t in step_times.items():
                logger.info(f"  {step}: {t:.1f}秒")
            
        except Exception as e:
            logger.error(f"工作流执行异常: {str(e)}")
            results['errors'].append(str(e))
        
        finally:
            # 清理临时文件
            if not keep_intermediate and temp_dir.exists():
                _cleanup_temp_dir(temp_dir)
        
        return results
    
    def _fix_markdown_image_paths(self, md_path: str, output_dir: str) -> None:
        """
        修正 Markdown 中的图片路径，确保与输出目录结构匹配
        
        MinerU 可能生成:
        - images/xxx.jpg（相对路径）
        - auto/images/xxx.jpg（嵌套路径）
        - ./images/xxx.jpg（带点路径）
        - 绝对路径如 D:/xxx/images/xxx.jpg
        
        统一修正为 images/xxx.jpg（与 Obsidian 等兼容）
        """
        try:
            md_file = Path(md_path)
            if not md_file.exists():
                return
            
            content = md_file.read_text(encoding='utf-8')
            import re
            
            # 匹配 Markdown 图片语法: ![alt](path)
            # 也匹配 HTML img: <img src="path">
            original_content = content
            
            # 方案1: 匹配 ![alt](path) 或 ![alt](path "title")
            def fix_image_path(match):
                alt = match.group(1)
                path = match.group(2)
                
                # 如果路径已经是 images/xxx 格式，保持不变
                if path.startswith('images/'):
                    return match.group(0)
                
                # 提取文件名
                path_obj = Path(path)
                filename = path_obj.name
                
                if not filename:
                    return match.group(0)
                
                # 统一为 images/filename
                new_path = f"images/{filename}"
                return f"![{alt}]({new_path})"
            
            content = re.sub(r'!\[([^\]]*)\]\(([^)"\s]+)(?:\s+"[^"]*")?\)', fix_image_path, content)
            
            # 方案2: 匹配 <img src="path">
            def fix_img_src(match):
                path = match.group(1)
                path_obj = Path(path)
                filename = path_obj.name
                
                if not filename:
                    return match.group(0)
                
                new_path = f"images/{filename}"
                return f'<img src="{new_path}"'
            
            content = re.sub(r'<img\s+src="([^"]+)"', fix_img_src, content)
            
            # 如果有修改，写回文件
            if content != original_content:
                md_file.write_text(content, encoding='utf-8')
                logger.info(f"✓ 修正图片路径: {md_path}")
                
        except Exception as e:
            logger.warning(f"修正图片路径时出错: {e}")
    
    def batch_run(
        self,
        pdf_dir: str,
        output_dir: str,
        output_formats: Optional[List[str]] = None,
        resume: bool = False,
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
        if output_formats is None:
            output_formats = ['md']
        
        pdf_dir = Path(pdf_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest = TaskManifest(output_dir / 'conversion_manifest.json')
        
        print(f"[batch_run] pdf_dir={pdf_dir}, output_dir={output_dir}")
        
        if not pdf_dir.exists():
            print(f"[batch_run] 目录不存在: {pdf_dir}")
            return {
                'success': False,
                'error': f'目录不存在: {pdf_dir}'
            }
        
        pdf_files = _unique_files(pdf_dir, ['*.pdf', '*.PDF'])
        
        print(f"[batch_run] 找到 {len(pdf_files)} 个PDF文件")
        
        if not pdf_files:
            return {
                'success': False,
                'error': f'目录中没有PDF文件: {pdf_dir}'
            }
        
        results = []
        success_count = 0
        skipped_count = 0
        
        for i, pdf_file in enumerate(pdf_files, 1):
            if resume and manifest.is_success(pdf_file):
                logger.info(f"\n[{i}/{len(pdf_files)}] 跳过已完成: {pdf_file.name}")
                skipped_count += 1
                success_count += 1
                continue
            
            logger.info(f"\n[{i}/{len(pdf_files)}] 处理: {pdf_file.name}")
            
            # 为每个文件创建单独的输出目录
            file_output_dir = output_dir / pdf_file.stem
            file_output_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"调用 run() 处理: {pdf_file} -> {file_output_dir}")
            manifest.mark_running(
                pdf_file,
                file_output_dir,
                {"formats": output_formats, "resume": resume, **kwargs}
            )
            
            result = self.run(
                str(pdf_file),
                str(file_output_dir),
                output_formats,
                **kwargs
            )
            
            logger.info(f"run() 返回: success={result.get('success')}")
            manifest.mark_result(pdf_file, result)
            
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
            'skipped_count': skipped_count,
            'failed_count': len(pdf_files) - success_count,
            'manifest_path': str(manifest.path),
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
        output_formats: Optional[List[str]] = None,
        export_md_only: bool = False,
        keep_intermediate: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行Word工作流
        
        Args:
            docx_path: Word文件路径
            output_dir: 输出目录
            output_formats: 输出格式列表，支持: md, docx, pdf, epub, html
            export_md_only: 是否只导出Markdown（兼容旧参数）
            keep_intermediate: 是否保留中间文件
            **kwargs: 额外参数
            
        Returns:
            工作流结果字典
        """
        docx_path = Path(docx_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if output_formats is None:
            output_formats = ['md'] if export_md_only else ['docx']
        output_formats = [fmt.lower() for fmt in output_formats]
        if export_md_only and 'md' not in output_formats:
            output_formats = ['md']
        
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
            
            # 步骤3: Markdown → 目标格式
            logger.info(f"[3/3] 转换为: {', '.join(output_formats)}")
            for fmt in output_formats:
                if fmt == 'md':
                    output_md_path = _safe_output_path(output_dir, docx_path, '.md')
                    shutil.copy2(str(optimized_md_path), str(output_md_path))
                    results['outputs']['md'] = str(output_md_path)
                    logger.info(f"✓ Markdown: {output_md_path}")
                elif fmt == 'docx':
                    output_docx_path = _safe_output_path(output_dir, docx_path, '.docx')
                    result = self.pandoc.markdown_to_word(
                        str(optimized_md_path),
                        str(output_docx_path)
                    )
                    if result['success']:
                        results['outputs']['docx'] = str(output_docx_path)
                        logger.info(f"✓ Word: {output_docx_path}")
                    else:
                        results['errors'].append(f"Word转换失败: {result['error']}")
                elif fmt == 'pdf':
                    output_pdf_path = _safe_output_path(output_dir, docx_path, '.pdf')
                    result = self.pandoc.markdown_to_pdf(
                        str(optimized_md_path),
                        str(output_pdf_path)
                    )
                    if result['success']:
                        results['outputs']['pdf'] = str(output_pdf_path)
                        logger.info(f"✓ PDF: {output_pdf_path}")
                    else:
                        results['errors'].append(f"PDF转换失败: {result['error']}")
                elif fmt == 'epub':
                    output_epub_path = _safe_output_path(output_dir, docx_path, '.epub')
                    result = self.pandoc.markdown_to_epub(
                        str(optimized_md_path),
                        str(output_epub_path)
                    )
                    if result['success']:
                        results['outputs']['epub'] = str(output_epub_path)
                        logger.info(f"✓ EPUB: {output_epub_path}")
                    else:
                        results['errors'].append(f"EPUB转换失败: {result['error']}")
                elif fmt == 'html':
                    output_html_path = _safe_output_path(output_dir, docx_path, '.html')
                    result = self.pandoc.markdown_to_html(
                        str(optimized_md_path),
                        str(output_html_path)
                    )
                    if result['success']:
                        results['outputs']['html'] = str(output_html_path)
                        logger.info(f"✓ HTML: {output_html_path}")
                    else:
                        results['errors'].append(f"HTML转换失败: {result['error']}")
                else:
                    logger.warning(f"不支持的格式: {fmt}")
            
            results['success'] = len(results['outputs']) > 0
            if results['outputs']:
                write_report = self.config.get('output', {}).get('write_quality_report', False)
                results['quality'] = check_outputs(results['outputs'], str(output_dir), write_report=write_report)
                if not results['quality']['ok']:
                    results['errors'].append('输出质量检查发现问题，请查看日志')
            
        except Exception as e:
            logger.error(f"工作流执行异常: {str(e)}")
            results['errors'].append(str(e))
        
        finally:
            # 清理临时文件
            if not keep_intermediate and temp_dir.exists():
                _cleanup_temp_dir(temp_dir)
        
        return results
    
    def batch_run(
        self,
        docx_dir: str,
        output_dir: str,
        output_formats: Optional[List[str]] = None,
        export_md_only: bool = False,
        resume: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        批量处理Word文件
        
        Args:
            docx_dir: Word文件目录
            output_dir: 输出目录
            output_formats: 输出格式列表
            export_md_only: 是否只导出Markdown
            **kwargs: 额外参数
            
        Returns:
            批量处理结果
        """
        docx_dir = Path(docx_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest = TaskManifest(output_dir / 'conversion_manifest.json')
        
        if not docx_dir.exists():
            return {
                'success': False,
                'error': f'目录不存在: {docx_dir}'
            }
        
        docx_files = _unique_files(docx_dir, ['*.docx', '*.DOCX', '*.doc', '*.DOC'])
        
        if not docx_files:
            return {
                'success': False,
                'error': f'目录中没有Word文件: {docx_dir}'
            }
        
        results = []
        success_count = 0
        skipped_count = 0
        
        for i, docx_file in enumerate(docx_files, 1):
            if resume and manifest.is_success(docx_file):
                logger.info(f"\n[{i}/{len(docx_files)}] 跳过已完成: {docx_file.name}")
                skipped_count += 1
                success_count += 1
                continue
            
            logger.info(f"\n[{i}/{len(docx_files)}] 处理: {docx_file.name}")
            file_output_dir = output_dir
            manifest.mark_running(
                docx_file,
                file_output_dir,
                {"output_formats": output_formats, "export_md_only": export_md_only, "resume": resume, **kwargs}
            )
            
            result = self.run(
                str(docx_file),
                str(file_output_dir),
                output_formats=output_formats,
                export_md_only=export_md_only,
                **kwargs
            )
            manifest.mark_result(docx_file, result)
            
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
            'skipped_count': skipped_count,
            'failed_count': len(docx_files) - success_count,
            'manifest_path': str(manifest.path),
            'results': results
        }
