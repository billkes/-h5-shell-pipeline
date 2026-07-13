"""Tests for product ↔ uupm binding helpers."""

from __future__ import annotations

import json
from pathlib import Path

from batch.skill_product_bind import (
    domain_theme_boost,
    hero_visual_motif,
    master_category_label,
    navigation_pattern_canon,
)
from batch.uupm_design_system import _patch_master_category


def test_master_category_label_prefers_core_scene() -> None:
    bind = {
        "product": {
            "coreScene": "开学预算清单",
            "localFeature": "支出追踪",
            "themeCn": "工具",
            "audience": "陪读家长",
        }
    }
    assert master_category_label(bind) == "开学预算清单"


def test_hero_visual_motif_from_product_not_style() -> None:
    bind = {
        "product": {"coreScene": "课堂演讲", "localFeature": "提词滚动"},
        "constraints": {"interactionTopologyLabel": "Wizard pipeline"},
    }
    motif = hero_visual_motif(bind)
    assert "课堂演讲" in motif
    assert "Wizard pipeline" in motif


def test_domain_theme_boost_favors_financial_for_budget_product() -> None:
    product = "back-to-school checklist budget spending tracker parent school"
    finance = {
        "id": "c1",
        "category": "Finance",
        "style": {"name": "Financial Dashboard", "keywords": "budget ledger"},
    }
    analytics = {
        "id": "c3",
        "style": {"name": "Predictive Analytics", "keywords": "forecast AI"},
    }
    assert domain_theme_boost(finance, product) > domain_theme_boost(analytics, product)


def test_navigation_pattern_canon_uses_topology_label() -> None:
    bind = {
        "constraints": {
            "interactionTopology": "T8_reminder_ring",
            "interactionTopologyLabel": "Reminder ring hub",
        }
    }
    assert navigation_pattern_canon(bind, project_dir=Path("."), fallback="Enterprise SaaS") == "Reminder ring hub"


def test_patch_master_category_replaces_uupm_line(tmp_path: Path) -> None:
    master = tmp_path / "MASTER.md"
    master.write_text(
        "# Design System MASTER\n\n**Category:** Mood Tracker\n\n## Colors\n",
        encoding="utf-8",
    )
    _patch_master_category(master, "开学预算清单")
    text = master.read_text(encoding="utf-8")
    assert "**Category:** 开学预算清单" in text
    assert "Mood Tracker" not in text
