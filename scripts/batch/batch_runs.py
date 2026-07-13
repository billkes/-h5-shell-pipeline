"""Batch run metadata — replaces per-batch ``output/_batch-info.txt``."""

from __future__ import annotations

import json
import socket
from datetime import datetime
from pathlib import Path
from typing import Any


def batch_runs_path(registry_dir: Path) -> Path:
    return registry_dir / "batch-runs.json"


def _empty() -> dict[str, Any]:
    return {"runs": []}


def load_batch_runs(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _empty()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty()
    if not isinstance(data, dict):
        return _empty()
    runs = data.get("runs")
    if not isinstance(runs, list):
        data["runs"] = []
    return data


def write_batch_runs(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_batch_run(
    path: Path,
    *,
    batch_id: str,
    stamp: str,
    task_csv: str,
    app_names: list[str],
    output_dir: str,
    reports_dir: str,
    app_workspaces: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    data = load_batch_runs(path)
    runs = data.setdefault("runs", [])
    entry: dict[str, Any] = {
        "batchId": batch_id,
        "stamp": stamp,
        "startedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hostname": socket.gethostname() or "unknown",
        "taskCsv": task_csv,
        "outputDir": output_dir,
        "reportsDir": reports_dir,
        "apps": app_names,
        "runner": "batch-python",
    }
    if app_workspaces:
        entry["appWorkspaces"] = app_workspaces
    if isinstance(runs, list):
        runs.append(entry)
    write_batch_runs(path, data)
    return entry
