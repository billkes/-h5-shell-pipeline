"""Tests for skill-factory Tab1 preview (MASTER only)."""

from __future__ import annotations

import json
from pathlib import Path

from batch.preview_skill_tab1 import build_skill_factory_tab1_html, write_skill_tab1_preview

MASTER = """# Design System Master File
### Color Palette
| Primary | `#1E3A5F` | `--color-primary` |
| Accent/CTA | `#A16207` | `--color-accent` |
| Background | `#F8FAFC` | `--color-background` |
| Foreground | `#0F172A` | `--color-foreground` |
| Muted | `#E9EEF5` | `--color-muted` |
| Border | `#CBD5E1` | `--color-border` |
### Typography
- **Heading Font:** Outfit
- **Body Font:** Outfit
```css
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&display=swap');
```
### Shadow Depths
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.1)` | Cards |
### Spacing Variables
| `--space-md` | `16px` | Standard |
| `--space-sm` | `8px` | Inline |
"""


def test_skill_tab1_preview_from_master_only(tmp_path: Path) -> None:
    ds = tmp_path / "design-system" / "demo"
    ds.mkdir(parents=True)
    (ds / "MASTER.md").write_text(MASTER, encoding="utf-8")
    (tmp_path / "本包登记信息.json").write_text(
        json.dumps({"appName": "Demo"}),
        encoding="utf-8",
    )
    html = build_skill_factory_tab1_html(tmp_path, "Demo")
    assert "PREVIEW-IMPL:skill-factory" in html
    assert "btn-primary" in html
    assert "#A16207" in html or "A16207" in html
    assert "Morning run" in html
    assert "kit.css" not in html
    assert "c-demo-" not in html

    out = write_skill_tab1_preview(tmp_path, "Demo", write=True)
    assert out.is_file()
    assert "demo-tab1-preview.html" in out.name
