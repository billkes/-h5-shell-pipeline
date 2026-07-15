"""Batch output directory naming — flat layout with centralized reports."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from batch.task_schema import reports_dir


def make_batch_stamp(when: datetime | None = None) -> str:
    """Wall-clock stamp unique per process (second + PID) for concurrent batch runs."""
    moment = when or datetime.now()
    return moment.strftime("%Y-%m-%d_%H-%M-%S") + f"-{os.getpid()}"


def ensure_output_layout(output_root: Path) -> Path:
    """Ensure flat ``output/`` and ``output/_reports/`` exist."""
    output_root.mkdir(parents=True, exist_ok=True)
    reports_dir(output_root).mkdir(parents=True, exist_ok=True)
    return output_root.resolve()


def report_paths(
    output_root: Path,
    *,
    batch_id: str,
    stamp: str,
) -> tuple[Path, Path]:
    """Return (detailed_log, batch_report) under ``output/_reports/``."""
    rep = reports_dir(output_root)
    rep.mkdir(parents=True, exist_ok=True)
    tag = f"{stamp}-{batch_id}" if batch_id else stamp
    return (
        rep / f"{tag}详细日志.md",
        rep / f"{tag}_batch-report.md",
    )
