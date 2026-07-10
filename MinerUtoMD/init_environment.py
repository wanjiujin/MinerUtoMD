"""One-click environment check and initialization for MinerUtoMD."""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - handled at runtime
    yaml = None


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "config.yaml"


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    if yaml is None:
        raise RuntimeError("缺少 PyYAML，请先运行: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def save_yaml(path: Path, data: Dict[str, Any]) -> None:
    if yaml is None:
        raise RuntimeError("缺少 PyYAML，请先运行: pip install pyyaml")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def existing_path(candidates: Iterable[Optional[str]]) -> Optional[str]:
    for candidate in candidates:
        if not candidate:
            continue
        p = Path(str(candidate).strip('"'))
        if p.exists():
            return str(p)
        found = shutil.which(str(candidate))
        if found:
            return found
    return None


def run_version(command: list[str]) -> Dict[str, Any]:
    executable = command[0]
    if not existing_path([executable]):
        return {"ok": False, "detail": f"未找到命令: {executable}"}
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        text = (result.stdout or result.stderr or "").strip().splitlines()
        return {"ok": result.returncode == 0, "detail": text[0] if text else ""}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}


def detect_python(config: Dict[str, Any]) -> Optional[str]:
    mineru_cfg = config.get("mineru", {})
    env_python = os.environ.get("MINERUTOMD_PYTHON") or os.environ.get("MINERU_PYTHON")
    candidates = [
        mineru_cfg.get("python_exe"),
        mineru_cfg.get("python_v3"),
        env_python,
        r"D:\CDriveMoved\miniforge3\envs\mineru2\python.exe",
        r"D:\CDriveMoved\miniforge3\envs\mineru\python.exe",
        sys.executable,
    ]
    return existing_path(candidates)


def detect_cli(config: Dict[str, Any]) -> Dict[str, Optional[str]]:
    mineru_cfg = config.get("mineru", {})
    return {
        "mineru": existing_path([
            mineru_cfg.get("mineru_cli_v3"),
            "mineru",
            r"D:\CDriveMoved\miniforge3\envs\mineru2\Scripts\mineru.exe",
        ]),
        "magic_pdf": existing_path([
            mineru_cfg.get("mineru_cli_v1"),
            "magic-pdf",
            r"D:\CDriveMoved\miniforge3\envs\mineru\Scripts\magic-pdf.exe",
        ]),
    }


def detect_pandoc(config: Dict[str, Any]) -> Optional[str]:
    pandoc_cfg = config.get("pandoc", {})
    return existing_path([
        pandoc_cfg.get("path"),
        "pandoc",
        r"D:\CDriveMoved\miniforge3\envs\mineru2\Library\bin\pandoc.exe",
    ])


def detect_pdf_engine(config: Dict[str, Any]) -> Optional[str]:
    pandoc_cfg = config.get("pandoc", {})
    return existing_path([
        pandoc_cfg.get("pdf_engine"),
        "wkhtmltopdf",
        r"D:\CDriveMoved\miniforge3\envs\mineru2\Library\bin\wkhtmltopdf.exe",
    ])


def detect_model_cache(config: Dict[str, Any]) -> Dict[str, Optional[str]]:
    mineru_cfg = config.get("mineru", {})
    hf_home = existing_path([
        mineru_cfg.get("hf_home"),
        os.environ.get("HF_HOME"),
        ROOT / "models" / "hf_cache",
        r"D:\CDriveMoved\hf_cache",
    ])
    hf_hub_cache = existing_path([
        mineru_cfg.get("hf_hub_cache"),
        os.environ.get("HF_HUB_CACHE"),
        Path(hf_home) / "hub" if hf_home else None,
    ])
    local_model_config = existing_path([
        mineru_cfg.get("mineru_tools_config_json"),
        ROOT / "mineru_local_models.json",
    ])
    return {
        "hf_home": hf_home,
        "hf_hub_cache": hf_hub_cache,
        "mineru_tools_config_json": local_model_config,
    }


def detect_all(config: Dict[str, Any]) -> Dict[str, Any]:
    python_exe = detect_python(config)
    cli = detect_cli(config)
    pandoc = detect_pandoc(config)
    pdf_engine = detect_pdf_engine(config)
    model_cache = detect_model_cache(config)

    return {
        "python_exe": python_exe,
        "mineru_cli": cli,
        "pandoc": pandoc,
        "pdf_engine": pdf_engine,
        "model_cache": model_cache,
        "versions": {
            "python": run_version([python_exe or "python", "--version"]),
            "pandoc": run_version([pandoc or "pandoc", "--version"]),
            "pdf_engine": run_version([pdf_engine or "wkhtmltopdf", "--version"]),
        },
    }


def update_config(config: Dict[str, Any], detected: Dict[str, Any]) -> Dict[str, Any]:
    updated = copy.deepcopy(config)
    mineru_cfg = updated.setdefault("mineru", {})
    pandoc_cfg = updated.setdefault("pandoc", {})

    if detected.get("python_exe"):
        mineru_cfg["python_exe"] = detected["python_exe"]
    if detected["mineru_cli"].get("mineru"):
        mineru_cfg["mineru_cli_v3"] = detected["mineru_cli"]["mineru"]
    if detected["mineru_cli"].get("magic_pdf"):
        mineru_cfg["mineru_cli_v1"] = detected["mineru_cli"]["magic_pdf"]

    cache = detected.get("model_cache", {})
    for key in ("hf_home", "hf_hub_cache", "mineru_tools_config_json"):
        if cache.get(key):
            mineru_cfg[key] = cache[key]
    if cache.get("mineru_tools_config_json"):
        mineru_cfg["model_source"] = "local"

    if detected.get("pandoc"):
        pandoc_cfg["path"] = detected["pandoc"]
    if detected.get("pdf_engine"):
        pandoc_cfg["pdf_engine"] = detected["pdf_engine"]

    return updated


def print_report(detected: Dict[str, Any]) -> None:
    checks = [
        ("Python", detected.get("python_exe"), detected["versions"]["python"]),
        ("MinerU CLI", detected["mineru_cli"].get("mineru") or detected["mineru_cli"].get("magic_pdf"), None),
        ("Pandoc", detected.get("pandoc"), detected["versions"]["pandoc"]),
        ("PDF 引擎", detected.get("pdf_engine"), detected["versions"]["pdf_engine"]),
        ("HF_HOME", detected["model_cache"].get("hf_home"), None),
        ("HF_HUB_CACHE", detected["model_cache"].get("hf_hub_cache"), None),
        ("本地模型配置", detected["model_cache"].get("mineru_tools_config_json"), None),
    ]

    print("MinerUtoMD 环境检查")
    print("=" * 60)
    for name, path, version in checks:
        ok = bool(path)
        mark = "OK" if ok else "MISS"
        detail = f" -> {path}" if path else ""
        if version:
            detail += f" ({version.get('detail', '')})"
        print(f"[{mark}] {name}{detail}")

    print("\n建议")
    if not detected.get("pandoc"):
        print("- 未找到 Pandoc：请安装 Pandoc，或把 pandoc.exe 绝对路径写入 config.yaml。")
    if not detected.get("pdf_engine"):
        print("- 未找到 wkhtmltopdf：需要导出 PDF 时请安装 wkhtmltopdf，或改用 xelatex/weasyprint。")
    if not (detected["mineru_cli"].get("mineru") or detected["mineru_cli"].get("magic_pdf")):
        print("- 未找到 MinerU CLI：请在当前 Python 环境安装 MinerU，并确认 mineru/magic-pdf 可执行。")
    print("- 检查通过后可运行: python MinerUtoMD/main.py doctor")


def main() -> int:
    parser = argparse.ArgumentParser(description="MinerUtoMD 一键环境检查/初始化")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="读取的配置文件路径")
    parser.add_argument("--output-config", default=None, help="写出的配置文件路径，默认覆盖 --config")
    parser.add_argument("--write-config", action="store_true", help="把自动探测到的路径写入配置文件")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出检测结果")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    output_path = Path(args.output_config).resolve() if args.output_config else config_path
    config = load_yaml(config_path)
    detected = detect_all(config)

    if args.json:
        print(json.dumps(detected, ensure_ascii=False, indent=2))
    else:
        print_report(detected)

    if args.write_config:
        updated = update_config(config, detected)
        if output_path.exists() and output_path == config_path:
            backup = output_path.with_name(f"{output_path.name}.bak_{datetime.now():%Y%m%d_%H%M%S}")
            shutil.copy2(output_path, backup)
            print(f"\n已备份原配置: {backup}")
        save_yaml(output_path, updated)
        print(f"已写入本机配置: {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
