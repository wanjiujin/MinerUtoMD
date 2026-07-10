"""Output quality checks for MinerUtoMD conversions."""
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)|<img\s+[^>]*src=[\"']([^\"']+)[\"']", re.IGNORECASE)


def _clean_image_ref(ref: str) -> str:
    ref = ref.strip()
    if " " in ref and not Path(ref).exists():
        ref = ref.split(" ", 1)[0]
    return ref.strip("\"'")


def check_markdown_images(md_path: Path) -> Dict[str, Any]:
    missing = []
    refs = []
    try:
        content = md_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {"ok": False, "error": str(exc), "image_refs": [], "missing_images": []}

    for match in IMAGE_PATTERN.finditer(content):
        ref = _clean_image_ref(match.group(1) or match.group(2) or "")
        if not ref or ref.startswith(("http://", "https://", "data:")):
            continue
        refs.append(ref)
        image_path = (md_path.parent / ref).resolve()
        if not image_path.exists():
            missing.append(ref)

    return {
        "ok": not missing,
        "image_refs": refs,
        "missing_images": missing,
    }


def check_outputs(
    outputs: Dict[str, str],
    output_dir: Optional[str] = None,
    write_report: bool = False,
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    ok = True

    for fmt, path_text in outputs.items():
        path = Path(path_text)
        exists = path.exists()
        is_file = path.is_file()
        size = path.stat().st_size if exists and is_file else None
        item = {
            "format": fmt,
            "path": str(path),
            "exists": exists,
            "size": size,
            "ok": bool(exists and (not is_file or (size is not None and size > 0))),
        }
        if fmt == "md" and exists and is_file:
            item["markdown_images"] = check_markdown_images(path)
            item["ok"] = item["ok"] and item["markdown_images"]["ok"]
        checks.append(item)
        ok = ok and item["ok"]

    report = {"ok": ok, "checks": checks}
    if output_dir and write_report:
        report_path = Path(output_dir) / "conversion_report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["report_path"] = str(report_path)
    return report
