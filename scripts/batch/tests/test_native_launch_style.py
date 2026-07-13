"""Tests for native launch veil / retry UI."""

from __future__ import annotations

import json
from pathlib import Path

from batch.native_launch_style import (
    collect_native_launch_ui_violations,
    launch_style_values,
    sync_oc_host_launch_ui,
)


def test_launch_style_reads_visual_lock(tmp_path: Path) -> None:
    (tmp_path / "本包视觉锁.json").write_text(
        json.dumps(
            {
                "colorTokens": {
                    "primary": "#EA580C",
                    "accent": "#059669",
                    "backgroundDark": "#0F172A",
                }
            }
        ),
        encoding="utf-8",
    )
    style = launch_style_values(tmp_path)
    assert style["{{LAUNCH_PRIMARY_R}}"].startswith("0.9")
    assert style["{{LAUNCH_BG_B}}"].startswith("0.1")


def test_collect_native_launch_ui_violations_flags_generic_copy(tmp_path: Path) -> None:
    host = tmp_path / "Demo" / "DemoHostController.m"
    host.parent.mkdir(parents=True)
    host.write_text('@property UIActivityIndicatorView *demoVeilSpinner;\nConnection issue\n', encoding="utf-8")
    issues = collect_native_launch_ui_violations(tmp_path)
    assert issues


def test_sync_oc_host_launch_ui_writes_branded_host(tmp_path: Path) -> None:
    reg = {
        "appName": "Temioo",
        "packType": "h5_oc_shell",
        "codeAntiCorrelation": {"dartCodePrefix": "uhfnf"},
    }
    (tmp_path / "本包登记信息.json").write_text(json.dumps(reg), encoding="utf-8")
    (tmp_path / "本包视觉锁.json").write_text(
        json.dumps({"colorTokens": {"primary": "#EA580C", "backgroundDark": "#0F172A", "accent": "#059669"}}),
        encoding="utf-8",
    )
    stale = tmp_path / "Temioo" / "UhfnfHostController.m"
    stale.parent.mkdir(parents=True)
    stale.write_text("Connection issue\nVeilSpinner\n", encoding="utf-8")
    out = sync_oc_host_launch_ui(tmp_path, write=True)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "VeilCaption" in text
    assert "Connection issue" not in text
    assert "Temioo offline" in text
