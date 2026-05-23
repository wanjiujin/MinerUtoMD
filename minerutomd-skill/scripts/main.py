"""
MinerUtoMD - 文档转换工作流工具
"""
import os
import sys
import logging
from pathlib import Path
from typing import Optional, List

# Windows 编码修复
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # 设置控制台代码页为 UTF-8
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)
    except:
        pass

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
import yaml

# 支持直接运行和包导入
try:
    from .workflow import PDFWorkflow, WordWorkflow
    from .mineru_extractor import MinerUExtractor
    from .pandoc_converter import PandocConverter
except ImportError:
    from workflow import PDFWorkflow, WordWorkflow
    from mineru_extractor import MinerUExtractor
    from pandoc_converter import PandocConverter

# 初始化Rich控制台 - 禁用 legacy_windows 模式避免编码问题
console = Console(force_terminal=True, legacy_windows=False)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: Optional[str] = None) -> dict:
    """加载配置文件"""
    if config_path and Path(config_path).exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    # 默认配置路径
    default_config = Path(__file__).parent / 'config.yaml'
    if default_config.exists():
        with open(default_config, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    return {}


def check_dependencies():
    """检查依赖工具"""
    console.print("\n[bold]检查依赖工具...[/bold]\n")
    
    # 检查Pandoc
    pandoc = PandocConverter()
    if pandoc.check_installation():
        console.print("✓ Pandoc 已安装", style="green")
    else:
        console.print("✗ Pandoc 未安装", style="red")
        console.print("  请从 https://pandoc.org/installing.html 下载安装", style="yellow")
    
    # 检查MinerU
    mineru = MinerUExtractor()
    if mineru.check_installation():
        console.print("✓ MinerU 已安装", style="green")
    else:
        console.print("✗ MinerU 未安装", style="red")
        console.print("  运行: pip install magic-pdf[full]", style="yellow")
    
    console.print()


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='配置文件路径')
@click.pass_context
def cli(ctx, config):
    """
    MinerUtoMD - 文档转换工作流工具
    
    \b
    工作流一（PDF专用）:
      PDF → MinerU提取 → Markdown → Pandoc转换 → Word/PDF/EPUB/HTML
    
    \b
    工作流二（Word专用）:
      docx → Pandoc转MD → 优化排版 → Pandoc转回规整docx
    """
    ctx.ensure_object(dict)
    ctx.obj['config'] = load_config(config)


@cli.command()
def check():
    """检查依赖工具是否安装"""
    check_dependencies()


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='输出目录')
@click.option('--format', '-f', 'formats', multiple=True, 
              type=click.Choice(['md', 'docx', 'pdf', 'epub', 'html']),
              default=['md'], help='输出格式（可多次指定）')
@click.option('--formula', is_flag=True, default=True, help='启用公式识别')
@click.option('--table', is_flag=True, default=False, help='启用表格识别')
@click.option('--keep-temp', is_flag=True, help='保留中间文件')
@click.pass_context
def pdf(ctx, input_file, output, formats, formula, table, keep_temp):
    """
    PDF工作流：PDF → Markdown → 多格式
    
    \b
    示例:
      minerutomd pdf document.pdf
      minerutomd pdf document.pdf -f docx -f pdf
      minerutomd pdf document.pdf -o ./output -f docx
      minerutomd pdf document.pdf --formula --table
    """
    config = ctx.obj['config']
    
    # 更新配置
    if 'mineru' not in config:
        config['mineru'] = {}
    config['mineru']['enable_formula'] = formula
    config['mineru']['enable_table'] = table
    
    # 确定输出目录
    if not output:
        output = Path(input_file).parent / 'output'
    
    console.print(Panel.fit(
        f"[bold cyan]PDF工作流[/bold cyan]\n\n"
        f"输入: {input_file}\n"
        f"输出: {output}\n"
        f"格式: {', '.join(formats)}\n"
        f"公式识别: {'是' if formula else '否'}\n"
        f"表格识别: {'是' if table else '否'}",
        title="MinerUtoMD"
    ))
    
    workflow = PDFWorkflow(config)
    
    # Windows 下简化输出，避免 Rich spinner 编码问题
    console.print("[cyan]处理中...[/cyan]")
    
    result = workflow.run(
        input_file,
        output,
        list(formats),
        keep_intermediate=keep_temp,
        enable_formula=formula,
        enable_table=table
    )
    
    if result['success']:
        console.print("\n[bold green]✓ 转换成功！[/bold green]\n")
        
        # 显示输出文件
        table = Table(title="输出文件")
        table.add_column("格式", style="cyan")
        table.add_column("路径", style="green")
        
        for fmt, path in result['outputs'].items():
            table.add_row(fmt.upper(), path)
        
        console.print(table)
    else:
        console.print(f"\n[bold red]✗ 转换失败[/bold red]")
        for error in result['errors']:
            console.print(f"  {error}", style="red")


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='输出目录')
@click.option('--md-only', is_flag=True, help='只导出Markdown，不转回Word')
@click.option('--keep-temp', is_flag=True, help='保留中间文件')
@click.pass_context
def word(ctx, input_file, output, md_only, keep_temp):
    """
    Word工作流：docx → Markdown → 优化 → docx
    
    \b
    示例:
      minerutomd word document.docx
      minerutomd word document.docx --md-only
      minerutomd word document.docx -o ./output
    """
    config = ctx.obj['config']
    
    # 确定输出目录
    if not output:
        output = Path(input_file).parent / 'output'
    
    console.print(Panel.fit(
        f"[bold cyan]Word工作流[/bold cyan]\n\n"
        f"输入: {input_file}\n"
        f"输出: {output}\n"
        f"模式: {'仅Markdown' if md_only else '完整工作流'}",
        title="MinerUtoMD"
    ))
    
    workflow = WordWorkflow(config)
    
    console.print("[cyan]处理中...[/cyan]")
    
    result = workflow.run(
        input_file,
        output,
        export_md_only=md_only,
        keep_intermediate=keep_temp
    )
    
    if result['success']:
        console.print("\n[bold green]✓ 转换成功！[/bold green]\n")
        
        # 显示输出文件
        table = Table(title="输出文件")
        table.add_column("格式", style="cyan")
        table.add_column("路径", style="green")
        
        for fmt, path in result['outputs'].items():
            table.add_row(fmt.upper(), path)
        
        console.print(table)
    else:
        console.print(f"\n[bold red]✗ 转换失败[/bold red]")
        for error in result['errors']:
            console.print(f"  {error}", style="red")


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='输出目录')
@click.option('--format', '-f', 'formats', multiple=True,
              type=click.Choice(['md', 'docx', 'pdf', 'epub', 'html']),
              default=['md'], help='输出格式')
@click.pass_context
def batch_pdf(ctx, input_dir, output, formats):
    """
    批量处理PDF文件
    
    \b
    示例:
      minerutomd batch-pdf ./pdfs
      minerutomd batch-pdf ./pdfs -f docx -f pdf
    """
    config = ctx.obj['config']
    
    if not output:
        output = Path(input_dir) / 'output'
    
    console.print(Panel.fit(
        f"[bold cyan]批量PDF工作流[/bold cyan]\n\n"
        f"输入目录: {input_dir}\n"
        f"输出目录: {output}\n"
        f"格式: {', '.join(formats)}",
        title="MinerUtoMD"
    ))
    
    workflow = PDFWorkflow(config)
    
    console.print("[cyan]批量处理中...[/cyan]")
    
    result = workflow.batch_run(
        input_dir,
        output,
        list(formats)
    )
    
    console.print(f"\n[bold]处理完成[/bold]")
    console.print(f"  总计: {result['total']}")
    console.print(f"  成功: [green]{result['success_count']}[/green]")
    console.print(f"  失败: [red]{result['failed_count']}[/red]")


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='输出目录')
@click.option('--md-only', is_flag=True, help='只导出Markdown')
@click.pass_context
def batch_word(ctx, input_dir, output, md_only):
    """
    批量处理Word文件
    
    \b
    示例:
      minerutomd batch-word ./docs
      minerutomd batch-word ./docs --md-only
    """
    config = ctx.obj['config']
    
    if not output:
        output = Path(input_dir) / 'output'
    
    console.print(Panel.fit(
        f"[bold cyan]批量Word工作流[/bold cyan]\n\n"
        f"输入目录: {input_dir}\n"
        f"输出目录: {output}\n"
        f"模式: {'仅Markdown' if md_only else '完整工作流'}",
        title="MinerUtoMD"
    ))
    
    workflow = WordWorkflow(config)
    
    console.print("[cyan]批量处理中...[/cyan]")
    
    result = workflow.batch_run(
        input_dir,
        output,
        export_md_only=md_only
    )
    
    console.print(f"\n[bold]处理完成[/bold]")
    console.print(f"  总计: {result['total']}")
    console.print(f"  成功: [green]{result['success_count']}[/green]")
    console.print(f"  失败: [red]{result['failed_count']}[/red]")


@cli.command()
def formats():
    """显示支持的输出格式"""
    converter = PandocConverter()
    supported = converter.get_supported_formats()
    
    table = Table(title="支持的输出格式")
    table.add_column("格式", style="cyan")
    table.add_column("说明", style="green")
    
    for fmt, desc in supported.items():
        table.add_row(fmt, desc)
    
    console.print(table)


def main():
    """主入口"""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]用户取消操作[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]错误: {str(e)}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()
