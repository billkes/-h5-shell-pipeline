"""Tests for English-only H5 UI copy helpers."""

from __future__ import annotations

import json
from pathlib import Path

from batch.h5_ui_copy import (
    collect_h5_demo_seed_cjk_violations,
    collect_h5_demo_cta_violations,
    collect_h5_stack_layout_violations,
    collect_h5_ui_cjk_violations,
    collect_h5_welcome_demo_violations,
    contains_cjk,
    english_core_scene,
    hero_copy,
)


def test_contains_cjk() -> None:
    assert contains_cjk("严格计时")
    assert not contains_cjk("Timed lectures")


def test_hero_copy_skips_chinese_core_scene(tmp_path: Path) -> None:
    ctx = tmp_path / "skill-input"
    ctx.mkdir()
    (ctx / "context.json").write_text(
        json.dumps(
            {
                "product": {
                    "coreScene": "严格计时的课堂与大学演讲",
                    "localFeature": "实时语速监测与结构性超时预警",
                    "themeAngle": (
                        "Theme: 离线学术演讲节奏控制系统; Product flow: "
                        "Import or paste a presentation script; map each section to a time budget"
                    ),
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    copy = hero_copy(tmp_path)
    assert not contains_cjk(copy["{{HERO_EYEBROW}}"])
    assert not contains_cjk(copy["{{HERO_SUB}}"])
    assert copy["{{HERO_EYEBROW}}"] == "Strictly timed classroom lectures"


def test_english_core_scene_prefers_english_field() -> None:
    product = {"coreScene": "Campus lecture timing"}
    assert english_core_scene(product, default="Fallback") == "Campus lecture timing"


def test_collect_h5_stack_layout_violations(tmp_path: Path) -> None:
    src = tmp_path / "h5" / "src" / "views"
    src.mkdir(parents=True)
    (src / "RunDetailView.vue").write_text(
        '<header class="c-demo-wizard-bar"><button class="c-demo-topbar__back"></button></header>',
        encoding="utf-8",
    )
    issues = collect_h5_stack_layout_violations(tmp_path)
    assert any("wizard-bar" in i for i in issues)


def test_collect_h5_demo_seed_cjk_violations(tmp_path: Path) -> None:
    store = tmp_path / "h5" / "src" / "store"
    store.mkdir(parents=True)
    (store / "data.ts").write_text(
        'export function demoPlan() { return { title: "严格计时" }; }',
        encoding="utf-8",
    )
    issues = collect_h5_demo_seed_cjk_violations(tmp_path)
    assert issues


def test_collect_h5_ui_cjk_violations(tmp_path: Path) -> None:
    src = tmp_path / "h5" / "src" / "views"
    src.mkdir(parents=True)
    (src / "HubView.vue").write_text("<p>严格计时</p>", encoding="utf-8")
    issues = collect_h5_ui_cjk_violations(tmp_path)
    assert issues
    assert "HubView.vue" in issues[0]


def test_collect_h5_demo_cta_violations_hub(tmp_path: Path) -> None:
    views = tmp_path / "h5" / "src" / "views"
    views.mkdir(parents=True)
    (views / "HubView.vue").write_text(
        '<button @click="importDemo">Import Demo Script</button>',
        encoding="utf-8",
    )
    issues = collect_h5_demo_cta_violations(tmp_path)
    assert issues
    assert "HubView.vue" in issues[0]


def test_collect_h5_welcome_demo_violations(tmp_path: Path) -> None:
    views = tmp_path / "h5" / "src" / "views"
    views.mkdir(parents=True)
    (views / "WelcomeView.vue").write_text(
        '<button @click="loadDemo">Load demo plan</button>',
        encoding="utf-8",
    )
    issues = collect_h5_welcome_demo_violations(tmp_path)
    assert issues
    assert "Welcome" in issues[0]
