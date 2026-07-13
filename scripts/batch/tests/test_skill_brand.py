"""Tests for skill_brand."""

from __future__ import annotations

import json
from pathlib import Path

from batch.config import BatchConfig
from batch.skill_brand import brand_check_warnings, run_brand_check


def test_run_brand_check_writes_json(tmp_path: Path) -> None:
    cfg = BatchConfig()
    out = run_brand_check(cfg=cfg, workspace=tmp_path)
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["status"] == "ok"
    assert brand_check_warnings(tmp_path) == []
