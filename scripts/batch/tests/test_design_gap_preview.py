"""Tests for MASTER palette parsing and design gap preview."""

from __future__ import annotations

import json
from pathlib import Path

from batch.design_gap_preview import analyze_design_gap, write_design_gap_preview
from batch.h5_theme_tokens import build_theme_block, sync_h5_global_theme
from batch.uupm_design_system import parse_master_palette, parse_master_typography

MASTER_SAMPLE = """# Design System Master File

### Color Palette

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary | `#1E3A5F` | `--color-primary` |
| Accent/CTA | `#A16207` | `--color-accent` |
| Background | `#F8FAFC` | `--color-background` |
| Foreground | `#0F172A` | `--color-foreground` |
| Muted | `#E9EEF5` | `--color-muted` |

### Typography

- **Heading Font:** Outfit
- **Body Font:** Outfit

```css
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&display=swap');
```
"""


def test_parse_master_palette() -> None:
    colors = parse_master_palette(MASTER_SAMPLE)
    assert colors["primary"] == "#1E3A5F"
    assert colors["accent"] == "#A16207"
    assert colors["background"] == "#F8FAFC"


def test_parse_master_typography() -> None:
    typo = parse_master_typography(MASTER_SAMPLE)
    assert typo["heading"] == "Outfit"
    assert "fonts.googleapis.com" in typo.get("google_fonts_url", "")


def test_build_theme_block_prefers_master_over_dark_candidate(tmp_path: Path) -> None:
    ds = tmp_path / "design-system" / "demo"
    ds.mkdir(parents=True)
    (ds / "MASTER.md").write_text(MASTER_SAMPLE, encoding="utf-8")
    (tmp_path / "skill-adapt").mkdir()
    (tmp_path / "skill-adapt" / "selected-candidate.json").write_text(
        json.dumps(
            {
                "designSystem": {
                    "colors": {
                        "primary": "#0F172A",
                        "accent": "#16A34A",
                        "background": "#020617",
                        "foreground": "#F8FAFC",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "本包登记信息.json").write_text(
        json.dumps({"codeAntiCorrelation": {"dartCodePrefix": "demo"}}),
        encoding="utf-8",
    )
    block = build_theme_block("demo", project=tmp_path)
    light = block.split("@media")[0]
    assert "--demo-primary: #1E3A5F" in light
    assert "--demo-accent: #A16207" in light
    assert "--demo-background: #F8FAFC" in light


def test_sync_injects_font_vars_from_master(tmp_path: Path) -> None:
    ds = tmp_path / "design-system" / "demo"
    ds.mkdir(parents=True)
    (ds / "MASTER.md").write_text(MASTER_SAMPLE, encoding="utf-8")
    (tmp_path / "skill-adapt").mkdir()
    (tmp_path / "skill-adapt" / "selected-candidate.json").write_text(
        json.dumps({"designSystem": {"colors": {"primary": "#000"}}}),
        encoding="utf-8",
    )
    (tmp_path / "本包登记信息.json").write_text(
        json.dumps({"codeAntiCorrelation": {"dartCodePrefix": "demo"}}),
        encoding="utf-8",
    )
    styles = tmp_path / "h5" / "src" / "styles"
    styles.mkdir(parents=True)
    css = styles / "global.css"
    css.write_text(
        ":root {}\n.page { font-family: var(--demo-font-display); }\n",
        encoding="utf-8",
    )
    sync_h5_global_theme(tmp_path, write=True)
    text = css.read_text(encoding="utf-8")
    assert "--demo-font-display: 'Outfit', sans-serif;" in text
    assert "fonts.googleapis.com" in text


def test_design_gap_preview_writes_html(tmp_path: Path) -> None:
    ds = tmp_path / "design-system" / "demo"
    ds.mkdir(parents=True)
    (ds / "MASTER.md").write_text(MASTER_SAMPLE, encoding="utf-8")
    (tmp_path / "skill-adapt").mkdir()
    (tmp_path / "skill-adapt" / "selected-candidate.json").write_text(
        json.dumps({"designSystem": {"colors": {"accent": "#16A34A"}}}),
        encoding="utf-8",
    )
    (tmp_path / "本包登记信息.json").write_text(
        json.dumps({"codeAntiCorrelation": {"dartCodePrefix": "demo"}}),
        encoding="utf-8",
    )
    styles = tmp_path / "h5" / "src" / "styles"
    styles.mkdir(parents=True)
    (styles / "global.css").write_text(
        ":root { --demo-accent: #16A34A; --demo-primary: #0F172A; }\n",
        encoding="utf-8",
    )
    (styles / "kit.css").write_text(".c-demo-btn { background: #16A34A; }\n", encoding="utf-8")
    out = write_design_gap_preview(tmp_path, write=True)
    assert out.is_file()
    html = out.read_text(encoding="utf-8")
    assert "MASTER" in html
    assert "Pipeline" in html
    report = analyze_design_gap(tmp_path)
    assert report["master_palette"].get("accent") == "#A16207"
