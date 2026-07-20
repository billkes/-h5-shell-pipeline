"""Tests for h5_theme_tokens system light/dark sync."""

from __future__ import annotations

import json
from pathlib import Path

from batch.h5_theme_tokens import (
    build_theme_block,
    normalize_css_imports,
    sync_h5_global_theme,
    verify_h5_theme_system,
)


def test_build_theme_block_has_light_and_dark() -> None:
    block = build_theme_block("demo", {"primary": "#EA580C", "background": "#0F172A", "foreground": "#FFF"})
    assert "color-scheme: light dark" in block
    assert "@media (prefers-color-scheme: dark)" in block
    assert "--demo-background: #F5F5F7" in block
    assert "--demo-foreground: #0F172A" in block
    assert "--demo-on-primary:" in block
    assert "--demo-on-ambient:" in block


def test_light_palette_rejects_dark_first_surfaces() -> None:
    """Dark-first candidate must not poison light:root (Monthio regression)."""
    block = build_theme_block(
        "cjsyi",
        {
            "primary": "#0F172A",
            "secondary": "#1E293B",
            "accent": "#16A34A",
            "background": "#020617",
            "foreground": "#F8FAFC",
            "muted": "#1A1E2F",
            "border": "#334155",
        },
    )
    light = block.split("@media")[0]
    assert "--cjsyi-background: #F5F5F7" in light
    assert "--cjsyi-foreground: #0F172A" in light
    assert "--cjsyi-muted: #E8EAED" in light
    assert "--cjsyi-secondary: #E2E8F0" in light
    assert "--cjsyi-border: rgba(15, 23, 42, 0.12)" in light
    # Explicit dark-first dict still keeps green accent when no MASTER override.
    assert "--cjsyi-accent: #16A34A" in light
    # Dark media still keeps dark surfaces.
    dark = block.split("@media")[1]
    assert "--cjsyi-background: #020617" in dark
    assert "--cjsyi-foreground: #F8FAFC" in dark


def test_sync_h5_global_theme(tmp_path: Path) -> None:
    (tmp_path / "h5" / "src" / "styles").mkdir(parents=True)
    (tmp_path / "skill-adapt").mkdir()
    (tmp_path / "本包登记信息.json").write_text(
        json.dumps({"codeAntiCorrelation": {"dartCodePrefix": "demo"}}),
        encoding="utf-8",
    )
    (tmp_path / "skill-adapt" / "selected-candidate.json").write_text(
        json.dumps({"designSystem": {"colors": {"primary": "#000", "background": "#111"}}}),
        encoding="utf-8",
    )
    css = tmp_path / "h5" / "src" / "styles" / "global.css"
    css.write_text(":root { --demo-bg: #000; }\n", encoding="utf-8")
    sync_h5_global_theme(tmp_path, write=True)
    text = css.read_text(encoding="utf-8")
    assert "prefers-color-scheme: dark" in text
    assert ".h5-app-shell" in text
    assert verify_h5_theme_system(tmp_path) == []


def test_normalize_css_imports_moves_misplaced_kit_and_fonts() -> None:
    """Agent often appends @import after :root — PostCSS then ignores kit.css."""
    from batch.h5_theme_tokens import _verify_css_import_order

    css = """:root {
  --demo-primary: #000;
}

@import url('https://fonts.googleapis.com/css2?family=Inter&display=swap');
@import './kit.css';

@tailwind base;
"""
    fixed = normalize_css_imports(css)
    lines = [ln.strip() for ln in fixed.splitlines() if ln.strip() and not ln.strip().startswith("/*")]
    assert lines[0].startswith("@import url(")
    assert lines[1] == "@import './kit.css';"
    assert lines[2].startswith(":root")
    assert _verify_css_import_order(fixed) == []
    assert _verify_css_import_order(css) != []
