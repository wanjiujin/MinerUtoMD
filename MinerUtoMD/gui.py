"""
MinerUtoMD GUI - 现代化图形界面
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import subprocess
import sys
import os
from datetime import datetime
import logging

# Windows 上隐藏子进程窗口
if sys.platform == 'win32':
    SUBPROCESS_FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
else:
    SUBPROCESS_FLAGS = 0


# 设置环境变量（解决 HuggingFace 访问和 Windows 路径长度问题）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HOME'] = 'D:/CDriveMoved/hf_cache'

# 样式配置
COLORS = {
    'bg_primary': '#1a1a2e',
    'bg_secondary': '#16213e',
    'bg_card': '#0f3460',
    'accent': '#e94560',
    'accent_hover': '#ff6b6b',
    'text_primary': '#ffffff',
    'text_secondary': '#a0a0a0',
    'success': '#00d26a',
    'warning': '#ffc107',
    'error': '#ff4757',
}

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModernButton(tk.Canvas):
    """现代化按钮"""
    def __init__(self, parent, text, command=None, width=200, height=45, 
                 bg_color=None, text_color=None, corner_radius=10):
        super().__init__(parent, width=width, height=height, 
                        bg=COLORS['bg_primary'], highlightthickness=0)
        
        self.command = command
        self.corner_radius = corner_radius
        self.bg_color = bg_color or COLORS['accent']
        self.text_color = text_color or COLORS['text_primary']
        self.width = width
        self.height = height
        
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.bind('<Button-1>', self.on_click)
        
        self.draw_button(text)
    
    def draw_button(self, text):
        self.delete('all')
        # 绘制圆角矩形
        self.create_rounded_rect(2, 2, self.width-2, self.height-2, 
                                  self.corner_radius, fill=self.bg_color)
        # 绘制文字
        self.create_text(self.width//2, self.height//2, text=text,
                        fill=self.text_color, font=('Microsoft YaHei UI', 11, 'bold'))
    
    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1+radius, y1, x2-radius, y1,
            x2, y1, x2, y1+radius,
            x2, y2-radius, x2, y2,
            x2-radius, y2, x1+radius, y2,
            x1, y2, x1, y2-radius,
            x1, y1+radius, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def on_enter(self, event):
        self.config(cursor='hand2')
    
    def on_leave(self, event):
        self.config(cursor='')
    
    def on_click(self, event):
        if self.command:
            self.command()


class CardFrame(tk.Frame):
    """卡片式容器"""
    def __init__(self, parent, title="", **kwargs):
        super().__init__(parent, bg=COLORS['bg_card'], **kwargs)
        
        if title:
            title_label = tk.Label(self, text=title, 
                                   font=('Microsoft YaHei UI', 12, 'bold'),
                                   bg=COLORS['bg_card'], fg=COLORS['text_primary'])
            title_label.pack(pady=(15, 10), padx=20, anchor='w')


class MinerUtoMDGUI:
    VERSION = "1.1.0"
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"MinerUtoMD v{self.VERSION} - 文档转换工具")
        self.root.geometry("900x700")
        self.root.configure(bg=COLORS['bg_primary'])
        self.root.resizable(True, True)
        
        # 设置窗口图标（如果存在）
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
        
        # 检测环境
        self.python_exe = self.detect_python_exe()
        self.pandoc_path = self.detect_pandoc()
        self.has_watermark_deps = self.check_watermark_dependencies()
        self.gpu_info = self.detect_gpu()
        
        self.setup_ui()
        self.center_window()
        
    def detect_python_exe(self):
        """检测 Python 可执行文件"""
        # 优先使用新版 MinerU 环境 (支持公式识别)
        mineru2_python = r"D:\CDriveMoved\miniforge3\envs\mineru2\python.exe"
        if Path(mineru2_python).exists():
            return mineru2_python
        
        # 旧版环境
        conda_python = r"D:\CDriveMoved\miniforge3\envs\mineru\python.exe"
        if Path(conda_python).exists():
            return conda_python
        
        # 使用系统 Python
        return sys.executable
    
    def detect_pandoc(self):
        """检测 Pandoc 路径"""
        pandoc_path = r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\JohnMacFarlane.Pandoc_Microsoft.Winget.Source_8wekyb3d8bbwe\pandoc-3.9.0.2\pandoc.exe"
        if Path(pandoc_path).exists():
            return pandoc_path
        return "pandoc"
    
    def check_watermark_dependencies(self):
        """检测水印去除所需的依赖"""
        deps = {'cv2': False, 'fitz': False}
        
        try:
            import cv2
            deps['cv2'] = True
        except ImportError:
            pass
        
        try:
            import fitz  # PyMuPDF
            deps['fitz'] = True
        except ImportError:
            pass
        
        return deps['cv2'] and deps['fitz']
    
    def detect_gpu(self):
        """检测 GPU 可用性，使用多种方案"""
        info = {'has_cuda': False, 'device_name': None, 'vram_mb': None, 'error': None}
        
        # 方案1: 通过 torch 检测（使用 mineru2 环境）
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
                info['error'] = f"torch.cuda.is_available()={lines[0].strip() if lines else 'unknown'}"
            else:
                info['error'] = f"torch 检测失败: rc={r.returncode}"
                if r.stderr:
                    info['error'] += f", stderr={r.stderr[:200]}"
        except Exception as e:
            info['error'] = f"torch 检测异常: {str(e)}"
        
        # 方案2: nvidia-smi 备选
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
                    mem_str = parts[1].replace('MiB', '').replace('MB', '').strip()
                    try:
                        info['vram_mb'] = int(mem_str)
                    except ValueError:
                        pass
                    info['error'] = (info['error'] or "") + "; nvidia-smi 正常，PyTorch 可能缺少 CUDA 支持"
        except Exception:
            pass
        
        return info
    
    def setup_ui(self):
        """设置界面"""
        # 主容器
        main_container = tk.Frame(self.root, bg=COLORS['bg_primary'])
        main_container.pack(fill='both', expand=True, padx=30, pady=20)
        
        # 标题区域
        self.setup_header(main_container)
        
        # 工作流选择
        self.setup_workflow_selector(main_container)
        
        # 文件选择区域
        self.setup_file_selector(main_container)
        
        # 输出设置区域
        self.setup_output_settings(main_container)
        
        # 进度显示区域
        self.setup_progress_area(main_container)
        
        # 底部按钮
        self.setup_bottom_buttons(main_container)
        
        # 状态栏
        self.setup_status_bar()
    
    def setup_header(self, parent):
        """设置标题区域"""
        header_frame = tk.Frame(parent, bg=COLORS['bg_primary'])
        header_frame.pack(fill='x', pady=(0, 20))
        
        # 标题
        title = tk.Label(header_frame, text="MinerUtoMD",
                        font=('Microsoft YaHei UI', 28, 'bold'),
                        bg=COLORS['bg_primary'], fg=COLORS['text_primary'])
        title.pack(anchor='w')
        
        # 副标题
        subtitle = tk.Label(header_frame, 
                           text="智能文档转换工具 - PDF/Word → Markdown → 多格式",
                           font=('Microsoft YaHei UI', 11),
                           bg=COLORS['bg_primary'], fg=COLORS['text_secondary'])
        subtitle.pack(anchor='w', pady=(5, 0))
    
    def setup_workflow_selector(self, parent):
        """设置工作流选择"""
        workflow_frame = CardFrame(parent, title="选择工作流")
        workflow_frame.pack(fill='x', pady=(0, 15))
        
        # 工作流选项
        options_frame = tk.Frame(workflow_frame, bg=COLORS['bg_card'])
        options_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        self.workflow_var = tk.StringVar(value="pdf")
        
        # PDF 工作流
        pdf_frame = tk.Frame(options_frame, bg=COLORS['bg_card'])
        pdf_frame.pack(side='left', padx=(0, 20))
        
        pdf_rb = tk.Radiobutton(pdf_frame, text="📄 PDF 工作流",
                               variable=self.workflow_var, value="pdf",
                               font=('Microsoft YaHei UI', 11),
                               bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                               selectcolor=COLORS['bg_secondary'],
                               activebackground=COLORS['bg_card'])
        pdf_rb.pack(side='left')
        
        pdf_desc = tk.Label(pdf_frame, text="PDF → Markdown → Word/PDF/EPUB/HTML",
                           font=('Microsoft YaHei UI', 9),
                           bg=COLORS['bg_card'], fg=COLORS['text_secondary'])
        pdf_desc.pack(side='left', padx=(10, 0))
        
        # Word 工作流
        word_frame = tk.Frame(options_frame, bg=COLORS['bg_card'])
        word_frame.pack(side='left')
        
        word_rb = tk.Radiobutton(word_frame, text="📝 Word 工作流",
                                variable=self.workflow_var, value="word",
                                font=('Microsoft YaHei UI', 11),
                                bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                                selectcolor=COLORS['bg_secondary'],
                                activebackground=COLORS['bg_card'])
        word_rb.pack(side='left')
        
        word_desc = tk.Label(word_frame, text="Word → Markdown → 优化 → Word",
                            font=('Microsoft YaHei UI', 9),
                            bg=COLORS['bg_card'], fg=COLORS['text_secondary'])
        word_desc.pack(side='left', padx=(10, 0))
    
    def setup_file_selector(self, parent):
        """设置文件选择区域"""
        file_frame = CardFrame(parent, title="选择文件")
        file_frame.pack(fill='x', pady=(0, 15))
        
        # 单文件模式
        single_frame = tk.Frame(file_frame, bg=COLORS['bg_card'])
        single_frame.pack(fill='x', padx=20, pady=10)
        
        self.file_mode_var = tk.StringVar(value="single")
        
        single_rb = tk.Radiobutton(single_frame, text="单个文件",
                                  variable=self.file_mode_var, value="single",
                                  font=('Microsoft YaHei UI', 10),
                                  bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                                  selectcolor=COLORS['bg_secondary'],
                                  command=self.toggle_file_mode)
        single_rb.pack(side='left')
        
        batch_rb = tk.Radiobutton(single_frame, text="批量处理",
                                  variable=self.file_mode_var, value="batch",
                                  font=('Microsoft YaHei UI', 10),
                                  bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                                  selectcolor=COLORS['bg_secondary'],
                                  command=self.toggle_file_mode)
        batch_rb.pack(side='left', padx=(20, 0))
        
        # 子文件夹选项（批量模式）
        self.subfolder_var = tk.BooleanVar(value=False)
        self.subfolder_cb = tk.Checkbutton(single_frame, 
                                    text="包含子文件夹",
                                    variable=self.subfolder_var,
                                    font=('Microsoft YaHei UI', 10),
                                    bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                                    selectcolor=COLORS['bg_secondary'],
                                    activebackground=COLORS['bg_card'])
        self.subfolder_cb.pack(side='left', padx=(20, 0))
        
        # 文件路径输入
        path_frame = tk.Frame(file_frame, bg=COLORS['bg_card'])
        path_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        self.file_path_var = tk.StringVar()
        self.file_entry = tk.Entry(path_frame, textvariable=self.file_path_var,
                                   font=('Microsoft YaHei UI', 10),
                                   bg=COLORS['bg_secondary'], fg=COLORS['text_primary'],
                                   insertbackground=COLORS['text_primary'],
                                   relief='flat')
        self.file_entry.pack(side='left', fill='x', expand=True, padx=(0, 10), ipady=5)
        
        self.browse_btn = ModernButton(path_frame, "浏览", 
                                       command=self.browse_file,
                                       width=100, height=35,
                                       bg_color=COLORS['bg_secondary'])
        self.browse_btn.pack(side='right')
        
        # 文件统计显示
        self.file_count_var = tk.StringVar(value="")
        file_count_label = tk.Label(file_frame, textvariable=self.file_count_var,
                                   font=('Microsoft YaHei UI', 10),
                                   bg=COLORS['bg_card'], fg=COLORS['text_secondary'])
        file_count_label.pack(fill='x', padx=20, pady=(0, 10))
    
    def setup_output_settings(self, parent):
        """设置输出选项"""
        output_frame = CardFrame(parent, title="输出设置")
        output_frame.pack(fill='x', pady=(0, 15))
        
        # 格式选择
        format_frame = tk.Frame(output_frame, bg=COLORS['bg_card'])
        format_frame.pack(fill='x', padx=20, pady=10)
        
        format_label = tk.Label(format_frame, text="输出格式：",
                               font=('Microsoft YaHei UI', 10),
                               bg=COLORS['bg_card'], fg=COLORS['text_primary'])
        format_label.pack(side='left')
        
        self.format_vars = {}
        formats = [('md', 'Markdown'), ('docx', 'Word'), ('pdf', 'PDF'), 
                   ('epub', 'EPUB'), ('html', 'HTML')]
        
        for fmt, label in formats:
            var = tk.BooleanVar(value=(fmt == 'md'))
            self.format_vars[fmt] = var
            
            cb = tk.Checkbutton(format_frame, text=label,
                               variable=var,
                               font=('Microsoft YaHei UI', 10),
                               bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                               selectcolor=COLORS['bg_secondary'],
                               activebackground=COLORS['bg_card'])
            cb.pack(side='left', padx=(15, 0))
        
        # 输出目录
        output_dir_frame = tk.Frame(output_frame, bg=COLORS['bg_card'])
        output_dir_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        output_label = tk.Label(output_dir_frame, text="输出目录：",
                               font=('Microsoft YaHei UI', 10),
                               bg=COLORS['bg_card'], fg=COLORS['text_primary'])
        output_label.pack(side='left')
        
        self.output_dir_var = tk.StringVar(value=str(Path.cwd() / "output"))
        output_entry = tk.Entry(output_dir_frame, textvariable=self.output_dir_var,
                               font=('Microsoft YaHei UI', 10),
                               bg=COLORS['bg_secondary'], fg=COLORS['text_primary'],
                               insertbackground=COLORS['text_primary'],
                               relief='flat')
        output_entry.pack(side='left', fill='x', expand=True, padx=(10, 10))
        
        output_btn = ModernButton(output_dir_frame, "选择",
                                 command=self.browse_output_dir,
                                 width=80, height=30,
                                 bg_color=COLORS['bg_secondary'])
        output_btn.pack(side='right')
        
        # Word 工作流选项
        self.md_only_var = tk.BooleanVar(value=False)
        self.word_options_frame = tk.Frame(output_frame, bg=COLORS['bg_card'])
        self.word_options_frame.pack(fill='x', padx=20, pady=(0, 5))
        
        md_only_cb = tk.Checkbutton(self.word_options_frame, 
                                    text="仅导出 Markdown（不转回 Word）",
                                    variable=self.md_only_var,
                                    font=('Microsoft YaHei UI', 10),
                                    bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                                    selectcolor=COLORS['bg_secondary'],
                                    activebackground=COLORS['bg_card'])
        md_only_cb.pack(side='left')
        
        # PDF 工作流选项 - 设备选择
        self.pdf_device_frame = tk.Frame(output_frame, bg=COLORS['bg_card'])
        self.pdf_device_frame.pack(fill='x', padx=20, pady=(0, 5))
        
        device_label = tk.Label(self.pdf_device_frame, text="设备:", 
                               font=('Microsoft YaHei UI', 10),
                               bg=COLORS['bg_card'], fg=COLORS['text_secondary'])
        device_label.pack(side='left')
        
        self.device_var = tk.StringVar(value="auto")
        
        auto_rb = tk.Radiobutton(self.pdf_device_frame, text="自动", variable=self.device_var,
                                value="auto", font=('Microsoft YaHei UI', 10),
                                bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                                selectcolor=COLORS['bg_secondary'],
                                activebackground=COLORS['bg_card'])
        auto_rb.pack(side='left', padx=(5, 0))
        
        gpu_text = "GPU"
        if self.gpu_info['has_cuda']:
            name = self.gpu_info.get('device_name', '')
            vram = self.gpu_info.get('vram_mb')
            if name:
                vram_str = f" {vram}MB" if vram else ""
                gpu_text = f"GPU ({name}{vram_str})"
        else:
            gpu_text = "GPU (不可用)"
        
        gpu_rb = tk.Radiobutton(self.pdf_device_frame, text=gpu_text, variable=self.device_var,
                               value="cuda", font=('Microsoft YaHei UI', 10),
                               bg=COLORS['bg_card'], 
                               fg=COLORS['text_primary'] if self.gpu_info['has_cuda'] else COLORS['text_secondary'],
                               selectcolor=COLORS['bg_secondary'],
                               activebackground=COLORS['bg_card'],
                               state='normal' if self.gpu_info['has_cuda'] else 'disabled')
        gpu_rb.pack(side='left', padx=(10, 0))
        
        cpu_rb = tk.Radiobutton(self.pdf_device_frame, text="CPU", variable=self.device_var,
                               value="cpu", font=('Microsoft YaHei UI', 10),
                               bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                               selectcolor=COLORS['bg_secondary'],
                               activebackground=COLORS['bg_card'])
        cpu_rb.pack(side='left', padx=(10, 0))
        
        # PDF 工作流选项 - 公式和表格识别
        self.pdf_options_frame = tk.Frame(output_frame, bg=COLORS['bg_card'])
        self.pdf_options_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        # 公式识别
        self.formula_var = tk.BooleanVar(value=True)
        formula_cb = tk.Checkbutton(self.pdf_options_frame, 
                                    text="公式识别",
                                    variable=self.formula_var,
                                    font=('Microsoft YaHei UI', 10),
                                    bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                                    selectcolor=COLORS['bg_secondary'],
                                    activebackground=COLORS['bg_card'])
        formula_cb.pack(side='left')
        
        # 表格识别
        self.table_var = tk.BooleanVar(value=False)
        table_cb = tk.Checkbutton(self.pdf_options_frame, 
                                  text="表格识别",
                                  variable=self.table_var,
                                  font=('Microsoft YaHei UI', 10),
                                  bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                                  selectcolor=COLORS['bg_secondary'],
                                  activebackground=COLORS['bg_card'])
        table_cb.pack(side='left', padx=(20, 0))
        
        # 水印去除（可选功能，需要 OpenCV 和 PyMuPDF）
        self.watermark_var = tk.BooleanVar(value=False)
        watermark_text = "水印去除" if self.has_watermark_deps else "水印去除 (需安装opencv-python和pymupdf)"
        watermark_cb = tk.Checkbutton(self.pdf_options_frame, 
                                      text=watermark_text,
                                      variable=self.watermark_var,
                                      font=('Microsoft YaHei UI', 10),
                                      bg=COLORS['bg_card'], 
                                      fg=COLORS['text_primary'] if self.has_watermark_deps else COLORS['text_secondary'],
                                      selectcolor=COLORS['bg_secondary'],
                                      activebackground=COLORS['bg_card'],
                                      state='normal' if self.has_watermark_deps else 'disabled')
        watermark_cb.pack(side='left', padx=(20, 0))
        
        # 水印去除模式选择
        self.watermark_mode_var = tk.StringVar(value="fast")
        self.watermark_mode_fast = tk.Radiobutton(self.pdf_options_frame, 
                                                  text="快速",
                                                  variable=self.watermark_mode_var, 
                                                  value="fast",
                                                  font=('Microsoft YaHei UI', 9),
                                                  bg=COLORS['bg_card'], 
                                                  fg=COLORS['text_secondary'],
                                                  selectcolor=COLORS['bg_secondary'],
                                                  activebackground=COLORS['bg_card'],
                                                  state='normal' if self.has_watermark_deps else 'disabled')
        self.watermark_mode_fast.pack(side='left', padx=(5, 0))
        
        self.watermark_mode_deep = tk.Radiobutton(self.pdf_options_frame, 
                                                  text="深度",
                                                  variable=self.watermark_mode_var, 
                                                  value="deep",
                                                  font=('Microsoft YaHei UI', 9),
                                                  bg=COLORS['bg_card'], 
                                                  fg=COLORS['text_secondary'],
                                                  selectcolor=COLORS['bg_secondary'],
                                                  activebackground=COLORS['bg_card'],
                                                  state='normal' if self.has_watermark_deps else 'disabled')
        self.watermark_mode_deep.pack(side='left', padx=(5, 0))
    
    def setup_progress_area(self, parent):
        """设置进度显示区域"""
        progress_frame = CardFrame(parent, title="处理进度")
        progress_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, 
                                            variable=self.progress_var,
                                            maximum=100,
                                            style='Custom.Horizontal.TProgressbar')
        self.progress_bar.pack(fill='x', padx=20, pady=10)
        
        # 日志文本框
        log_frame = tk.Frame(progress_frame, bg=COLORS['bg_card'])
        log_frame.pack(fill='both', expand=True, padx=20, pady=(0, 15))
        
        self.log_text = tk.Text(log_frame, height=8,
                               font=('Consolas', 9),
                               bg=COLORS['bg_secondary'], 
                               fg=COLORS['text_primary'],
                               insertbackground=COLORS['text_primary'],
                               relief='flat', wrap='word')
        self.log_text.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=scrollbar.set)
    
    def setup_bottom_buttons(self, parent):
        """设置底部按钮"""
        button_frame = tk.Frame(parent, bg=COLORS['bg_primary'])
        button_frame.pack(fill='x')
        
        # 开始转换按钮
        self.convert_btn = ModernButton(button_frame, "开始转换",
                                        command=self.start_conversion,
                                        width=150, height=50,
                                        bg_color=COLORS['accent'])
        self.convert_btn.pack(side='left', padx=(0, 10))
        
        # 暂停/继续按钮
        self.pause_btn = ModernButton(button_frame, "暂停",
                                      command=self.toggle_pause,
                                      width=100, height=50,
                                      bg_color='#f0ad4e')
        self.pause_btn.pack(side='left', padx=(0, 10))
        
        # 刷新按钮
        refresh_btn = ModernButton(button_frame, "刷新",
                                   command=self.refresh_file_list,
                                   width=80, height=50,
                                   bg_color=COLORS['bg_secondary'])
        refresh_btn.pack(side='left', padx=(0, 10))
        
        # 断点续传按钮
        resume_btn = ModernButton(button_frame, "断点续传",
                                  command=self.resume_conversion,
                                  width=120, height=50,
                                  bg_color='#5bc0de')
        resume_btn.pack(side='left', padx=(0, 10))
        
        # 打开输出目录按钮
        open_output_btn = ModernButton(button_frame, "打开输出目录",
                                       command=self.open_output_dir,
                                       width=130, height=50,
                                       bg_color=COLORS['bg_secondary'])
        open_output_btn.pack(side='left', padx=(0, 10))
        
        # 检查环境按钮
        check_btn = ModernButton(button_frame, "检查环境",
                                command=self.check_environment,
                                width=100, height=50,
                                bg_color=COLORS['bg_secondary'])
        check_btn.pack(side='left')
        
        # 初始化状态变量
        self.is_paused = False
        self.is_running = False
        self.processed_files = set()  # 已处理的文件
    
    def setup_status_bar(self):
        """设置状态栏"""
        status_frame = tk.Frame(self.root, bg=COLORS['bg_secondary'], height=30)
        status_frame.pack(fill='x', side='bottom')
        
        self.status_var = tk.StringVar(value="就绪")
        status_label = tk.Label(status_frame, textvariable=self.status_var,
                               font=('Microsoft YaHei UI', 9),
                               bg=COLORS['bg_secondary'], 
                               fg=COLORS['text_secondary'])
        status_label.pack(side='left', padx=10, pady=5)
        
        # 环境信息
        env_info = f"Python: {Path(self.python_exe).parent.name if self.python_exe else 'N/A'}"
        env_label = tk.Label(status_frame, text=env_info,
                            font=('Microsoft YaHei UI', 9),
                            bg=COLORS['bg_secondary'],
                            fg=COLORS['text_secondary'])
        env_label.pack(side='right', padx=10, pady=5)
    
    def center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def toggle_file_mode(self):
        """切换文件模式"""
        self.file_count_var.set("")
    
    def browse_file(self):
        """浏览文件"""
        mode = self.file_mode_var.get()
        
        if mode == "single":
            workflow = self.workflow_var.get()
            if workflow == "pdf":
                filetypes = [("PDF文件", "*.pdf"), ("所有文件", "*.*")]
            else:
                filetypes = [("Word文档", "*.docx *.doc"), ("所有文件", "*.*")]
            
            filepath = filedialog.askopenfilename(filetypes=filetypes)
            if filepath:
                self.file_path_var.set(filepath)
        else:
            dirpath = filedialog.askdirectory()
            if dirpath:
                self.file_path_var.set(dirpath)
                self.refresh_file_list()
    
    def refresh_file_list(self):
        """刷新文件列表并显示数量"""
        mode = self.file_mode_var.get()
        if mode != "batch":
            return
        
        input_path = self.file_path_var.get()
        if not input_path:
            return
        
        input_path = Path(input_path)
        if not input_path.exists():
            return
        
        workflow = self.workflow_var.get()
        if workflow == "pdf":
            ext = "*.pdf"
        else:
            ext = "*.docx"
        
        # 根据是否包含子文件夹选择扫描方式
        if self.subfolder_var.get():
            files = list(input_path.rglob(ext))
            files += list(input_path.rglob(ext.upper()))
        else:
            files = list(input_path.glob(ext))
            files += list(input_path.glob(ext.upper()))
        
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
        self.log(f"扫描完成: 找到 {len(files)} 个文件\n", 'info')
    
    def toggle_pause(self):
        """暂停/继续"""
        if not self.is_running:
            return
        
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.config(text="继续")
            self.log("处理已暂停\n", 'warning')
            self.status_var.set("已暂停")
        else:
            self.pause_btn.config(text="暂停")
            self.log("继续处理...\n", 'info')
            self.status_var.set("处理中...")
    
    def resume_conversion(self):
        """断点续传"""
        if self.is_running:
            messagebox.showwarning("提示", "当前有任务正在运行")
            return
        
        mode = self.file_mode_var.get()
        if mode != "batch":
            messagebox.showwarning("提示", "断点续传仅支持批量处理模式")
            return
        
        output_dir = Path(self.output_dir_var.get())
        if not output_dir.exists():
            messagebox.showwarning("提示", "输出目录不存在")
            return
        
        # 扫描已处理的文件
        self.processed_files = set()
        for item in output_dir.iterdir():
            if item.is_dir():
                # 检查是否有输出文件
                has_output = False
                for ext in ['*.md', '*.docx', '*.pdf']:
                    if list(item.glob(ext)):
                        has_output = True
                        break
                if has_output:
                    self.processed_files.add(item.name.lower())
        
        self.log(f"已找到 {len(self.processed_files)} 个已处理的文件\n", 'info')
        self.log("点击\"开始转换\"继续处理剩余文件\n", 'info')
        
        # 开始转换
        self.start_conversion(resume=True)
    
    def browse_output_dir(self):
        """选择输出目录"""
        dirpath = filedialog.askdirectory()
        if dirpath:
            self.output_dir_var.set(dirpath)
    
    def open_output_dir(self):
        """打开输出目录"""
        output_dir = Path(self.output_dir_var.get())
        if output_dir.exists():
            os.startfile(str(output_dir))
        else:
            messagebox.showinfo("提示", "输出目录不存在")
    
    def check_environment(self):
        """检查环境"""
        self.log_text.delete(1.0, tk.END)
        self.log("正在检查环境...\n", 'info')
        
        # 检查 Python
        self.log(f"Python: {self.python_exe}\n", 'info')
        
        # 检查 Pandoc
        try:
            result = subprocess.run([self.pandoc_path, "--version"],
                                   capture_output=True, text=True,
                                   creationflags=SUBPROCESS_FLAGS)
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                self.log(f"Pandoc: {version}\n", 'success')
            else:
                self.log("Pandoc: 未找到\n", 'error')
        except Exception as e:
            self.log(f"Pandoc: 检查失败 - {e}\n", 'error')
        
        # 检查 MinerU
        try:
            # 先检查新版 MinerU 3.x
            result = subprocess.run([self.python_exe, "-c", "import mineru; print('mineru 3.x')"],
                                   capture_output=True, text=True,
                                   creationflags=SUBPROCESS_FLAGS)
            if result.returncode == 0 and 'mineru' in result.stdout:
                # 获取详细版本
                version_result = subprocess.run(
                    [r"D:\CDriveMoved\miniforge3\envs\mineru2\Scripts\mineru.exe", "--version"],
                    capture_output=True, text=True,
                    creationflags=SUBPROCESS_FLAGS
                )
                if version_result.returncode == 0:
                    self.log(f"MinerU: {version_result.stdout.strip()} (支持公式识别)\n", 'success')
                else:
                    self.log("MinerU: 3.x 已安装\n", 'success')
            else:
                # 检查旧版 magic-pdf
                result = subprocess.run([self.python_exe, "-m", "magic_pdf.cli", "--version"],
                                       capture_output=True, text=True,
                                       creationflags=SUBPROCESS_FLAGS)
                if result.returncode == 0:
                    self.log(f"MinerU: {result.stdout.strip()} (旧版，不支持公式识别)\n", 'warning')
                else:
                    self.log("MinerU: 未找到\n", 'warning')
        except Exception as e:
            self.log(f"MinerU: 检查失败 - {e}\n", 'warning')
        
        # 检查 PyTorch 和 GPU
        try:
            result = subprocess.run([self.python_exe, "-c",
                                    "import torch; print(f'{torch.__version__},{torch.cuda.is_available()}')"],
                                   capture_output=True, text=True,
                                   creationflags=SUBPROCESS_FLAGS)
            if result.returncode == 0:
                version, cuda = result.stdout.strip().split(',')
                cuda_status = "CUDA已启用" if cuda == "True" else "仅CPU"
                self.log(f"PyTorch: {version} ({cuda_status})\n", 'success')
                # 显示 GPU 详情
                if cuda == "True" and self.gpu_info.get('device_name'):
                    name = self.gpu_info['device_name']
                    vram = self.gpu_info.get('vram_mb')
                    vram_str = f", {vram}MB" if vram else ""
                    self.log(f"GPU: {name}{vram_str}\n", 'success')
                elif cuda != "True" and self.gpu_info.get('device_name'):
                    # nvidia-smi 能工作但 PyTorch 缺少 CUDA 支持
                    name = self.gpu_info['device_name']
                    vram = self.gpu_info.get('vram_mb')
                    vram_str = f", {vram}MB" if vram else ""
                    self.log(f"GPU: {name}{vram_str} (驱动正常，但PyTorch未启用CUDA)\n", 'warning')
                    error = self.gpu_info.get('error')
                    if error:
                        self.log(f"  原因: {error}\n", 'warning')
                elif cuda != "True":
                    error = self.gpu_info.get('error')
                    if error:
                        self.log(f"GPU: 不可用 ({error})\n", 'warning')
                    else:
                        self.log("GPU: 不可用 (将使用CPU模式)\n", 'warning')
            else:
                error = self.gpu_info.get('error')
                if error:
                    self.log(f"GPU: 检测失败 ({error})\n", 'warning')
                else:
                    self.log("GPU: 检测失败 (将使用CPU模式)\n", 'warning')
        except Exception as e:
            self.log(f"PyTorch: 检查失败 - {e}\n", 'warning')
            error = self.gpu_info.get('error')
            if error:
                self.log(f"GPU: 检测失败 ({error})\n", 'warning')
            else:
                self.log("GPU: 检测失败 (将使用CPU模式)\n", 'warning')
        
        # 检查水印去除依赖
        self.log("\n可选功能:\n", 'info')
        
        # OpenCV
        try:
            result = subprocess.run([self.python_exe, "-c", "import cv2; print(cv2.__version__)"],
                                   capture_output=True, text=True,
                                   creationflags=SUBPROCESS_FLAGS)
            if result.returncode == 0:
                self.log(f"OpenCV: {result.stdout.strip()} ✓\n", 'success')
            else:
                self.log("OpenCV: 未安装 (水印去除功能不可用)\n", 'warning')
        except Exception as e:
            self.log(f"OpenCV: 未安装\n", 'warning')
        
        # PyMuPDF
        try:
            result = subprocess.run([self.python_exe, "-c", "import fitz; print('ok')"],
                                   capture_output=True, text=True,
                                   creationflags=SUBPROCESS_FLAGS)
            if result.returncode == 0 and 'ok' in result.stdout:
                # 获取版本
                ver_result = subprocess.run([self.python_exe, "-c", "import fitz; print(fitz.VersionBind)"],
                                           capture_output=True, text=True,
                                           creationflags=SUBPROCESS_FLAGS)
                version = ver_result.stdout.strip() if ver_result.returncode == 0 else "已安装"
                self.log(f"PyMuPDF: {version} ✓\n", 'success')
            else:
                self.log("PyMuPDF: 未安装 (水印去除功能不可用)\n", 'warning')
        except Exception as e:
            self.log(f"PyMuPDF: 未安装\n", 'warning')
        
        # 水印去除功能状态
        if self.has_watermark_deps:
            self.log("水印去除: 可用 (快速/深度两种模式)\n", 'success')
        else:
            self.log("水印去除: 不可用 (需安装 opencv-python 和 pymupdf)\n", 'warning')
        
        self.log("\n环境检查完成！\n", 'info')
    
    def log(self, message, level='info'):
        """添加日志（线程安全）"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        colors = {
            'info': COLORS['text_primary'],
            'success': COLORS['success'],
            'warning': COLORS['warning'],
            'error': COLORS['error'],
        }
        
        # 使用 after 确保在主线程更新 GUI
        def update_log():
            self.log_text.insert(tk.END, f"[{timestamp}] {message}")
            self.log_text.see(tk.END)
        
        self.root.after(0, update_log)
    
    def start_conversion(self, resume=False):
        """开始转换"""
        # 获取参数
        file_path = self.file_path_var.get()
        
        if not file_path:
            messagebox.showwarning("警告", "请选择文件或目录")
            return
        
        # 获取选中的格式
        formats = [fmt for fmt, var in self.format_vars.items() if var.get()]
        
        if not formats:
            messagebox.showwarning("警告", "请至少选择一种输出格式")
            return
        
        # 清空日志（非断点续传模式）
        if not resume:
            self.log_text.delete(1.0, tk.END)
            self.processed_files = set()
        
        self.progress_var.set(0)
        self.is_running = True
        self.is_paused = False
        self.pause_btn.config(text="暂停")
        
        # 记录启动信息
        self.log("正在启动转换任务...\n", 'info')
        self.log(f"文件路径: {file_path}\n", 'info')
        self.log(f"输出格式: {formats}\n", 'info')
        
        # 在新线程中执行
        try:
            thread = threading.Thread(target=self.run_conversion,
                                      args=(file_path, formats, resume))
            thread.daemon = True
            thread.start()
        except Exception as e:
            self.log(f"启动线程失败: {str(e)}\n", 'error')
            import traceback
            self.log(traceback.format_exc(), 'error')
    
    def run_conversion(self, file_path, formats, resume=False):
        """执行转换"""
        try:
            self.root.after(0, lambda: self.status_var.set("正在处理..."))
            self.log("开始处理...\n", 'info')
            
            workflow_type = self.workflow_var.get()
            mode = self.file_mode_var.get()
            output_dir = self.output_dir_var.get()
            
            self.log(f"工作流类型: {workflow_type}\n", 'info')
            self.log(f"处理模式: {mode}\n", 'info')
            
            # 加载配置
            self.log("加载配置文件...\n", 'info')
            config = self.load_config()
            
            # 更新 MinerU 配置
            if 'mineru' not in config:
                config['mineru'] = {}
            config['mineru']['enable_formula'] = self.formula_var.get()
            config['mineru']['enable_table'] = self.table_var.get()
            config['mineru']['device'] = self.device_var.get()
            
            # 设置 Pandoc 路径
            if 'pandoc' not in config:
                config['pandoc'] = {}
            config['pandoc']['path'] = self.pandoc_path
            
            # 设置水印去除配置
            if 'watermark_remover' not in config:
                config['watermark_remover'] = {}
            config['watermark_remover']['mode'] = self.watermark_mode_var.get()
            
            self.log(f"输入: {file_path}\n", 'info')
            self.log(f"输出: {output_dir}\n", 'info')
            self.log(f"格式: {', '.join(formats)}\n", 'info')
            if workflow_type == "pdf":
                self.log(f"公式识别: {'是' if self.formula_var.get() else '否'}\n", 'info')
                self.log(f"表格识别: {'是' if self.table_var.get() else '否'}\n", 'info')
                if self.watermark_var.get():
                    self.log(f"水印去除: 是 ({self.watermark_mode_var.get()}模式)\n", 'info')
                else:
                    self.log(f"水印去除: 否\n", 'info')
            self.log("\n", 'info')
            
            # 导入工作流模块
            self.log("导入工作流模块...\n", 'info')
            try:
                from doc_workflow import PDFWorkflow, WordWorkflow
                self.log("工作流模块导入成功\n", 'success')
            except ImportError as e:
                # 打包后的路径
                import sys
                if getattr(sys, 'frozen', False):
                    bundle_dir = Path(sys._MEIPASS)
                    sys.path.insert(0, str(bundle_dir))
                from doc_workflow import PDFWorkflow, WordWorkflow
                self.log("工作流模块导入成功 (打包模式)\n", 'success')
            
            if mode == "batch":
                if workflow_type == "pdf":
                    self.log("批量PDF处理...\n", 'info')
                    workflow = PDFWorkflow(config)
                    self.log(f"开始批量处理，输入目录: {file_path}\n", 'info')
                    self.log(f"输出目录: {output_dir}\n", 'info')
                    self.log(f"输出格式: {formats}\n", 'info')
                    try:
                        # 检查输入目录
                        input_path = Path(file_path)
                        if not input_path.exists():
                            self.log(f"错误: 输入目录不存在\n", 'error')
                            return
                        
                        # 根据是否包含子文件夹选择扫描方式
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
                        
                        total_files = len(pdf_files)
                        self.log(f"找到 {total_files} 个PDF文件\n", 'info')
                        
                        # 断点续传：过滤已处理的文件
                        if resume and self.processed_files:
                            original_count = len(pdf_files)
                            pdf_files = [f for f in pdf_files if f.stem.lower() not in self.processed_files]
                            skipped = original_count - len(pdf_files)
                            self.log(f"跳过已处理的 {skipped} 个文件\n", 'info')
                        
                        if not pdf_files:
                            self.log(f"没有需要处理的文件\n", 'warning')
                            return
                        
                        # 处理每个文件
                        success_count = 0
                        failed_count = 0
                        skipped_count = len(self.processed_files) if resume else 0
                        start_time = datetime.now()
                        
                        for i, pdf_file in enumerate(pdf_files, 1):
                            # 检查暂停
                            while self.is_paused:
                                self.root.update()
                                import time
                                time.sleep(0.1)
                            
                            if not self.is_running:
                                self.log(f"\n处理已中断\n", 'warning')
                                break
                            
                            file_start_time = datetime.now()
                            self.log(f"\n[{i}/{len(pdf_files)}] 处理: {pdf_file.name}\n", 'info')
                            
                            # 更新进度
                            progress = (i / len(pdf_files)) * 100
                            self.progress_var.set(progress)
                            
                            # 为每个文件创建单独的输出目录
                            file_output_dir = Path(output_dir) / pdf_file.stem
                            file_output_dir.mkdir(parents=True, exist_ok=True)
                            
                            try:
                                result = workflow.run(
                                    str(pdf_file),
                                    str(file_output_dir),
                                    formats,
                                    enable_formula=self.formula_var.get(),
                                    enable_table=self.table_var.get(),
                                    remove_watermark=self.watermark_var.get()
                                )
                                
                                # 计算处理时间
                                file_time = (datetime.now() - file_start_time).total_seconds()
                                
                                if result.get('success'):
                                    success_count += 1
                                    self.processed_files.add(pdf_file.stem.lower())
                                    self.log(f"  ✓ 成功 ({file_time:.1f}秒)\n", 'success')
                                    for fmt, path in result.get('outputs', {}).items():
                                        self.log(f"    {fmt.upper()}: {path}\n", 'success')
                                else:
                                    failed_count += 1
                                    self.log(f"  ✗ 失败 ({file_time:.1f}秒)\n", 'error')
                                    for error in result.get('errors', []):
                                        # 截断错误信息
                                        if len(error) > 200:
                                            error = error[:200] + "..."
                                        self.log(f"    错误: {error}\n", 'error')
                            except Exception as e:
                                failed_count += 1
                                file_time = (datetime.now() - file_start_time).total_seconds()
                                self.log(f"  ✗ 异常 ({file_time:.1f}秒): {str(e)}\n", 'error')
                            
                            # 显示总耗时
                            elapsed = (datetime.now() - start_time).total_seconds()
                            avg_time = elapsed / i
                            remaining = avg_time * (len(pdf_files) - i)
                            self.status_var.set(f"处理中... 已用时 {elapsed:.0f}秒，预计剩余 {remaining:.0f}秒")
                        
                        # 显示结果
                        total_time = (datetime.now() - start_time).total_seconds()
                        self.progress_var.set(100)
                        self.log(f"\n批量处理完成！\n", 'success')
                        self.log(f"总计: {total_files}\n", 'info')
                        if skipped_count > 0:
                            self.log(f"跳过: {skipped_count}\n", 'info')
                        self.log(f"成功: {success_count}\n", 'success')
                        self.log(f"失败: {failed_count}\n", 'error' if failed_count > 0 else 'info')
                        self.log(f"总耗时: {total_time:.1f}秒\n", 'info')
                        self.status_var.set("转换完成")
                        messagebox.showinfo("完成", f"批量处理完成！\n成功: {success_count}, 失败: {failed_count}\n总耗时: {total_time:.1f}秒")
                        return
                        
                    except Exception as e:
                        self.log(f"批量处理异常: {str(e)}\n", 'error')
                        import traceback
                        self.log(traceback.format_exc(), 'error')
                        return
                else:
                    self.log("批量Word处理...\n", 'info')
                    workflow = WordWorkflow(config)
                    result = workflow.batch_run(
                        file_path,
                        output_dir,
                        export_md_only=self.md_only_var.get()
                    )
                    if result.get('success'):
                        self.progress_var.set(100)
                        self.log(f"\n批量Word处理完成！\n", 'success')
                        self.log(f"总计: {result.get('total', 0)}\n", 'info')
                        self.log(f"成功: {result.get('success_count', 0)}\n", 'success')
                        failed_count = result.get('failed_count', 0)
                        self.log(f"失败: {failed_count}\n", 'error' if failed_count else 'info')
                        self.status_var.set("转换完成")
                        messagebox.showinfo(
                            "完成",
                            f"批量Word处理完成！\n成功: {result.get('success_count', 0)}, 失败: {failed_count}"
                        )
                    else:
                        self.log(f"Word批量处理失败: {result.get('error', '未知错误')}\n", 'error')
                        self.status_var.set("转换失败")
                        messagebox.showerror("错误", "Word批量处理失败，请查看日志")
                    return
            
            else:
                # 单文件处理
                if workflow_type == "pdf":
                    self.log("PDF工作流处理...\n", 'info')
                    workflow = PDFWorkflow(config)
                    result = workflow.run(
                        file_path, output_dir, formats,
                        enable_formula=self.formula_var.get(),
                        enable_table=self.table_var.get(),
                        remove_watermark=self.watermark_var.get()
                    )
                else:
                    self.log("Word工作流处理...\n", 'info')
                    workflow = WordWorkflow(config)
                    result = workflow.run(
                        file_path, output_dir,
                        export_md_only=self.md_only_var.get()
                    )
                
                if result.get('success'):
                    self.progress_var.set(100)
                    self.log("\n转换完成！\n", 'success')
                    self.log("输出文件:\n", 'info')
                    for fmt, path in result.get('outputs', {}).items():
                        self.log(f"  {fmt.upper()}: {path}\n", 'success')
                    self.status_var.set("转换完成")
                    messagebox.showinfo("成功", "文档转换完成！")
                else:
                    self.log("\n转换失败！\n", 'error')
                    for error in result.get('errors', []):
                        self.log(f"  错误: {error}\n", 'error')
                    self.status_var.set("转换失败")
                    messagebox.showerror("错误", "文档转换失败，请查看日志")
                    
        except Exception as e:
            import traceback
            self.log(f"\n错误: {str(e)}\n", 'error')
            self.log(traceback.format_exc(), 'error')
            self.root.after(0, lambda: self.status_var.set("转换失败"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"转换失败: {str(e)}"))
        finally:
            self.is_running = False
            self.is_paused = False
            self.log("任务结束\n", 'info')
    
    def load_config(self):
        """加载配置文件"""
        import yaml
        
        # 尝试多个配置文件路径
        config_paths = [
            Path(__file__).parent / 'config.yaml',
        ]
        
        # 打包后的路径
        if getattr(sys, 'frozen', False):
            bundle_dir = Path(sys._MEIPASS)
            config_paths.insert(0, bundle_dir / 'config.yaml')
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        return yaml.safe_load(f) or {}
                except Exception as e:
                    self.log(f"加载配置失败: {e}\n", 'warning')
        
        return {}
    
    def run(self):
        """运行应用"""
        self.root.mainloop()


def main():
    app = MinerUtoMDGUI()
    app.run()


if __name__ == '__main__':
    main()
