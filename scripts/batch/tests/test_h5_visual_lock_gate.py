"""Tests for post-delivery visual lock gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS))

from batch.h5_visual_lock_gate import collect_h5_visual_lock_violations  # noqa: E402


def _write_lock(ws: Path) -> None:
    (ws / "本包视觉锁.json").write_text(
        json.dumps(
            {
                "designerDeckSelections": {
                    "headingFont": "Calistoga",
                    "bodyFont": "Inter",
                },
                "colorTokens": {
                    "primary": "#EA580C",
                    "backgroundDark": "#120E0C",
                    "background": "#FFFBF7",
                },
                "componentSelection": ["shell/top_bar", "feedback/snackbar"],
                "ambientCanvas": {
                    "motifKey": "warm-grid",
                    "scenes": {"hub": "hub", "splash": "splash"},
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _write_css(ws: Path, *, primary: str = "#EA580C", dark_bg: str = "#120E0C") -> None:
    css_dir = ws / "h5" / "src" / "styles"
    css_dir.mkdir(parents=True)
    (css_dir / "global.css").write_text(
        f"""
/* THEME:pipeline — auto-synced; do not hand-edit */
:root {{
  color-scheme: light dark;
  --demo-primary: {primary};
  --demo-bg: #FFFBF7;
  --demo-fg: #431407;
  --demo-background: #FFFBF7;
  --demo-foreground: #431407;
  --demo-on-primary: #FFFFFF;
  --demo-on-ambient: #431407;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --demo-primary: {primary};
    --demo-bg: {dark_bg};
    --demo-fg: #FFFFFF;
    --demo-background: {dark_bg};
    --demo-foreground: #FFFFFF;
    --demo-on-primary: #FFFFFF;
    --demo-on-ambient: #FFFFFF;
  }}
}}
/* THEME:end */
.h5-app-shell {{ min-height: 100vh; }}
""",
        encoding="utf-8",
    )


def test_visual_lock_passes_when_css_matches(tmp_path: Path) -> None:
    ws = tmp_path / "App"
    (ws / "h5" / "src").mkdir(parents=True)
    (ws / "本包登记信息.json").write_text(
        json.dumps({"codeAntiCorrelation": {"dartCodePrefix": "demo"}}),
        encoding="utf-8",
    )
    _write_lock(ws)
    _write_css(ws)
    (ws / "h5" / "src" / "App.vue").write_text(
        '<script setup>\nfunction setAmbientScene() {}\n</script>\n<div class="u-demo-ambient"></div>\n',
        encoding="utf-8",
    )
    (ws / "h5" / "index.html").write_text(
        '<link href="https://fonts.googleapis.com/css?family=Calistoga">\n'
        '<link href="https://fonts.googleapis.com/css?family=Inter">\n',
        encoding="utf-8",
    )
    issues = collect_h5_visual_lock_violations(ws)
    assert issues == []


def test_visual_lock_flags_primary_drift(tmp_path: Path) -> None:
    ws = tmp_path / "App"
    (ws / "h5" / "src").mkdir(parents=True)
    (ws / "本包登记信息.json").write_text(
        json.dumps({"codeAntiCorrelation": {"dartCodePrefix": "demo"}}),
        encoding="utf-8",
    )
    _write_lock(ws)
    _write_css(ws, primary="#2563EB")
    (ws / "h5" / "src" / "App.vue").write_text("setAmbientScene\n", encoding="utf-8")
    issues = collect_h5_visual_lock_violations(ws)
    assert any("primary" in i and "不一致" in i for i in issues)


def test_visual_lock_requires_lock_file(tmp_path: Path) -> None:
    ws = tmp_path / "App"
    (ws / "h5" / "src").mkdir(parents=True)
    issues = collect_h5_visual_lock_violations(ws)
    assert any("缺少 本包视觉锁.json" in i for i in issues)
