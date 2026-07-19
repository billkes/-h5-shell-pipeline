"""Tests for h5_kit_skeleton — kit CSS skeleton + bare element audit."""

from __future__ import annotations

import json
from pathlib import Path

from batch.h5_kit_skeleton import (
    build_kit_css_skeleton,
    sync_kit_css_skeleton,
    verify_h5_bare_kit_elements,
)


def test_build_kit_css_skeleton_bauhaus_shape() -> None:
    css = build_kit_css_skeleton(
        "demo",
        candidate={
            "designSystem": {
                "colors": {"primary": "#0F172A", "accent": "#16A34A"},
                "typography": {"heading": "Playfair Display", "body": "Outfit"},
            }
        },
        designer={"shapeLanguage": "Bauhaus (包豪斯)"},
    )
    assert ".c-demo-btn" in css
    assert ".c-demo-checkbox-row" in css
    assert ".c-demo-link" in css
    assert "border-radius: 4px" in css
    assert "4px 4px 0 var(--demo-primary)" in css


def test_sync_kit_css_skeleton_writes_file(tmp_path: Path) -> None:
    (tmp_path / "本包登记信息.json").write_text(
        json.dumps({"codeAntiCorrelation": {"dartCodePrefix": "demo"}}),
        encoding="utf-8",
    )
    adapt = tmp_path / "skill-adapt"
    adapt.mkdir()
    (adapt / "selected-candidate.json").write_text(
        json.dumps({"designSystem": {"style": {"name": "Minimal"}}}),
        encoding="utf-8",
    )
    (adapt / "selected-designer.json").write_text(
        json.dumps({"designerDeckSelections": {"shapeLanguage": "soft rounded"}}),
        encoding="utf-8",
    )
    out = sync_kit_css_skeleton(tmp_path, write=True)
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert ".c-demo-btn" in text
    assert "KIT:pipeline" in text


def test_verify_h5_bare_kit_elements_flags_bare_tags(tmp_path: Path) -> None:
    project = tmp_path / "App"
    h5 = project / "h5" / "src"
    (h5 / "views").mkdir(parents=True)
    (h5 / "styles").mkdir(parents=True)
    (project / "本包登记信息.json").write_text(
        json.dumps({"codeAntiCorrelation": {"dartCodePrefix": "demo"}}),
        encoding="utf-8",
    )
    (project / "h5" / "package.json").write_text('{"name":"demo"}', encoding="utf-8")
    (h5 / "views" / "WelcomeView.vue").write_text(
        """
<template>
  <div>
    <button type="button">Go</button>
    <input type="checkbox" v-model="ok" />
    <a href="#" @click.prevent="openLegal('privacy')">Privacy</a>
  </div>
</template>
""",
        encoding="utf-8",
    )
    issues = verify_h5_bare_kit_elements(project)
    assert any("裸 <button>" in i for i in issues)
    assert any("裸 checkbox" in i for i in issues)
    assert any("裸 <a>" in i for i in issues)
    assert any("缺少 h5/src/styles/kit.css" in i for i in issues)


def test_verify_h5_bare_kit_elements_passes_with_classes(tmp_path: Path) -> None:
    project = tmp_path / "App"
    h5 = project / "h5" / "src"
    (h5 / "views").mkdir(parents=True)
    (h5 / "styles").mkdir(parents=True)
    (project / "本包登记信息.json").write_text(
        json.dumps({"codeAntiCorrelation": {"dartCodePrefix": "demo"}}),
        encoding="utf-8",
    )
    (project / "h5" / "package.json").write_text('{"name":"demo"}', encoding="utf-8")
    (h5 / "styles" / "kit.css").write_text(
        ".c-demo-btn {}\n.c-demo-input {}\n.c-demo-checkbox-row {}\n"
        ".c-demo-panel {}\n.c-demo-chip {}\n",
        encoding="utf-8",
    )
    (h5 / "views" / "WelcomeView.vue").write_text(
        """
<template>
  <label class="c-demo-checkbox-row">
    <input type="checkbox" class="c-demo-checkbox" v-model="ok" />
    <span>I am 18 or older</span>
  </label>
  <button type="button" class="c-demo-btn">Continue</button>
  <a href="#" class="c-demo-link" @click.prevent="openLegal('privacy')">Privacy</a>
</template>
""",
        encoding="utf-8",
    )
    issues = verify_h5_bare_kit_elements(project)
    assert issues == []
