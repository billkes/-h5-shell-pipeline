"""Batch stamp uniqueness for concurrent runs."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from batch.batch_tag import make_batch_stamp, report_paths


def test_make_batch_stamp_includes_seconds_and_pid() -> None:
    when = datetime(2026, 7, 15, 12, 3, 43)
    stamp = make_batch_stamp(when)
    assert stamp.startswith("2026-07-15_12-03-43-")
    assert stamp.endswith(f"-{os.getpid()}")


def test_report_paths_use_unique_stamp(tmp_path: Path) -> None:
    stamp = make_batch_stamp(datetime(2026, 7, 15, 12, 3, 43))
    log_path, report_path = report_paths(
        tmp_path, batch_id="TEST-0714", stamp=stamp
    )
    assert log_path.name == f"{stamp}-TEST-0714详细日志.md"
    assert report_path.name == f"{stamp}-TEST-0714_batch-report.md"
    assert log_path.parent.name == "_reports"
