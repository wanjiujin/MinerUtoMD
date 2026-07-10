"""Environment diagnostics for MinerUtoMD."""
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from .mineru_extractor import MinerUExtractor, SUBPROCESS_FLAGS
    from .pandoc_converter import PandocConverter
except ImportError:
    from mineru_extractor import MinerUExtractor, SUBPROCESS_FLAGS
    from pandoc_converter import PandocConverter


def _path_status(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {"path": None, "exists": False}
    p = Path(path)
    return {"path": str(p), "exists": p.exists(), "is_dir": p.is_dir()}


def _run_version(command) -> Dict[str, Any]:
    executable = command[0]
    if not Path(executable).exists() and shutil.which(executable) is None:
        return {"ok": False, "error": f"command not found: {executable}"}

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            creationflags=SUBPROCESS_FLAGS,
        )
        text = (result.stdout or result.stderr or "").strip()
        return {"ok": result.returncode == 0, "returncode": result.returncode, "output": text[:500]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def diagnose_environment(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    config = config or {}
    mineru_config = config.get("mineru", {})
    pandoc_config = config.get("pandoc", {}).copy()
    if "path" in pandoc_config:
        pandoc_config["pandoc_path"] = pandoc_config["path"]

    mineru = MinerUExtractor(mineru_config)
    pandoc = PandocConverter(pandoc_config)

    mineru_tools_config = mineru_config.get("mineru_tools_config_json")
    local_model_config = None
    if mineru_tools_config and Path(mineru_tools_config).exists():
        try:
            local_model_config = json.loads(Path(mineru_tools_config).read_text(encoding="utf-8"))
        except Exception as exc:
            local_model_config = {"error": str(exc)}

    gpu_info = MinerUExtractor.detect_gpu(mineru.python_exe or sys.executable)
    pandoc_error = None
    try:
        pandoc_ok = pandoc.check_installation()
    except Exception as exc:
        pandoc_ok = False
        pandoc_error = str(exc)

    return {
        "mineru": {
            "ok": mineru.check_installation(),
            "version_family": mineru.version,
            "python": _path_status(mineru.python_exe),
            "cli": _path_status(mineru.cli_path),
            "device": mineru.device,
            "model_source": mineru_config.get("model_source", "huggingface"),
            "mineru_tools_config_json": _path_status(mineru_tools_config),
            "local_model_config": local_model_config,
            "hf_home": _path_status(mineru_config.get("hf_home")),
            "hf_hub_cache": _path_status(mineru_config.get("hf_hub_cache")),
        },
        "gpu": gpu_info,
        "pandoc": {
            "ok": pandoc_ok,
            "error": pandoc_error,
            "path": _path_status(pandoc.pandoc_path),
            "version": _run_version([pandoc.pandoc_path, "--version"]),
        },
    }


def flatten_diagnostics(report: Dict[str, Any]):
    rows = []

    def add(name, ok, detail=""):
        rows.append({"name": name, "ok": bool(ok), "detail": detail})

    mineru = report.get("mineru", {})
    add("MinerU", mineru.get("ok"), f"version={mineru.get('version_family')} python={mineru.get('python', {}).get('path')}")
    add("MinerU CLI", mineru.get("cli", {}).get("exists"), mineru.get("cli", {}).get("path"))
    add("Model source", mineru.get("model_source") != "local" or mineru.get("mineru_tools_config_json", {}).get("exists"), mineru.get("model_source"))
    add("HF cache", mineru.get("hf_hub_cache", {}).get("exists"), mineru.get("hf_hub_cache", {}).get("path"))

    gpu = report.get("gpu", {})
    add("CUDA", gpu.get("has_cuda"), gpu.get("device_name") or gpu.get("error") or "")

    pandoc = report.get("pandoc", {})
    add("Pandoc", pandoc.get("ok"), pandoc.get("path", {}).get("path"))

    return rows
