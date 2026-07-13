"""Tests for h5_layout_contract fixed chrome + page-shell sync."""

from __future__ import annotations

import json
from pathlib import Path

from batch.h5_layout_contract import (
    build_layout_block,
    sync_h5_layout_contract,
    verify_h5_layout_contract,
)
from batch.h5_theme_tokens import sync_h5_global_theme


def _write_project(root: Path, *, css: str) -> Path:
    project = root / "LayoutApp"
    (project / "h5" / "src" / "styles").mkdir(parents=True)
    (project / "skill-adapt").mkdir()
    (project / "本包登记信息.json").write_text(
        json.dumps({"codeAntiCorrelation": {"dartCodePrefix": "demo"}}),
        encoding="utf-8",
    )
    (project / "skill-adapt" / "selected-candidate.json").write_text(
        json.dumps({"designSystem": {"colors": {"primary": "#000", "background": "#111"}}}),
        encoding="utf-8",
    )
    (project / "h5" / "src" / "styles" / "global.css").write_text(css, encoding="utf-8")
    return project


def test_build_layout_block_has_page_inset_tokens() -> None:
    block = build_layout_block("demo")
    assert "--demo-page-inset-top" in block
    assert "height: var(--demo-page-inset-top)" in block
    assert "padding: var(--demo-page-inset-top)" in block


def test_sync_appends_layout_block_at_end(tmp_path: Path) -> None:
    project = _write_project(
        tmp_path,
        css=".c-demo-topbar { position: fixed; top: 0; min-height: 48px; }\n.page-shell { padding-top: 56px; }\n",
    )
    sync_h5_layout_contract(project, write=True)
    text = (project / "h5" / "src" / "styles" / "global.css").read_text(encoding="utf-8")
    assert "LAYOUT:pipeline" in text
    assert text.strip().endswith("/* LAYOUT:end */")
    assert verify_h5_layout_contract(project) == []


def test_verify_detects_missing_page_inset(tmp_path: Path) -> None:
    project = _write_project(
        tmp_path,
        css=".c-demo-topbar { position: fixed; top: 0; }\n.page-shell { padding-top: 56px; }\n",
    )
    issues = verify_h5_layout_contract(project)
    assert any("page-inset-top" in i for i in issues)


def test_theme_sync_includes_layout_block(tmp_path: Path) -> None:
    project = _write_project(tmp_path, css=":root { --demo-bg: #000; }\n")
    sync_h5_global_theme(project, write=True)
    text = (project / "h5" / "src" / "styles" / "global.css").read_text(encoding="utf-8")
    assert "LAYOUT:pipeline" in text
    assert "--safe-top" in text
    assert verify_h5_layout_contract(project) == []
