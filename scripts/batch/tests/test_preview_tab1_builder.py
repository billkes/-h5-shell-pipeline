"""Tests for Tab1 preview HTML builder."""

from __future__ import annotations

import json
from pathlib import Path

from batch.preview_tab1_builder import build_tab1_preview_html, write_tab1_preview
from batch.preview_tabs import preview_canonical_path, preview_html_path, verify_preview_tabs_outputs

MASTER = """### Color Palette
| Primary | `#1E3A5F` | `--color-primary` |
| Accent/CTA | `#A16207` | `--color-accent` |
| Background | `#F8FAFC` | `--color-background` |
| Foreground | `#0F172A` | `--color-foreground` |
"""


def _scaffold_project(tmp_path: Path) -> Path:
    ds = tmp_path / "design-system" / "demo"
    ds.mkdir(parents=True)
    (ds / "MASTER.md").write_text(MASTER, encoding="utf-8")
    (tmp_path / "skill-adapt").mkdir()
    (tmp_path / "skill-adapt" / "selected-candidate.json").write_text(
        json.dumps({"designSystem": {"colors": {"primary": "#0F172A", "accent": "#16A34A"}}}),
        encoding="utf-8",
    )
    (tmp_path / "本包登记信息.json").write_text(
        json.dumps({"appName": "Demo", "codeAntiCorrelation": {"dartCodePrefix": "demo"}}),
        encoding="utf-8",
    )
    styles = tmp_path / "h5" / "src" / "styles"
    styles.mkdir(parents=True)
    (styles / "global.css").write_text(
        "/* THEME:pipeline */:root{--demo-primary:#1E3A5F;}/* THEME:end */\n"
        ":root { --demo-font-display: 'Outfit', sans-serif; }\n"
        ".c-demo-habit-tile { min-height: 80px; }\n",
        encoding="utf-8",
    )
    (styles / "kit.css").write_text(".c-demo-btn { min-height: 44px; }\n", encoding="utf-8")
    return tmp_path


def test_build_tab1_preview_html(tmp_path: Path) -> None:
    ws = _scaffold_project(tmp_path)
    html = build_tab1_preview_html(ws, "Demo")
    assert "Tab1 Canvas" in html
    assert "preview-light" in html
    assert "c-demo-habit-tile" in html
    assert "Canvas" in html


def test_write_tab1_preview(tmp_path: Path) -> None:
    ws = _scaffold_project(tmp_path)
    out = write_tab1_preview(ws, "Demo", write=True)
    assert out.name == "demo-tab1-preview.html"
    assert out.stat().st_size > 500
