"""Tests for preview.tabs artifacts and theme truth source."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS))

from batch.h5_theme_tokens import _load_candidate_colors  # noqa: E402
from batch.preview_tabs import (  # noqa: E402
    preview_canonical_path,
    preview_html_path,
    verify_preview_tabs_outputs,
)


def test_verify_preview_tabs_outputs_missing() -> None:
    td = Path(tempfile.mkdtemp())
    ws = td / "App"
    ws.mkdir()
    issues = verify_preview_tabs_outputs(ws, "Rolioo")
    assert any("rolioo-tabs-preview.html" in i for i in issues)
    assert any("preview-canonical.md" in i for i in issues)


def test_verify_preview_tabs_outputs_ok() -> None:
    td = Path(tempfile.mkdtemp())
    ws = td / "App"
    ws.mkdir()
    html = preview_html_path(ws, "Rolioo")
    html.parent.mkdir(parents=True, exist_ok=True)
    html.write_text(
        "<html><style>@media (prefers-color-scheme: dark){}</style>"
        + "x" * 600
        + "</html>",
        encoding="utf-8",
    )
    canonical = preview_canonical_path(ws)
    canonical.write_text(
        "## Tabs\n| Home | #/hub | main |\n\n"
        "## Colors\n"
        "### Light mode\n| background | `#FFFBF7` |\n| primary | `#EA580C` |\n\n"
        "### Dark mode\n| background | `#120E0C` |\n| primary | `#FB923C` |\n\n"
        "## Typography\nCalistoga\n\n"
        "## Key Components\nhero\n\n"
        "## Allowed MASTER Deviations\nwarm palette\n",
        encoding="utf-8",
    )
    (ws / "skill-adapt").mkdir(parents=True)
    (ws / "skill-adapt" / "preview-approved-colors.json").write_text(
        json.dumps(
            {
                "light": {"primary": "#EA580C", "background": "#FFFBF7"},
                "dark": {"primary": "#FB923C", "background": "#120E0C"},
            }
        ),
        encoding="utf-8",
    )
    assert verify_preview_tabs_outputs(ws, "Rolioo") == []


def test_preview_approved_light_dark_format() -> None:
    td = Path(tempfile.mkdtemp())
    ws = td / "App"
    adapt = ws / "skill-adapt"
    adapt.mkdir(parents=True)
    (adapt / "preview-approved-colors.json").write_text(
        json.dumps(
            {
                "light": {"primary": "#EA580C", "background": "#FFFBF7", "foreground": "#431407"},
                "dark": {"primary": "#FB923C", "background": "#120E0C"},
            }
        ),
        encoding="utf-8",
    )
    colors = _load_candidate_colors(ws)
    assert colors["primary"] == "#EA580C"
    assert colors["background"] == "#FFFBF7"


def test_preview_approved_colors_override_candidate() -> None:
    td = Path(tempfile.mkdtemp())
    ws = td / "App"
    adapt = ws / "skill-adapt"
    adapt.mkdir(parents=True)
    (adapt / "selected-candidate.json").write_text(
        json.dumps({"designSystem": {"colors": {"primary": "#111111"}}}),
        encoding="utf-8",
    )
    (adapt / "preview-approved-colors.json").write_text(
        json.dumps({"colors": {"primary": "#EA580C", "background": "#FFF7ED"}}),
        encoding="utf-8",
    )
    colors = _load_candidate_colors(ws)
    assert colors["primary"] == "#EA580C"
    assert colors["background"] == "#FFF7ED"
