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

# 设置环境变量（解决 HuggingFace 访问和 Windows 路径长度问题）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HOME'] = 'C:/hf_cache'

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
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MinerUtoMD - 文档转换工具")
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
        
        self.setup_ui()
        self.center_window()
        
    def detect_python_exe(self):
        """检测 Python 可执行文件"""
        # 优先使用新版 MinerU 环境 (支持公式识别)
        mineru2_python = r"C:\ProgramData\miniforge3\envs\mineru2\python.exe"
        if Path(mineru2_python).exists():
            return mineru2_python
        
        # 旧版环境
        conda_python = r"C:\ProgramData\miniforge3\envs\mineru\python.exe"
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
                                        width=200, height=50,
                                        bg_color=COLORS['accent'])
        self.convert_btn.pack(side='left', padx=(0, 15))
        
        # 打开输出目录按钮
        open_output_btn = ModernButton(button_frame, "打开输出目录",
                                       command=self.open_output_dir,
                                       width=150, height=50,
                                       bg_color=COLORS['bg_secondary'])
        open_output_btn.pack(side='left', padx=(0, 15))
        
        # 检查环境按钮
        check_btn = ModernButton(button_frame, "检查环境",
                                command=self.check_environment,
                                width=120, height=50,
                                bg_color=COLORS['bg_secondary'])
        check_btn.pack(side='left')
    
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
        pass  # 可以添加更多逻辑
    
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
                                   capture_output=True, text=True)
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
                                   capture_output=True, text=True)
            if result.returncode == 0 and 'mineru' in result.stdout:
                # 获取详细版本
                version_result = subprocess.run(
                    [r"C:\ProgramData\miniforge3\envs\mineru2\Scripts\mineru.exe", "--version"],
                    capture_output=True, text=True
                )
                if version_result.returncode == 0:
                    self.log(f"MinerU: {version_result.stdout.strip()} (支持公式识别)\n", 'success')
                else:
                    self.log("MinerU: 3.x 已安装\n", 'success')
            else:
                # 检查旧版 magic-pdf
                result = subprocess.run([self.python_exe, "-m", "magic_pdf.cli", "--version"],
                                       capture_output=True, text=True)
                if result.returncode == 0:
                    self.log(f"MinerU: {result.stdout.strip()} (旧版，不支持公式识别)\n", 'warning')
                else:
                    self.log("MinerU: 未找到\n", 'warning')
        except Exception as e:
            self.log(f"MinerU: 检查失败 - {e}\n", 'warning')
        
        # 检查 PyTorch
        try:
            result = subprocess.run([self.python_exe, "-c",
                                    "import torch; print(f'{torch.__version__},{torch.cuda.is_available()}')"],
                                   capture_output=True, text=True)
            if result.returncode == 0:
                version, cuda = result.stdout.strip().split(',')
                cuda_status = "CUDA已启用" if cuda == "True" else "仅CPU"
                self.log(f"PyTorch: {version} ({cuda_status})\n", 'success')
        except Exception as e:
            self.log(f"PyTorch: 检查失败 - {e}\n", 'warning')
        
        self.log("\n环境检查完成！\n", 'info')
    
    def log(self, message, level='info'):
        """添加日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        colors = {
            'info': COLORS['text_primary'],
            'success': COLORS['success'],
            'warning': COLORS['warning'],
            'error': COLORS['error'],
        }
        
        self.log_text.insert(tk.END, f"[{timestamp}] {message}")
        self.log_text.see(tk.END)
    
    def start_conversion(self):
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
        
        # 清空日志
        self.log_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        
        # 在新线程中执行
        thread = threading.Thread(target=self.run_conversion,
                                  args=(file_path, formats))
        thread.daemon = True
        thread.start()
    
    def run_conversion(self, file_path, formats):
        """执行转换"""
        try:
            self.status_var.set("正在处理...")
            self.log("开始处理...\n", 'info')
            
            workflow_type = self.workflow_var.get()
            mode = self.file_mode_var.get()
            output_dir = self.output_dir_var.get()
            
            # 加载配置
            config = self.load_config()
            
            # 更新 MinerU 配置
            if 'mineru' not in config:
                config['mineru'] = {}
            config['mineru']['enable_formula'] = self.formula_var.get()
            config['mineru']['enable_table'] = self.table_var.get()
            
            # 设置 Pandoc 路径
            if 'pandoc' not in config:
                config['pandoc'] = {}
            config['pandoc']['path'] = self.pandoc_path
            
            self.log(f"输入: {file_path}\n", 'info')
            self.log(f"输出: {output_dir}\n", 'info')
            self.log(f"格式: {', '.join(formats)}\n", 'info')
            if workflow_type == "pdf":
                self.log(f"公式识别: {'是' if self.formula_var.get() else '否'}\n", 'info')
                self.log(f"表格识别: {'是' if self.table_var.get() else '否'}\n", 'info')
            self.log("\n", 'info')
            
            # 导入工作流模块
            try:
                from workflow import PDFWorkflow, WordWorkflow
            except ImportError:
                # 打包后的路径
                import sys
                if getattr(sys, 'frozen', False):
                    bundle_dir = Path(sys._MEIPASS)
                    sys.path.insert(0, str(bundle_dir))
                from workflow import PDFWorkflow, WordWorkflow
            
            if mode == "batch":
                if workflow_type == "pdf":
                    self.log("批量PDF处理...\n", 'info')
                    workflow = PDFWorkflow(config)
                    result = workflow.batch_run(file_path, output_dir, formats)
                else:
                    self.log("批量Word处理...\n", 'info')
                    workflow = WordWorkflow(config)
                    result = workflow.batch_run(
                        file_path, output_dir, 
                        export_md_only=self.md_only_var.get()
                    )
                
                if result.get('success'):
                    self.progress_var.set(100)
                    self.log(f"\n处理完成！\n", 'success')
                    self.log(f"总计: {result['total']}\n", 'info')
                    self.log(f"成功: {result['success_count']}\n", 'success')
                    self.log(f"失败: {result['failed_count']}\n", 
                            'error' if result['failed_count'] > 0 else 'info')
                    self.status_var.set("转换完成")
                    messagebox.showinfo("成功", f"批量处理完成！\n成功: {result['success_count']}, 失败: {result['failed_count']}")
                else:
                    self.log(f"\n处理失败: {result.get('error', '未知错误')}\n", 'error')
                    self.status_var.set("转换失败")
                    messagebox.showerror("错误", f"处理失败: {result.get('error', '未知错误')}")
            else:
                # 单文件处理
                if workflow_type == "pdf":
                    self.log("PDF工作流处理...\n", 'info')
                    workflow = PDFWorkflow(config)
                    result = workflow.run(
                        file_path, output_dir, formats,
                        enable_formula=self.formula_var.get(),
                        enable_table=self.table_var.get()
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
            self.status_var.set("转换失败")
            messagebox.showerror("错误", f"转换失败: {str(e)}")
    
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
