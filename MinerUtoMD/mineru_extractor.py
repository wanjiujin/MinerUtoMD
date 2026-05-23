"""
MinerU PDF 提取模块
支持 MinerU 3.x (mineru) 和旧版 (magic-pdf)
"""
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class MinerUExtractor:
    """MinerU PDF提取器"""
    
    # 新版 MinerU 3.x CLI 路径
    MINERU_CLI_V3 = r"C:\ProgramData\miniforge3\envs\mineru2\Scripts\mineru.exe"
    # 旧版 magic-pdf CLI 路径
    MINERU_CLI_V1 = r"C:\ProgramData\miniforge3\envs\mineru\Scripts\magic-pdf.exe"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化提取器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.keep_images = self.config.get('keep_images', True)
        self.image_dir = self.config.get('image_dir', 'images')
        # MinerU 解析方法: ocr, txt, auto
        self.parse_method = self.config.get('parse_method', 'auto')
        self.ocr_lang = self.config.get('ocr_lang', 'ch')
        # 公式识别
        self.enable_formula = self.config.get('enable_formula', True)
        # 表格识别
        self.enable_table = self.config.get('enable_table', False)
        # 后端: pipeline (本地模型), hybrid-auto-engine (需要VLM模型)
        self.backend = self.config.get('backend', 'pipeline')
        
        # 检测使用哪个版本
        self._detect_version()
    
    def _detect_version(self):
        """检测 MinerU 版本"""
        if Path(self.MINERU_CLI_V3).exists():
            self.cli_path = self.MINERU_CLI_V3
            self.version = 3
            logger.info("使用 MinerU 3.x (支持公式识别)")
        elif Path(self.MINERU_CLI_V1).exists():
            self.cli_path = self.MINERU_CLI_V1
            self.version = 1
            logger.info("使用 MinerU 1.x (magic-pdf, 不支持公式识别)")
        else:
            self.cli_path = None
            self.version = None
            logger.warning("未找到 MinerU 安装")
    
    def check_installation(self) -> bool:
        """检查MinerU是否正确安装"""
        if self.cli_path and Path(self.cli_path).exists():
            return True
        
        # 检查PATH
        for cmd in ['mineru', 'magic-pdf']:
            try:
                result = subprocess.run(
                    [cmd, '--version'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return True
            except FileNotFoundError:
                continue
        
        logger.error("MinerU未安装，请运行: pip install mineru[full]")
        return False
    
    def _setup_environment(self) -> dict:
        """设置环境变量"""
        env = os.environ.copy()
        
        # 设置 HuggingFace 镜像（解决国内访问问题）
        env['HF_ENDPOINT'] = 'https://hf-mirror.com'
        # 设置短路径缓存目录（解决 Windows 路径长度限制）
        env['HF_HOME'] = 'C:/hf_cache'
        
        return env
    
    def extract(
        self,
        pdf_path: str,
        output_dir: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        提取PDF内容为Markdown
        
        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录
            **kwargs: 额外参数
                - start_page: 起始页码
                - end_page: 结束页码
                - enable_formula: 是否启用公式识别
                - enable_table: 是否启用表格识别
            
        Returns:
            包含提取结果的字典:
            - success: 是否成功
            - markdown_path: Markdown文件路径
            - images_dir: 图片目录路径
            - error: 错误信息（如果失败）
        """
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        
        if not pdf_path.exists():
            return {
                'success': False,
                'error': f'PDF文件不存在: {pdf_path}'
            }
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 设置环境变量
            env = self._setup_environment()
            
            # 根据版本构建命令
            if self.version == 3:
                cmd = self._build_v3_command(pdf_path, output_dir, **kwargs)
            else:
                cmd = self._build_v1_command(pdf_path, output_dir, **kwargs)
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            
            # 执行命令 - 增加超时时间
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=env,
                timeout=600  # 10分钟超时
            )
            
            if result.returncode != 0:
                logger.error(f"MinerU执行失败: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr
                }
            
            # 查找输出的Markdown文件
            markdown_path = self._find_markdown_output(output_dir, pdf_path)
            
            if not markdown_path:
                return {
                    'success': False,
                    'error': '未找到输出的Markdown文件'
                }
            
            # 查找图片目录
            images_dir = self._find_images_dir(output_dir, markdown_path)
            
            logger.info(f"PDF提取成功: {markdown_path}")
            
            return {
                'success': True,
                'markdown_path': str(markdown_path),
                'images_dir': str(images_dir) if images_dir else None,
                'output_dir': str(output_dir)
            }
            
        except Exception as e:
            logger.error(f"PDF提取异常: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _build_v3_command(self, pdf_path: Path, output_dir: Path, **kwargs) -> list:
        """构建 MinerU 3.x 命令"""
        cmd = [
            self.cli_path,
            '-p', str(pdf_path),
            '-o', str(output_dir),
            '-b', self.backend,  # pipeline, hybrid-auto-engine
            '-m', self.parse_method,
            '-l', self.ocr_lang,
        ]
        
        # 公式识别
        enable_formula = kwargs.get('enable_formula', self.enable_formula)
        cmd.extend(['-f', str(enable_formula).lower()])
        
        # 表格识别
        enable_table = kwargs.get('enable_table', self.enable_table)
        cmd.extend(['-t', str(enable_table).lower()])
        
        # 页码范围
        if 'start_page' in kwargs:
            cmd.extend(['--start', str(kwargs['start_page'])])
        if 'end_page' in kwargs:
            cmd.extend(['--end', str(kwargs['end_page'])])
        
        return cmd
    
    def _build_v1_command(self, pdf_path: Path, output_dir: Path, **kwargs) -> list:
        """构建 MinerU 1.x (magic-pdf) 命令"""
        cmd = [
            self.cli_path,
            '-p', str(pdf_path),
            '-o', str(output_dir),
            '-m', self.parse_method,
            '-l', self.ocr_lang,
        ]
        
        return cmd
    
    def _find_markdown_output(self, output_dir: Path, pdf_path: Path) -> Optional[Path]:
        """查找输出的 Markdown 文件"""
        pdf_name = pdf_path.stem
        
        # 可能的输出路径
        possible_paths = [
            # MinerU 3.x 输出路径
            output_dir / pdf_name / 'auto' / f"{pdf_name}.md",
            output_dir / pdf_name / f"{pdf_name}.md",
            # MinerU 1.x 输出路径
            output_dir / f"{pdf_name}" / f"{pdf_name}.md",
            output_dir / f"{pdf_name}.md",
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # 尝试查找任何 .md 文件
        md_files = list(output_dir.rglob('*.md'))
        if md_files:
            return md_files[0]
        
        return None
    
    def _find_images_dir(self, output_dir: Path, markdown_path: Path) -> Optional[Path]:
        """查找图片目录"""
        if not self.keep_images:
            return None
        
        # 可能的图片目录
        possible_dirs = [
            markdown_path.parent / self.image_dir,
            markdown_path.parent / 'images',
            output_dir / self.image_dir,
        ]
        
        for img_dir in possible_dirs:
            if img_dir.exists() and img_dir.is_dir():
                return img_dir
        
        return None
    
    def batch_extract(
        self,
        pdf_dir: str,
        output_dir: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        批量提取PDF文件
        
        Args:
            pdf_dir: PDF文件目录
            output_dir: 输出目录
            **kwargs: 额外参数
            
        Returns:
            批量提取结果
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
        
        for pdf_file in pdf_files:
            logger.info(f"处理: {pdf_file.name}")
            result = self.extract(
                str(pdf_file),
                str(output_dir / pdf_file.stem),
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
