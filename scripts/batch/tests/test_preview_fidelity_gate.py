"""Tests for preview fidelity gate."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS))

from batch.h5_page_scaffold import sync_h5_page_scaffold  # noqa: E402
from batch.preview_fidelity_gate import (  # noqa: E402
    PREVIEW_IMPL_LOCK,
    parse_colors_from_canonical,
    sync_preview_approved_colors_from_canonical,
    verify_preview_approved_colors,
)
from batch.preview_tabs import preview_canonical_path, preview_html_path  # noqa: E402


def _canonical_body() -> str:
    return (
        "## Tabs\n| Home | #/hub | main |\n\n"
        "## Colors\n"
        "### Light mode\n| background | `#FFFBF7` |\n| primary | `#EA580C` |\n\n"
        "### Dark mode\n| background | `#120E0C` |\n| primary | `#FB923C` |\n\n"
        "## Typography\nCalistoga\n\n"
        "## Key Components\nhero\n\n"
        "## Allowed MASTER Deviations\nwarm\n"
    )


def test_parse_and_sync_preview_colors() -> None:
    td = Path(tempfile.mkdtemp())
    ws = td / "App"
    (ws / "skill-adapt").mkdir(parents=True)
    (ws / "_preview").mkdir(parents=True)
    preview_canonical_path(ws).write_text(_canonical_body(), encoding="utf-8")
    parsed = parse_colors_from_canonical(ws)
    assert parsed["light"]["primary"] == "#EA580C"
    assert parsed["dark"]["primary"] == "#FB923C"
    out = sync_preview_approved_colors_from_canonical(ws, write=True)
    assert out is not None
    assert verify_preview_approved_colors(ws) == []


def test_scaffold_skips_preview_locked_hub(tmp_path: Path) -> None:
    project = tmp_path / "PreviewApp"
    src = project / "h5" / "src"
    (src / "router").mkdir(parents=True)
    (src / "views").mkdir(parents=True)
    (src / "styles").mkdir(parents=True)
    (project / "h5" / "package.json").write_text("{}", encoding="utf-8")
    (project / "h5" / "vite.config.ts").write_text("export default {}\n", encoding="utf-8")
    (project / "本包登记信息.json").write_text(
        '{"packType":"h5_swift_shell","codeAntiCorrelation":{"dartCodePrefix":"demo"}}',
        encoding="utf-8",
    )
    (src / "styles" / "global.css").write_text(":root {}\n", encoding="utf-8")
    (src / "router" / "index.ts").write_text(
        "import HubView from '../views/HubView.vue';\n"
        "export const routes = [{ path: '/hub', component: HubView }];\n",
        encoding="utf-8",
    )
    html = preview_html_path(project, "PreviewApp")
    html.parent.mkdir(parents=True, exist_ok=True)
    html.write_text("<html><style>@media (prefers-color-scheme: dark){}</style>" + "x" * 600, encoding="utf-8")
    preview_canonical_path(project).write_text(_canonical_body(), encoding="utf-8")
    hub = src / "views" / "HubView.vue"
    hub.write_text(
        f"{PREVIEW_IMPL_LOCK}\n<template><div class=\"home-hero float-sheet board-path\">ok</div></template>\n",
        encoding="utf-8",
    )
    sync_h5_page_scaffold(project, app_name="PreviewApp", write=True)
    text = hub.read_text(encoding="utf-8")
    assert "home-hero" in text
    assert "SCAFFOLD:pipeline:start" not in text
