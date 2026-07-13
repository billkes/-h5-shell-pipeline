"""Tests for native launch veil / retry UI."""

from __future__ import annotations

import json
from pathlib import Path

from batch.native_launch_style import (
    collect_native_launch_ui_violations,
    launch_style_values,
    sync_oc_host_launch_ui,
)


def test_launch_style_reads_h5_css(tmp_path: Path) -> None:
    h5 = tmp_path / "h5" / "src" / "styles"
    h5.mkdir(parents=True)
    (h5 / "global.css").write_text(
        """
:root {
  --uhfnf-bg: #F5F5F7;
  --uhfnf-fg: #0F172A;
  --uhfnf-sheet: #FFFFFF;
  --uhfnf-on-muted: #64748B;
  --uhfnf-primary: #EA580C;
}
@media (prefers-color-scheme: dark) {
  :root {
    --uhfnf-bg: #0F172A;
    --uhfnf-fg: #FFFFFF;
    --uhfnf-sheet: rgba(32,28,39,0.88);
    --uhfnf-on-muted: #94A3B8;
    --uhfnf-primary: #EA580C;
  }
}
""",
        encoding="utf-8",
    )
    (tmp_path / "本包登记信息.json").write_text(
        json.dumps({"codeAntiCorrelation": {"dartCodePrefix": "uhfnf"}}),
        encoding="utf-8",
    )
    style = launch_style_values(tmp_path)
    assert style["{{LAUNCH_D_BG_B}}"].startswith("0.1")
    assert style["{{LAUNCH_L_BG_R}}"] > style["{{LAUNCH_D_BG_R}}"] or float(style["{{LAUNCH_L_BG_R}}"]) > float(
        style["{{LAUNCH_D_BG_R}}"]
    )


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
    assert "ApplyLaunchTheme" in text
    assert "LAUNCH_D_BG_R" not in text
    assert "Temioo offline" in text
