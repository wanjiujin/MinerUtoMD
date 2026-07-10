#!/usr/bin/env python3
"""Download MinerU models from HuggingFace.

This project previously contained an HTML 404 page under this filename.  The
script below keeps a small, valid entry point that delegates to MinerU when the
installed version exposes a model download module.
"""
import os
import runpy
import sys
from pathlib import Path


DEFAULT_HF_ENDPOINT = "https://hf-mirror.com"
DEFAULT_HF_HOME = "D:/CDriveMoved/hf_cache" if sys.platform == "win32" else str(Path.home() / ".cache" / "huggingface")


def configure_environment() -> None:
    os.environ.setdefault("HF_ENDPOINT", DEFAULT_HF_ENDPOINT)
    os.environ.setdefault("HF_HOME", DEFAULT_HF_HOME)


def main() -> int:
    configure_environment()

    candidates = [
        "mineru.cli.models_download",
        "mineru.cli.download_models",
        "magic_pdf.tools.download_models",
    ]

    errors = []
    for module_name in candidates:
        try:
            runpy.run_module(module_name, run_name="__main__")
            return 0
        except ModuleNotFoundError as exc:
            errors.append(f"{module_name}: {exc}")
        except Exception as exc:
            errors.append(f"{module_name}: {exc}")

    print("未找到可用的 MinerU 模型下载入口。")
    print("请先安装 MinerU，例如：pip install mineru[full]")
    print("已尝试：")
    for error in errors:
        print(f"  - {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
