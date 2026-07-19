"""Tests for tab-root blueprint metadata (no fragment composer)."""

from __future__ import annotations

from batch.h5_page_sections import (
    TAB_ROOT_BLUEPRINT,
    resolve_tab_root_sections,
    verify_tab_root_blueprint,
)


def test_blueprint_covers_all_tab_roots() -> None:
    assert set(TAB_ROOT_BLUEPRINT) == {"hub", "list", "settings"}
    assert verify_tab_root_blueprint() == []


def test_topology_trims_wizard_lane_on_default_hub() -> None:
    wizard = "wizard-lane"
    assert wizard in resolve_tab_root_sections("hub", "T4_wizard")
    assert wizard not in resolve_tab_root_sections("hub", "default")


def test_topology_hub_sections_differ() -> None:
    t5 = resolve_tab_root_sections("hub", "T5_workspace")
    t8 = resolve_tab_root_sections("hub", "T8_reminder_ring")
    t1 = resolve_tab_root_sections("hub", "T1_dashboard")
    assert "primary-zone" in t5
    assert "chip-rail-hub" not in t5
    assert "primary-zone" in t8
    assert "kpi-strip-hub" in t1
    assert t5 != t1
