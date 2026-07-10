"""Batch task manifest helpers."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class TaskManifest:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data: Dict[str, Any] = {
            "version": 1,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "tasks": {},
        }
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)
                self.data.setdefault("tasks", {})
        except Exception:
            pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data["updated_at"] = now_iso()
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def key_for(self, input_path: Path) -> str:
        return str(Path(input_path).resolve()).lower()

    def is_success(self, input_path: Path) -> bool:
        task = self.data.get("tasks", {}).get(self.key_for(input_path))
        return bool(task and task.get("status") == "success")

    def mark_running(self, input_path: Path, output_dir: Path, params: Optional[Dict[str, Any]] = None) -> None:
        self.data["tasks"][self.key_for(input_path)] = {
            "input": str(Path(input_path).resolve()),
            "output_dir": str(Path(output_dir).resolve()),
            "status": "running",
            "started_at": now_iso(),
            "params": params or {},
        }
        self.save()

    def mark_result(self, input_path: Path, result: Dict[str, Any]) -> None:
        key = self.key_for(input_path)
        task = self.data.setdefault("tasks", {}).setdefault(key, {"input": str(Path(input_path).resolve())})
        task.update({
            "status": "success" if result.get("success") else "failed",
            "finished_at": now_iso(),
            "outputs": result.get("outputs", {}),
            "errors": result.get("errors", []),
            "quality": result.get("quality"),
        })
        self.save()
