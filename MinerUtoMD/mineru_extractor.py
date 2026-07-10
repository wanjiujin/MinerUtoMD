"""
MinerU PDF 提取模块
支持 MinerU 3.x (mineru) 和旧版 (magic-pdf)
"""
import os
import subprocess
import shutil
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Windows 上隐藏子进程窗口
if sys.platform == 'win32':
    SUBPROCESS_FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
else:
    SUBPROCESS_FLAGS = 0



class MinerUExtractor:
    """MinerU PDF提取器"""
    
    # 可移植默认值：优先使用当前环境和 PATH；本机固定路径由 init_environment.py 写入配置。
    PYTHON_V3 = None
    PYTHON_V1 = None
    MINERU_CLI_V3 = None
    MINERU_CLI_V1 = None
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化提取器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        python_exe = self.config.get('python_exe')
        self.python_v3 = self.config.get('python_v3') or self.config.get('python_exe_v3') or python_exe or self.PYTHON_V3
        self.python_v1 = self.config.get('python_v1') or self.config.get('python_exe_v1') or self.PYTHON_V1
        self.mineru_cli_v3 = self.config.get('mineru_cli_v3') or shutil.which('mineru') or self.MINERU_CLI_V3
        self.mineru_cli_v1 = self.config.get('mineru_cli_v1') or shutil.which('magic-pdf') or self.MINERU_CLI_V1
        self.keep_images = self.config.get('keep_images', True)
        self.image_dir = self.config.get('image_dir', 'images')
        # MinerU 解析方法: ocr, txt, auto
        self.parse_method = self.config.get('parse_method', 'auto')
        self.ocr_lang = self.config.get('ocr_lang', 'ch')
        # 公式识别
        self.enable_formula = self.config.get('enable_formula', True)
        # 表格识别
        self.enable_table = self.config.get('enable_table', False)
        # MinerU 子进程超时秒数
        self.timeout = int(self.config.get('timeout', self.config.get('mineru_timeout', 1800)))
        # 后端: pipeline (本地模型), hybrid-auto-engine (需要VLM模型)
        self.backend = self.config.get('backend', 'pipeline')
        # 设备: auto (自动检测), cuda (GPU), cpu, npu
        self.device = self.config.get('device', 'auto')
        
        # 检测使用哪个版本
        self._detect_version()
        # 自动检测 GPU
        self._detect_device()
    
    def _detect_version(self):
        """检测 MinerU 版本"""
        if self.python_v3 and Path(self.python_v3).exists():
            self.python_exe = self.python_v3
            self.cli_path = self.mineru_cli_v3
            self.version = 3
            logger.info("使用 MinerU 3.x (支持公式识别)")
        elif self.python_v1 and Path(self.python_v1).exists():
            self.python_exe = self.python_v1
            self.cli_path = self.mineru_cli_v1
            self.version = 1
            logger.info("使用 MinerU 1.x (magic-pdf, 不支持公式识别)")
        elif self.mineru_cli_v3:
            self.python_exe = sys.executable
            self.cli_path = self.mineru_cli_v3
            self.version = 3
            logger.info("使用 PATH 中的 MinerU 3.x CLI")
        elif self.mineru_cli_v1:
            self.python_exe = sys.executable
            self.cli_path = self.mineru_cli_v1
            self.version = 1
            logger.info("使用 PATH 中的 MinerU 1.x (magic-pdf)")
        else:
            self.python_exe = None
            self.cli_path = None
            self.version = None
            logger.warning("未找到 MinerU 安装")
    
    def _detect_device(self):
        """自动检测并设置计算设备"""
        if self.device != 'auto':
            logger.info(f"设备模式: {self.device} (手动指定)")
            return
        
        # 尝试检测 CUDA
        try:
            import subprocess
            result = subprocess.run(
                [self.python_exe or 'python', '-c',
                 'import torch; print("cuda" if torch.cuda.is_available() else "cpu")'],
                capture_output=True, text=True, timeout=15,
                creationflags=SUBPROCESS_FLAGS
            )
            if result.returncode == 0 and result.stdout.strip():
                self.device = result.stdout.strip()
                logger.info(f"自动检测设备: {self.device}")
            else:
                self.device = 'cpu'
                stderr = result.stderr[:200] if result.stderr else ""
                logger.info(f"自动检测设备: cpu (torch 检测失败: rc={result.returncode}, stderr={stderr})")
        except Exception as e:
            self.device = 'cpu'
            logger.info(f"自动检测设备: cpu (异常: {e})")
    
    @staticmethod
    def detect_gpu(python_exe: str = None) -> dict:
        """
        静态方法：检测 GPU 可用性（供 GUI 调用）
        
        Args:
            python_exe: Python 解释器路径，默认使用 'python'
        
        Returns:
            dict: {
                'has_cuda': bool,
                'device_name': str or None,
                'cuda_version': str or None,
                'vram_mb': int or None,
                'error': str or None
            }
        """
        python_exe = python_exe or 'python'
        info = {
            'has_cuda': False,
            'device_name': None,
            'cuda_version': None,
            'vram_mb': None,
            'error': None
        }
        
        # 方案1: 通过 torch 检测（使用指定 Python 环境）
        try:
            import subprocess
            result = subprocess.run(
                [python_exe, '-c',
                 'import torch; '
                 'print(torch.cuda.is_available()); '
                 'print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else ""); '
                 'print(torch.version.cuda or ""); '
                  'print(int(torch.cuda.get_device_properties(0).total_memory / 1024 / 1024) if torch.cuda.is_available() else 0)'],
                capture_output=True, text=True, timeout=15,
                creationflags=SUBPROCESS_FLAGS
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 4 and lines[0].strip() == 'True':
                    info['has_cuda'] = True
                    info['device_name'] = lines[1].strip() or None
                    info['cuda_version'] = lines[2].strip() or None
                    try:
                        info['vram_mb'] = int(lines[3].strip()) or None
                    except ValueError:
                        pass
                    return info
                else:
                    info['error'] = f"torch.cuda.is_available()={lines[0].strip() if lines else 'unknown'}"
            else:
                info['error'] = f"torch 检测失败: rc={result.returncode}"
                if result.stderr:
                    info['error'] += f", stderr={result.stderr[:200]}"
        except Exception as e:
            info['error'] = f"torch 检测异常: {str(e)}"
        
        # 方案2: nvidia-smi 备选（确认硬件驱动正常）
        try:
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                capture_output=True, text=True, timeout=10,
                creationflags=SUBPROCESS_FLAGS
            )
            if result.returncode == 0 and result.stdout.strip():
                line = result.stdout.strip().split('\n')[0]
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 2:
                    info['device_name'] = parts[0]
                    mem_str = parts[1].replace('MiB', '').replace('MB', '').strip()
                    try:
                        info['vram_mb'] = int(mem_str)
                    except ValueError:
                        pass
                    info['error'] = (info['error'] or "") + "; nvidia-smi 正常，PyTorch 可能缺少 CUDA 支持"
        except Exception:
            pass
        
        return info
    
    def check_installation(self) -> bool:
        """检查MinerU是否正确安装"""
        if self.cli_path and Path(self.cli_path).exists():
            return True

        if self.python_exe and Path(self.python_exe).exists():
            module_name = 'mineru' if self.version == 3 else 'magic_pdf'
            try:
                result = subprocess.run(
                    [self.python_exe, '-c', f'import {module_name}'],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=SUBPROCESS_FLAGS
                )
                if result.returncode == 0:
                    return True
                logger.error(f"MinerU Python环境不可用: {result.stderr[:300] if result.stderr else result.returncode}")
            except Exception as exc:
                logger.error(f"MinerU Python环境检测失败: {exc}")
        
        # 检查PATH
        for cmd in ['mineru', 'magic-pdf']:
            try:
                result = subprocess.run(
                    [cmd, '--version'],
                    capture_output=True,
                    text=True,
                    creationflags=SUBPROCESS_FLAGS
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
        env['HF_ENDPOINT'] = self.config.get('hf_endpoint') or env.get('HF_ENDPOINT', 'https://hf-mirror.com')
        # 设置短路径缓存目录（解决 Windows 路径长度限制）
        hf_home = self.config.get('hf_home') or env.get('HF_HOME') or 'D:/CDriveMoved/hf_cache'
        hf_hub_cache = self.config.get('hf_hub_cache') or env.get('HF_HUB_CACHE') or str(Path(hf_home) / 'hub')
        xdg_cache_home = self.config.get('xdg_cache_home') or env.get('XDG_CACHE_HOME') or str(Path(hf_home).parent)
        env['HF_HOME'] = hf_home
        env['HF_HUB_CACHE'] = hf_hub_cache
        env['HUGGINGFACE_HUB_CACHE'] = hf_hub_cache
        env['XDG_CACHE_HOME'] = xdg_cache_home
        env['MINERU_MODEL_SOURCE'] = self.config.get('model_source') or env.get('MINERU_MODEL_SOURCE', 'huggingface')
        if self.config.get('mineru_tools_config_json'):
            env['MINERU_TOOLS_CONFIG_JSON'] = self.config['mineru_tools_config_json']
        
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
        
        if not self.check_installation() or self.version is None:
            return {
                'success': False,
                'error': 'MinerU未安装或未配置可用路径，请安装 mineru/magic-pdf 或在 config.yaml 中配置 Python/CLI 路径'
            }
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 设置环境变量
            env = self._setup_environment()
            
            # 构建命令
            if self.version == 3:
                cmd = self._build_v3_command(pdf_path, output_dir, **kwargs)
            elif self.version == 1:
                cmd = self._build_v1_command(pdf_path, output_dir, **kwargs)
            else:
                return {
                    'success': False,
                    'error': '未检测到可用的 MinerU 版本'
                }
            
            # 通过环境变量控制设备（MinerU CLI 不支持 --device 参数）
            if self.device == 'cpu':
                env['CUDA_VISIBLE_DEVICES'] = ''
            elif self.device == 'cuda':
                env['CUDA_VISIBLE_DEVICES'] = '0'
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            logger.info(f"工作目录: {os.getcwd()}")
            logger.info(f"MinerU版本: {self.version}")
            
            # MinerU 3.x 会启动临时 API 子进程；用 pipe 捕获输出时在 Windows 上可能卡住。
            # 将输出写入日志文件，失败时再读取日志尾部。
            log_path = output_dir / 'mineru_cli.log'
            with open(log_path, 'w', encoding='utf-8', errors='replace') as log_file:
                result = subprocess.run(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    env=env,
                    timeout=self.timeout,
                    creationflags=SUBPROCESS_FLAGS
                )
            
            try:
                log_text = log_path.read_text(encoding='utf-8', errors='replace')
            except Exception:
                log_text = ''
            
            logger.info(f"MinerU返回码: {result.returncode}")
            if log_text:
                logger.info(f"MinerU log: {log_text[-2000:]}")
            
            if result.returncode != 0:
                error_detail = log_text.strip()
                if not error_detail:
                    error_detail = f"MinerU返回非零退出码(rc={result.returncode})"
                logger.error(f"MinerU执行失败 (rc={result.returncode}): {error_detail[:1000]}")
                return {
                    'success': False,
                    'error': f"MinerU执行失败 (rc={result.returncode}): {error_detail[:600]}"
                }
            
            # 记录输出目录内容用于调试
            logger.info(f"MinerU执行完成，检查输出目录: {output_dir}")
            if output_dir.exists():
                all_files = list(output_dir.rglob('*'))[:20]
                for f in all_files:
                    logger.info(f"  输出文件: {f}")
            
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
        """构建 MinerU 3.x 命令（通过 python -m 调用，确保打包后环境正确）"""
        # 使用 python -m mineru.cli.client 而非直接调用 mineru.exe
        # 这样打包后的程序能通过显式指定的 python.exe 找到所有依赖
        cmd = [
            self.python_exe, '-m', 'mineru.cli.client',
            '-p', str(pdf_path),
            '-o', str(output_dir),
            '-b', self.backend,
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
