"""Tests for skill_ux_gate."""

from __future__ import annotations

import json
from pathlib import Path

from batch.skill_ux_gate import verify_skill_ux_gate


def test_verify_skill_ux_gate_detects_missing_reduced_motion(tmp_path: Path) -> None:
    site = tmp_path / "h5_site"
    site.mkdir()
    entry_name = "app_entry.htm"
    (site / entry_name).write_text(
        "<html><head><style>body{font-size:14px;}</style></head><body></body></html>",
        encoding="utf-8",
    )
    (tmp_path / "本包登记信息.json").write_text(
        json.dumps(
            {
                "h5SiteRoot": "h5_site",
                "h5SiteEntry": entry_name,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "design-system").mkdir()
    (tmp_path / "design-system" / "app").mkdir()
    (tmp_path / "design-system" / "app" / "ux-checklist.md").write_text("# ux", encoding="utf-8")
    issues = verify_skill_ux_gate(tmp_path)
    assert any("prefers-reduced-motion" in i for i in issues)
