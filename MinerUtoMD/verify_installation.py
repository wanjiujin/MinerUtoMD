"""
验证安装 - 简化版
"""
import sys
import subprocess
from pathlib import Path

print("=" * 60)
print("MinerUtoMD 安装验证")
print("=" * 60)

# 1. 检查Python版本
print(f"\n[Python] {sys.version}")

# 2. 检查Pandoc
print("\n[Pandoc]")
pandoc_path = r"C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Packages\JohnMacFarlane.Pandoc_Microsoft.Winget.Source_8wekyb3d8bbwe\pandoc-3.9.0.2\pandoc.exe"
try:
    result = subprocess.run([pandoc_path, "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        version = result.stdout.split('\n')[0]
        print(f"  状态: 已安装")
        print(f"  版本: {version}")
        print(f"  路径: {pandoc_path}")
    else:
        print("  状态: 未找到")
except Exception as e:
    print(f"  状态: 错误 - {e}")

# 3. 检查MinerU
print("\n[MinerU]")
try:
    result = subprocess.run(
        [sys.executable, "-m", "magic_pdf.cli", "--version"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        version = result.stdout.strip()
        print(f"  状态: 已安装")
        print(f"  版本: {version}")
    else:
        # 尝试CLI路径
        cli_path = Path(sys.executable).parent / "Scripts" / "magic-pdf.exe"
        if cli_path.exists():
            result = subprocess.run([str(cli_path), "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  状态: 已安装")
                print(f"  版本: {result.stdout.strip()}")
            else:
                print("  状态: 未找到")
        else:
            print("  状态: 未找到")
except Exception as e:
    print(f"  状态: 错误 - {e}")

# 4. 检查核心依赖
print("\n[核心依赖]")
dependencies = [
    "torch",
    "transformers", 
    "PyMuPDF",
    "scikit-learn",
    "numpy",
    "opencv-python",
]

for dep in dependencies:
    try:
        if dep == "opencv-python":
            import cv2
            print(f"  {dep}: {cv2.__version__}")
        else:
            module = __import__(dep.replace("-", "_").split("[")[0])
            version = getattr(module, "__version__", "已安装")
            print(f"  {dep}: {version}")
    except ImportError:
        print(f"  {dep}: 未安装")

# 5. 检查GPU
print("\n[GPU支持]")
try:
    import torch
    if torch.cuda.is_available():
        print(f"  CUDA: 可用")
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
        print(f"  显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    else:
        print("  CUDA: 不可用（将使用CPU）")
except Exception as e:
    print(f"  状态: {e}")

print("\n" + "=" * 60)
print("验证完成！")
print("=" * 60)

print("\n使用方法:")
print("  1. PDF工作流: python main.py pdf document.pdf -f docx")
print("  2. Word工作流: python main.py word document.docx")
print("  3. 批量处理: python main.py batch-pdf ./pdfs -f docx")
print("\n注意: 使用 start_conda.bat 启动会自动激活正确的环境")
