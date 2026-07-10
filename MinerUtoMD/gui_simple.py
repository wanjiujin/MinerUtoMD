"""
MinerUtoMD v1.1.0 - 简洁版 GUI
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import subprocess
import sys
import os
from datetime import datetime
import queue
import json

try:
    import yaml
except ImportError:
    yaml = None

# Windows 上隐藏子进程窗口
if sys.platform == 'win32':
    SUBPROCESS_FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
else:
    SUBPROCESS_FLAGS = 0

# 设置默认镜像地址；缓存目录由系统环境变量或 config.yaml 决定。
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

VERSION = "1.2.0"


class MinerUtoMDApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"MinerUtoMD v{VERSION}")
        self.root.geometry("900x700")
        
        # 状态变量
        self.is_running = False
        self.is_paused = False
        self.processed_files = set()
        self.log_queue = queue.Queue()
        
        self.base_config = self.load_config()
        # 检测环境（仅快速检测，不阻塞UI）
        self.python_exe = self.detect_python()
        self.pandoc_path = self.detect_pandoc()
        self.pdf_engine = self.detect_pdf_engine()
        self.apply_detected_paths()
        # 先使用默认值，异步检测完成后更新
        self.has_watermark = False
        self.gpu_info = {'has_cuda': False, 'device_name': None, 'vram_mb': None, 'error': None}
        
        self.setup_ui()
        self.process_log_queue()
        
        # 后台异步检测环境（不阻塞启动）
        self._start_async_env_check()
        
    def detect_python(self):
        """检测 MinerU Python 环境"""
        configured = (self.base_config or {}).get('mineru', {}).get('python_exe')
        paths = [
            configured,
            r"D:\CDriveMoved\miniforge3\envs\mineru2\python.exe",
            r"D:\CDriveMoved\miniforge3\envs\mineru\python.exe",
        ]
        for p in paths:
            if p and Path(p).exists():
                return p
        return sys.executable
    
    def detect_pandoc(self):
        """检测 Pandoc"""
        configured = (self.base_config or {}).get('pandoc', {}).get('path')
        paths = [
            configured,
            r"D:\CDriveMoved\miniforge3\envs\mineru2\Library\bin\pandoc.exe",
            r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\JohnMacFarlane.Pandoc_Microsoft.Winget.Source_8wekyb3d8bbwe\pandoc-3.9.0.2\pandoc.exe",
        ]
        for p in paths:
            if p and Path(p).exists():
                return p
            if p:
                import shutil
                found = shutil.which(str(p))
                if found:
                    return found
        return "pandoc"

    def detect_pdf_engine(self):
        """检测 Pandoc PDF 引擎"""
        configured = None
        try:
            configured = (self.base_config or {}).get('pandoc', {}).get('pdf_engine')
        except AttributeError:
            configured = None

        candidates = []
        if configured:
            candidates.append(str(configured))
        candidates.extend([
            r"D:\CDriveMoved\miniforge3\envs\mineru2\Library\bin\wkhtmltopdf.exe",
            "wkhtmltopdf",
        ])

        for candidate in candidates:
            if Path(candidate).exists():
                return candidate
            import shutil
            found = shutil.which(candidate)
            if found:
                return found
        return configured or "wkhtmltopdf"

    def app_dir(self):
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent

    def bundle_dir(self):
        if getattr(sys, 'frozen', False):
            return Path(sys._MEIPASS)
        return Path(__file__).resolve().parent

    def load_config(self):
        """加载随 exe 或源码提供的 config.yaml。"""
        if yaml is None:
            return {}

        candidates = [
            self.app_dir() / "config.yaml",
            self.bundle_dir() / "config.yaml",
            Path(__file__).resolve().parent / "config.yaml",
        ]
        for path in candidates:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
                except Exception:
                    return {}
        return {}

    def apply_detected_paths(self):
        mineru_cfg = self.base_config.setdefault('mineru', {})
        pandoc_cfg = self.base_config.setdefault('pandoc', {})
        if self.python_exe and not mineru_cfg.get('python_exe'):
            mineru_cfg['python_exe'] = self.python_exe
        if self.pandoc_path:
            pandoc_cfg['path'] = self.pandoc_path
        if self.pdf_engine:
            pandoc_cfg['pdf_engine'] = self.pdf_engine

        local_model_config = self.app_dir() / "mineru_local_models.json"
        if local_model_config.exists() and not mineru_cfg.get('mineru_tools_config_json'):
            mineru_cfg['mineru_tools_config_json'] = str(local_model_config)
            mineru_cfg['model_source'] = 'local'

        default_hf_home = Path(r"D:\CDriveMoved\hf_cache")
        if default_hf_home.exists() and not mineru_cfg.get('hf_home'):
            mineru_cfg['hf_home'] = str(default_hf_home)
        default_hf_hub = default_hf_home / "hub"
        if default_hf_hub.exists() and not mineru_cfg.get('hf_hub_cache'):
            mineru_cfg['hf_hub_cache'] = str(default_hf_hub)

        hf_home = mineru_cfg.get('hf_home')
        hf_hub_cache = mineru_cfg.get('hf_hub_cache')
        if hf_home:
            os.environ.setdefault('HF_HOME', str(hf_home))
        if hf_hub_cache:
            os.environ.setdefault('HF_HUB_CACHE', str(hf_hub_cache))
    
    def _start_async_env_check(self):
        """后台异步检测环境，不阻塞UI启动"""
        def check():
            # 检测水印依赖
            has_wm = self.check_watermark_deps()
            # 检测 GPU
            gpu = self.detect_gpu()
            # 在主线程更新UI
            self.root.after(0, lambda: self._update_env_state(has_wm, gpu))
        
        threading.Thread(target=check, daemon=True).start()
    
    def _update_env_state(self, has_watermark, gpu_info):
        """异步检测完成后更新UI状态"""
        self.has_watermark = has_watermark
        self.gpu_info = gpu_info
        
        # 更新水印复选框状态
        wm_text = "水印去除" if self.has_watermark else "水印去除 (需安装依赖)"
        wm_state = 'normal' if self.has_watermark else 'disabled'
        for widget in getattr(self, 'watermark_widgets', []):
            widget.config(state=wm_state)
        if hasattr(self, 'watermark_check'):
            self.watermark_check.config(text=wm_text)
        
        # 更新 GPU 单选按钮状态
        if self.gpu_info['has_cuda']:
            name = self.gpu_info.get('device_name', '')
            vram = self.gpu_info.get('vram_mb')
            vram_str = f" {vram}MB" if vram else ""
            gpu_text = f"GPU ({name}{vram_str})" if name else "GPU (CUDA)"
            self.gpu_radio.config(text=gpu_text, state='normal')
        else:
            self.gpu_radio.config(text="GPU (不可用)", state='disabled')
            # 如果当前选了GPU，自动切换到自动
            if self.device_var.get() == 'cuda':
                self.device_var.set('auto')
        
        # 在日志中显示检测结果
        if gpu_info.get('error'):
            self.log(f"GPU检测: {gpu_info['error']}")
        elif gpu_info['has_cuda']:
            name = gpu_info.get('device_name', '未知')
            vram = gpu_info.get('vram_mb', '?')
            self.log(f"GPU检测完成: {name} ({vram}MB)")
        else:
            self.log("GPU检测完成: 未检测到可用GPU")
        self.log(f"水印依赖: {'可用' if has_watermark else '不可用'}")

    def check_watermark_deps(self):
        """检测水印去除依赖"""
        try:
            result = subprocess.run(
                [self.python_exe, "-c", "import cv2, fitz"],
                capture_output=True,
                timeout=10,
                creationflags=SUBPROCESS_FLAGS
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def detect_gpu(self):
        """检测 GPU 可用性，使用多种方案"""
        info = {'has_cuda': False, 'device_name': None, 'vram_mb': None, 'error': None}
        
        # 方案1: 通过 torch 检测（最准确，能获取显存）
        try:
            r = subprocess.run(
                [self.python_exe, "-c",
                 "import torch; "
                 "print(torch.cuda.is_available()); "
                 "print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else ''); "
                  "print(int(torch.cuda.get_device_properties(0).total_memory/1024/1024) if torch.cuda.is_available() else 0); "
                 "print(torch.version.cuda or '')"],
                capture_output=True, text=True, timeout=15,
                creationflags=SUBPROCESS_FLAGS
            )
            if r.returncode == 0:
                lines = r.stdout.strip().split('\n')
                if len(lines) >= 3 and lines[0].strip() == 'True':
                    info['has_cuda'] = True
                    info['device_name'] = lines[1].strip() or None
                    try:
                        info['vram_mb'] = int(lines[2].strip()) or None
                    except ValueError:
                        pass
                    return info
                # torch 返回了结果但 cuda 不可用，记录原因
                info['error'] = f"torch.cuda.is_available()={lines[0].strip() if lines else 'unknown'}"
            else:
                info['error'] = f"torch 检测失败: rc={r.returncode}, stderr={r.stderr[:200]}"
        except Exception as e:
            info['error'] = f"torch 检测异常: {str(e)}"
        
        # 方案2: 通过 nvidia-smi 检测（备选，可确认驱动和硬件）
        try:
            r = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                capture_output=True, text=True, timeout=10,
                creationflags=SUBPROCESS_FLAGS
            )
            if r.returncode == 0 and r.stdout.strip():
                line = r.stdout.strip().split('\n')[0]
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 2:
                    info['device_name'] = parts[0]
                    # 解析显存如 "8192 MiB"
                    mem_str = parts[1].replace('MiB', '').replace('MB', '').strip()
                    try:
                        info['vram_mb'] = int(mem_str)
                    except ValueError:
                        pass
                    # nvidia-smi 能工作说明驱动和硬件正常，但 PyTorch 可能未编译 CUDA 支持
                    info['error'] = (info['error'] or "") + "; nvidia-smi 正常，PyTorch 可能缺少 CUDA 支持"
                    return info
        except Exception:
            pass
        
        return info
    
    def setup_ui(self):
        """设置界面"""
        # 主框架
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill='both', expand=True)
        
        # 标题
        ttk.Label(main, text=f"MinerUtoMD v{VERSION}", 
                 font=('Microsoft YaHei UI', 16, 'bold')).pack(anchor='w')
        ttk.Label(main, text="PDF/Word → Markdown → 多格式转换", 
                 font=('Microsoft YaHei UI', 10)).pack(anchor='w')
        
        ttk.Separator(main, orient='horizontal').pack(fill='x', pady=10)
        
        # 工作流选择
        wf_frame = ttk.LabelFrame(main, text="工作流", padding=5)
        wf_frame.pack(fill='x', pady=5)
        
        self.workflow_var = tk.StringVar(value="pdf")
        ttk.Radiobutton(wf_frame, text="PDF 工作流 (PDF → MD → Word/PDF/EPUB/HTML)", 
                       variable=self.workflow_var, value="pdf").pack(anchor='w')
        ttk.Radiobutton(wf_frame, text="Word 工作流 (Word → MD → 优化 → Word)", 
                       variable=self.workflow_var, value="word").pack(anchor='w')
        
        # 文件选择
        file_frame = ttk.LabelFrame(main, text="文件选择", padding=5)
        file_frame.pack(fill='x', pady=5)
        
        self.file_mode_var = tk.StringVar(value="batch")
        ttk.Radiobutton(file_frame, text="单个文件", variable=self.file_mode_var, 
                       value="single", command=self.on_mode_change).pack(side='left')
        ttk.Radiobutton(file_frame, text="批量处理", variable=self.file_mode_var, 
                       value="batch", command=self.on_mode_change).pack(side='left', padx=10)
        
        self.subfolder_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(file_frame, text="包含子文件夹", 
                       variable=self.subfolder_var).pack(side='left', padx=10)
        
        path_frame = ttk.Frame(file_frame)
        path_frame.pack(fill='x', pady=5)
        
        self.file_path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.file_path_var, width=60).pack(side='left', padx=5)
        ttk.Button(path_frame, text="浏览", command=self.browse_file).pack(side='left')
        
        self.file_count_var = tk.StringVar(value="")
        ttk.Label(file_frame, textvariable=self.file_count_var).pack(anchor='w')
        
        # 输出设置
        out_frame = ttk.LabelFrame(main, text="输出设置", padding=5)
        out_frame.pack(fill='x', pady=5)
        
        # 输出格式
        fmt_frame = ttk.Frame(out_frame)
        fmt_frame.pack(fill='x')
        ttk.Label(fmt_frame, text="输出格式:").pack(side='left')
        
        self.format_vars = {}
        for fmt in ['md', 'docx', 'pdf', 'epub', 'html']:
            var = tk.BooleanVar(value=(fmt == 'md'))
            self.format_vars[fmt] = var
            ttk.Checkbutton(fmt_frame, text=fmt.upper(), variable=var).pack(side='left', padx=5)
        
        # 输出目录
        dir_frame = ttk.Frame(out_frame)
        dir_frame.pack(fill='x', pady=5)
        ttk.Label(dir_frame, text="输出目录:").pack(side='left')
        self.output_dir_var = tk.StringVar(value=str(Path.cwd() / "output"))
        ttk.Entry(dir_frame, textvariable=self.output_dir_var, width=50).pack(side='left', padx=5)
        ttk.Button(dir_frame, text="选择", command=self.browse_output).pack(side='left')
        
        # PDF 选项
        pdf_frame = ttk.Frame(out_frame)
        pdf_frame.pack(fill='x', pady=5)
        
        # 设备选择 (GPU/CPU)
        device_frame = ttk.Frame(pdf_frame)
        device_frame.pack(side='left')
        
        ttk.Label(device_frame, text="设备:").pack(side='left')
        self.device_var = tk.StringVar(value="auto")
        
        auto_text = "自动"
        gpu_text = "GPU (CUDA)"
        cpu_text = "CPU"
        
        if self.gpu_info['has_cuda']:
            gpu_name = self.gpu_info.get('device_name', '')
            vram = self.gpu_info.get('vram_mb')
            vram_str = f" {vram}MB" if vram else ""
            gpu_text = f"GPU ({gpu_name}{vram_str})" if gpu_name else "GPU (CUDA)"
        else:
            gpu_text = "GPU (不可用)"
        
        self.auto_radio = ttk.Radiobutton(device_frame, text=auto_text, variable=self.device_var, 
                           value="auto")
        self.auto_radio.pack(side='left', padx=3)
        
        self.gpu_radio = ttk.Radiobutton(device_frame, text=gpu_text, variable=self.device_var, 
                           value="cuda", state='normal' if self.gpu_info['has_cuda'] else 'disabled')
        self.gpu_radio.pack(side='left', padx=3)
        
        self.cpu_radio = ttk.Radiobutton(device_frame, text=cpu_text, variable=self.device_var, 
                           value="cpu")
        self.cpu_radio.pack(side='left', padx=3)
        
        # 分隔
        ttk.Separator(pdf_frame, orient='vertical').pack(side='left', fill='y', padx=8)
        
        self.formula_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(pdf_frame, text="公式识别", variable=self.formula_var).pack(side='left')
        
        self.table_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(pdf_frame, text="表格识别", variable=self.table_var).pack(side='left', padx=10)
        
        self.watermark_var = tk.BooleanVar(value=False)
        wm_text = "水印去除" if self.has_watermark else "水印去除 (需安装依赖)"
        wm_state = 'normal' if self.has_watermark else 'disabled'
        self.watermark_check = ttk.Checkbutton(
            pdf_frame, text=wm_text, variable=self.watermark_var, state=wm_state
        )
        self.watermark_check.pack(side='left', padx=10)
        
        self.watermark_mode_var = tk.StringVar(value="fast")
        self.watermark_fast_radio = ttk.Radiobutton(
            pdf_frame, text="快速", variable=self.watermark_mode_var, value="fast", state=wm_state
        )
        self.watermark_fast_radio.pack(side='left')
        self.watermark_deep_radio = ttk.Radiobutton(
            pdf_frame, text="深度", variable=self.watermark_mode_var, value="deep", state=wm_state
        )
        self.watermark_deep_radio.pack(side='left')
        self.watermark_widgets = [
            self.watermark_check,
            self.watermark_fast_radio,
            self.watermark_deep_radio,
        ]

        # 高级选项
        adv_frame = ttk.Frame(out_frame)
        adv_frame.pack(fill='x', pady=5)

        ttk.Label(adv_frame, text="解析:").pack(side='left')
        mineru_cfg = self.base_config.get('mineru', {})
        self.parse_method_var = tk.StringVar(value=mineru_cfg.get('parse_method', 'auto'))
        self.parse_method_box = ttk.Combobox(
            adv_frame,
            textvariable=self.parse_method_var,
            values=['auto', 'txt', 'ocr'],
            width=6,
            state='readonly'
        )
        self.parse_method_box.pack(side='left', padx=3)

        ttk.Label(adv_frame, text="OCR语言:").pack(side='left', padx=(8, 0))
        self.ocr_lang_var = tk.StringVar(value=mineru_cfg.get('ocr_lang', 'ch'))
        ttk.Entry(adv_frame, textvariable=self.ocr_lang_var, width=8).pack(side='left', padx=3)

        ttk.Label(adv_frame, text="页码:").pack(side='left', padx=(8, 0))
        self.page_range_var = tk.StringVar(value="")
        ttk.Entry(adv_frame, textvariable=self.page_range_var, width=10).pack(side='left', padx=3)

        self.keep_intermediate_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(adv_frame, text="保留中间文件", variable=self.keep_intermediate_var).pack(side='left', padx=8)

        md_cfg = self.base_config.get('markdown_optimizer', {})
        self.optimize_tables_var = tk.BooleanVar(value=md_cfg.get('optimize_tables', True))
        ttk.Checkbutton(adv_frame, text="优化表格", variable=self.optimize_tables_var).pack(side='left')

        self.preserve_html_tables_var = tk.BooleanVar(
            value=md_cfg.get('table_output_mode') == 'preserve_html'
        )
        ttk.Checkbutton(
            adv_frame, text="保留HTML表格", variable=self.preserve_html_tables_var
        ).pack(side='left', padx=8)
        
        # 进度显示
        prog_frame = ttk.LabelFrame(main, text="处理进度", padding=5)
        prog_frame.pack(fill='both', expand=True, pady=5)
        
        self.progress_var = tk.DoubleVar()
        ttk.Progressbar(prog_frame, variable=self.progress_var, maximum=100).pack(fill='x', pady=5)
        
        self.log_text = tk.Text(prog_frame, height=10, font=('Consolas', 9))
        self.log_text.pack(fill='both', expand=True)
        
        # 按钮
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill='x', pady=10)
        
        self.start_btn = ttk.Button(btn_frame, text="开始转换", command=self.start_conversion)
        self.start_btn.pack(side='left', padx=5)
        
        self.pause_btn = ttk.Button(btn_frame, text="暂停", command=self.toggle_pause, state='disabled')
        self.pause_btn.pack(side='left', padx=5)
        
        ttk.Button(btn_frame, text="刷新", command=self.refresh_files).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="断点续传", command=self.resume_conversion).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="打开输出目录", command=self.open_output).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="检查环境", command=self.check_env).pack(side='left', padx=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self.root, textvariable=self.status_var, relief='sunken').pack(fill='x', side='bottom')
    
    def on_mode_change(self):
        self.file_count_var.set("")
    
    def browse_file(self):
        if self.file_mode_var.get() == "single":
            ext = "*.pdf" if self.workflow_var.get() == "pdf" else "*.docx"
            f = filedialog.askopenfilename(filetypes=[("文件", ext)])
            if f:
                self.file_path_var.set(f)
        else:
            d = filedialog.askdirectory()
            if d:
                self.file_path_var.set(d)
                self.refresh_files()
    
    def browse_output(self):
        d = filedialog.askdirectory()
        if d:
            self.output_dir_var.set(d)
    
    def refresh_files(self):
        path = self.file_path_var.get()
        if not path or self.file_mode_var.get() != "batch":
            return
        
        path = Path(path)
        if not path.exists():
            return
        
        ext = "*.pdf" if self.workflow_var.get() == "pdf" else "*.docx"
        if self.subfolder_var.get():
            files = list(path.rglob(ext)) + list(path.rglob(ext.upper()))
        else:
            files = list(path.glob(ext)) + list(path.glob(ext.upper()))
        
        # 去重（Windows不区分大小写，但保留原始路径大小写）
        seen = set()
        unique_files = []
        for f in files:
            key = str(f).lower()
            if key not in seen:
                seen.add(key)
                unique_files.append(f)
        files = unique_files
        
        self.file_count_var.set(f"找到 {len(files)} 个文件")
        self.log(f"扫描完成: {len(files)} 个文件")
    
    def toggle_pause(self):
        if not self.is_running:
            return
        self.is_paused = not self.is_paused
        self.pause_btn.config(text="继续" if self.is_paused else "暂停")
        self.status_var.set("已暂停" if self.is_paused else "处理中...")
        self.log("已暂停" if self.is_paused else "继续处理...")
    
    def resume_conversion(self):
        if self.is_running:
            messagebox.showwarning("提示", "当前有任务正在运行")
            return
        
        output_dir = Path(self.output_dir_var.get())
        if not output_dir.exists():
            messagebox.showwarning("提示", "输出目录不存在")
            return
        
        # 扫描已处理文件
        self.processed_files = set()
        for item in output_dir.iterdir():
            if item.is_dir():
                for ext in ['*.md', '*.docx']:
                    if list(item.glob(ext)):
                        self.processed_files.add(item.name.lower())
                        break
        
        self.log(f"找到 {len(self.processed_files)} 个已处理文件")
        self.start_conversion(resume=True)
    
    def open_output(self):
        d = Path(self.output_dir_var.get())
        if d.exists():
            os.startfile(str(d))
        else:
            messagebox.showinfo("提示", "输出目录不存在")
    
    def check_env(self):
        self.log_text.delete(1.0, tk.END)
        self.log("检查环境...")
        
        # Python
        self.log(f"Python: {self.python_exe}")
        
        # Pandoc
        try:
            r = subprocess.run([self.pandoc_path, "--version"], capture_output=True, text=True,
                              creationflags=SUBPROCESS_FLAGS)
            self.log(f"Pandoc: {r.stdout.split()[0] if r.returncode == 0 else '未找到'}")
            self.log(f"  路径: {self.pandoc_path}")
        except Exception as e:
            self.log(f"Pandoc: 未找到 ({e})")
        
        # MinerU
        try:
            r = subprocess.run([self.python_exe, "-c", "import mineru; print('ok')"], 
                              capture_output=True, text=True, timeout=10,
                              creationflags=SUBPROCESS_FLAGS)
            self.log(f"MinerU: {'已安装' if 'ok' in r.stdout else '未找到'}")
        except Exception as e:
            self.log(f"MinerU: 未找到 ({e})")
        
        # GPU - 直接重新检测，显示详细结果
        self.log("GPU: 正在检测...")
        self.root.update()  # 刷新UI
        gpu_info = self.detect_gpu()
        if gpu_info['has_cuda']:
            name = gpu_info.get('device_name', '未知')
            vram = gpu_info.get('vram_mb')
            vram_str = f", {vram}MB" if vram else ""
            self.log(f"GPU: {name}{vram_str}")
        else:
            error = gpu_info.get('error')
            if error:
                if 'nvidia-smi' in error:
                    # nvidia-smi 能工作但 PyTorch 缺少 CUDA 支持
                    name = gpu_info.get('device_name', '未知')
                    vram = gpu_info.get('vram_mb')
                    vram_str = f" {vram}MB" if vram else ""
                    self.log(f"GPU: {name}{vram_str} (驱动正常，但PyTorch未启用CUDA)")
                    self.log(f"  原因: {error}")
                else:
                    self.log(f"GPU: 不可用")
                    self.log(f"  原因: {error}")
            else:
                self.log(f"GPU: 不可用 (将使用CPU模式)")
                self.log(f"  原因: torch.cuda.is_available()=False，请确认已安装CUDA版PyTorch")
        
        # 水印依赖 - 直接重新检测，显示详细结果
        self.log("水印依赖: 正在检测...")
        self.root.update()  # 刷新UI
        
        # 分别检测 cv2 和 fitz
        cv2_ok = False
        fitz_ok = False
        cv2_err = ""
        fitz_err = ""
        
        try:
            r = subprocess.run([self.python_exe, "-c", "import cv2; print(cv2.__version__)"], 
                              capture_output=True, text=True, timeout=5,
                              creationflags=SUBPROCESS_FLAGS)
            if r.returncode == 0:
                cv2_ok = True
                self.log(f"  OpenCV: {r.stdout.strip()} ✓")
            else:
                cv2_err = r.stderr[:100] if r.stderr else "导入失败"
                self.log(f"  OpenCV: ✗ ({cv2_err})")
        except Exception as e:
            cv2_err = str(e)[:100]
            self.log(f"  OpenCV: ✗ ({cv2_err})")
        
        try:
            r = subprocess.run([self.python_exe, "-c", "import fitz; print('ok')"], 
                              capture_output=True, text=True, timeout=5,
                              creationflags=SUBPROCESS_FLAGS)
            if r.returncode == 0 and 'ok' in r.stdout:
                fitz_ok = True
                self.log(f"  PyMuPDF: 已安装 ✓")
            else:
                fitz_err = r.stderr[:100] if r.stderr else "导入失败"
                self.log(f"  PyMuPDF: ✗ ({fitz_err})")
        except Exception as e:
            fitz_err = str(e)[:100]
            self.log(f"  PyMuPDF: ✗ ({fitz_err})")
        
        if cv2_ok and fitz_ok:
            self.log("水印去除: 可用 ✓")
            self.has_watermark = True
        else:
            missing = []
            if not cv2_ok: missing.append("opencv-python")
            if not fitz_ok: missing.append("pymupdf")
            self.log(f"水印去除: 需安装 {' 和 '.join(missing)}")
            self.log(f"  安装命令: {self.python_exe} -m pip install {' '.join(missing)}")
            self.has_watermark = False
        
        # 更新UI状态
        self._update_env_state(self.has_watermark, gpu_info)
        
        self.log("环境检查完成")
        self.log("环境检查完成")
    
    def log(self, message):
        """添加日志到队列"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_queue.put(f"[{timestamp}] {message}\n")
    
    def process_log_queue(self):
        """处理日志队列"""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, msg)
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.process_log_queue)
    
    def start_conversion(self, resume=False):
        if self.is_running:
            return
        
        file_path = self.file_path_var.get()
        if not file_path:
            messagebox.showwarning("警告", "请选择文件或目录")
            return
        
        formats = [f for f, v in self.format_vars.items() if v.get()]
        if not formats:
            messagebox.showwarning("警告", "请至少选择一种输出格式")
            return
        
        if not resume:
            self.log_text.delete(1.0, tk.END)
            self.processed_files = set()
        
        self.progress_var.set(0)
        self.is_running = True
        self.is_paused = False
        self.pause_btn.config(text="暂停", state='normal')
        self.start_btn.config(state='disabled')
        self.status_var.set("处理中...")
        
        # 启动线程
        thread = threading.Thread(target=self.run_conversion, args=(file_path, formats, resume))
        thread.daemon = True
        thread.start()
    
    def run_conversion(self, file_path, formats, resume=False):
        """执行转换"""
        try:
            self.log("开始处理...")
            self.log(f"输入: {file_path}")
            self.log(f"输出: {self.output_dir_var.get()}")
            self.log(f"格式: {', '.join(formats)}")
            
            workflow_type = self.workflow_var.get()
            mode = self.file_mode_var.get()
            output_dir = self.output_dir_var.get()
            
            # 加载配置
            config = json.loads(json.dumps(self.base_config))
            config.setdefault('mineru', {})
            config.setdefault('pandoc', {})
            config.setdefault('watermark_remover', {})
            config.setdefault('markdown_optimizer', {})

            config['mineru'].update({
                'enable_formula': self.formula_var.get(),
                'enable_table': self.table_var.get(),
                'device': self.device_var.get(),
                'parse_method': self.parse_method_var.get(),
                'ocr_lang': self.ocr_lang_var.get().strip() or 'ch',
            })
            config['pandoc']['path'] = self.pandoc_path
            config['watermark_remover']['mode'] = self.watermark_mode_var.get()
            config['markdown_optimizer']['optimize_tables'] = self.optimize_tables_var.get()
            config['markdown_optimizer']['table_output_mode'] = (
                'preserve_html' if self.preserve_html_tables_var.get() else 'markdown'
            )
            
            # 导入工作流
            self.log("导入工作流模块...")
            import sys
            if getattr(sys, 'frozen', False):
                # 打包后的路径
                bundle_dir = Path(sys._MEIPASS)
                sys.path.insert(0, str(bundle_dir))
            
            from doc_workflow import PDFWorkflow, WordWorkflow
            self.PDFWorkflow = PDFWorkflow
            self.WordWorkflow = WordWorkflow
            self.log("工作流模块导入成功")
            
            if mode == "batch" and workflow_type == "pdf":
                self.run_batch_pdf(file_path, formats, output_dir, config, resume)
            elif mode == "batch" and workflow_type == "word":
                self.run_batch_word(file_path, formats, output_dir, config, resume)
            elif mode == "single" and workflow_type == "pdf":
                self.run_single_pdf(file_path, formats, output_dir, config)
            elif mode == "single" and workflow_type == "word":
                self.run_word(file_path, formats, output_dir, config)
            
        except Exception as e:
            import traceback
            self.log(f"错误: {e}")
            self.log(traceback.format_exc())
        finally:
            self.is_running = False
            self.is_paused = False
            self.root.after(0, lambda: self.start_btn.config(state='normal'))
            self.root.after(0, lambda: self.pause_btn.config(state='disabled'))
            self.root.after(0, lambda: self.status_var.set("就绪"))
            self.log("处理完成")

    def parse_page_range(self):
        text = self.page_range_var.get().strip()
        if not text:
            return {}

        try:
            if '-' in text:
                start_text, end_text = text.split('-', 1)
                start = max(int(start_text.strip()) - 1, 0)
                end = max(int(end_text.strip()) - 1, start)
            else:
                start = max(int(text) - 1, 0)
                end = start
            return {'start_page': start, 'end_page': end}
        except ValueError:
            self.log(f"页码范围无效，已忽略: {text}")
            return {}

    def workflow_options(self):
        options = {
            'enable_formula': self.formula_var.get(),
            'enable_table': self.table_var.get(),
            'remove_watermark': self.watermark_var.get(),
            'keep_intermediate': self.keep_intermediate_var.get(),
        }
        options.update(self.parse_page_range())
        return options

    def log_quality_report(self, result):
        quality = result.get('quality') or {}
        report_path = quality.get('report_path')
        if report_path:
            self.log(f"  质量报告: {report_path}")
    
    def run_batch_pdf(self, file_path, formats, output_dir, config, resume):
        """批量处理 PDF"""
        input_path = Path(file_path)
        if not input_path.exists():
            self.log("错误: 输入目录不存在")
            return
        
        # 扫描文件
        if self.subfolder_var.get():
            pdf_files = list(input_path.rglob('*.pdf')) + list(input_path.rglob('*.PDF'))
        else:
            pdf_files = list(input_path.glob('*.pdf')) + list(input_path.glob('*.PDF'))
        
        # 去重（Windows不区分大小写，但保留原始路径大小写）
        seen = set()
        unique_files = []
        for f in pdf_files:
            key = str(f).lower()
            if key not in seen:
                seen.add(key)
                unique_files.append(f)
        pdf_files = unique_files
        
        # 断点续传
        if resume and self.processed_files:
            pdf_files = [f for f in pdf_files if f.stem.lower() not in self.processed_files]
        
        total = len(pdf_files)
        self.log(f"共 {total} 个文件待处理")
        
        if not pdf_files:
            self.log("没有需要处理的文件")
            return
        
        workflow = self.PDFWorkflow(config)
        success = 0
        failed = 0
        start_time = datetime.now()
        
        for i, pdf in enumerate(pdf_files, 1):
            # 检查暂停
            while self.is_paused:
                import time
                time.sleep(0.1)
            
            if not self.is_running:
                self.log("处理已中断")
                break
            
            self.log(f"[{i}/{total}] {pdf.name}")
            
            # 更新进度
            progress = (i / total) * 100
            self.root.after(0, lambda p=progress: self.progress_var.set(p))
            
            # 处理文件
            file_out = Path(output_dir)
            file_out.mkdir(parents=True, exist_ok=True)
            
            file_start = datetime.now()
            try:
                result = workflow.run(
                    str(pdf), str(file_out), formats,
                    **self.workflow_options()
                )
                
                elapsed = (datetime.now() - file_start).total_seconds()
                if result.get('success'):
                    success += 1
                    self.processed_files.add(pdf.stem.lower())
                    self.log(f"  成功 ({elapsed:.1f}秒)")
                    self.log_quality_report(result)
                else:
                    failed += 1
                    self.log(f"  失败: {result.get('errors', ['未知错误'])[0][:100]}")
            except Exception as e:
                failed += 1
                self.log(f"  异常: {str(e)[:100]}")
            
            # 更新状态
            elapsed_total = (datetime.now() - start_time).total_seconds()
            avg = elapsed_total / i
            remaining = avg * (total - i)
            self.root.after(0, lambda e=elapsed_total, r=remaining: 
                           self.status_var.set(f"处理中... 已用时 {e:.0f}秒, 预计剩余 {r:.0f}秒"))
        
        # 完成
        total_time = (datetime.now() - start_time).total_seconds()
        self.root.after(0, lambda: self.progress_var.set(100))
        self.log(f"完成! 成功: {success}, 失败: {failed}, 耗时: {total_time:.1f}秒")
        self.root.after(0, lambda: messagebox.showinfo("完成", 
                       f"处理完成!\n成功: {success}\n失败: {failed}\n耗时: {total_time:.1f}秒"))
    
    def run_single_pdf(self, file_path, formats, output_dir, config):
        """单文件 PDF 处理"""
        workflow = self.PDFWorkflow(config)
        result = workflow.run(
            file_path, output_dir, formats,
            **self.workflow_options()
        )
        
        if result.get('success'):
            self.root.after(0, lambda: self.progress_var.set(100))
            self.log("转换成功!")
            for fmt, path in result.get('outputs', {}).items():
                self.log(f"  {fmt.upper()}: {path}")
            self.log_quality_report(result)
            self.root.after(0, lambda: messagebox.showinfo("成功", "转换完成!"))
        else:
            self.log("转换失败!")
            for err in result.get('errors', []):
                self.log(f"  错误: {err}")
            self.root.after(0, lambda: messagebox.showerror("错误", "转换失败, 请查看日志"))
    
    def run_word(self, file_path, formats, output_dir, config):
        """Word 工作流（单文件）"""
        workflow = self.WordWorkflow(config)
        result = workflow.run(file_path, output_dir, output_formats=formats)
        
        if result.get('success'):
            self.root.after(0, lambda: self.progress_var.set(100))
            self.log("转换成功!")
            self.log_quality_report(result)
            self.root.after(0, lambda: messagebox.showinfo("成功", "转换完成!"))
        else:
            self.log("转换失败!")
            self.root.after(0, lambda: messagebox.showerror("错误", "转换失败"))
    
    def run_batch_word(self, file_path, formats, output_dir, config, resume):
        """批量处理 Word"""
        input_path = Path(file_path)
        if not input_path.exists():
            self.log("错误: 输入目录不存在")
            return
        
        # 扫描文件
        if self.subfolder_var.get():
            docx_files = (
                list(input_path.rglob('*.docx')) + list(input_path.rglob('*.DOCX')) +
                list(input_path.rglob('*.doc')) + list(input_path.rglob('*.DOC'))
            )
        else:
            docx_files = (
                list(input_path.glob('*.docx')) + list(input_path.glob('*.DOCX')) +
                list(input_path.glob('*.doc')) + list(input_path.glob('*.DOC'))
            )
        
        # 去重（Windows不区分大小写，但保留原始路径大小写）
        seen = set()
        unique_files = []
        for f in docx_files:
            key = str(f).lower()
            if key not in seen:
                seen.add(key)
                unique_files.append(f)
        docx_files = unique_files
        
        # 断点续传
        if resume and self.processed_files:
            docx_files = [f for f in docx_files if f.stem.lower() not in self.processed_files]
        
        total = len(docx_files)
        self.log(f"共 {total} 个Word文件待处理")
        
        if not docx_files:
            self.log("没有需要处理的文件")
            return
        
        workflow = self.WordWorkflow(config)
        success = 0
        failed = 0
        start_time = datetime.now()
        
        for i, docx in enumerate(docx_files, 1):
            # 检查暂停
            while self.is_paused:
                import time
                time.sleep(0.1)
            
            if not self.is_running:
                self.log("处理已中断")
                break
            
            self.log(f"[{i}/{total}] {docx.name}")
            
            # 更新进度
            progress = (i / total) * 100
            self.root.after(0, lambda p=progress: self.progress_var.set(p))
            
            # 处理文件
            file_out = Path(output_dir)
            file_out.mkdir(parents=True, exist_ok=True)
            
            file_start = datetime.now()
            try:
                result = workflow.run(str(docx), str(file_out), output_formats=formats)
                
                elapsed = (datetime.now() - file_start).total_seconds()
                if result.get('success'):
                    success += 1
                    self.processed_files.add(docx.stem.lower())
                    self.log(f"  成功 ({elapsed:.1f}秒)")
                    self.log_quality_report(result)
                else:
                    failed += 1
                    self.log(f"  失败: {result.get('errors', ['未知错误'])[0][:100]}")
            except Exception as e:
                failed += 1
                self.log(f"  异常: {str(e)[:100]}")
            
            # 更新状态
            elapsed_total = (datetime.now() - start_time).total_seconds()
            avg = elapsed_total / i
            remaining = avg * (total - i)
            self.root.after(0, lambda e=elapsed_total, r=remaining:
                           self.status_var.set(f"处理中... 已用时 {e:.0f}秒, 预计剩余 {r:.0f}秒"))
        
        # 完成
        total_time = (datetime.now() - start_time).total_seconds()
        self.root.after(0, lambda: self.progress_var.set(100))
        self.log(f"完成! 成功: {success}, 失败: {failed}, 耗时: {total_time:.1f}秒")
        self.root.after(0, lambda: messagebox.showinfo("完成",
                       f"处理完成!\n成功: {success}\n失败: {failed}\n耗时: {total_time:.1f}秒"))
    
    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = MinerUtoMDApp()
    app.run()
