"""Batch output directory naming — flat layout with centralized reports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from batch.task_schema import reports_dir


def make_batch_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M")


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
