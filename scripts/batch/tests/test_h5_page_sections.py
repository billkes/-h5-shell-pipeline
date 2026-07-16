"""Tests for spec-driven tab-root section composer."""

from __future__ import annotations

from batch.h5_page_sections import (
    TAB_ROOT_BLUEPRINT,
    compose_tab_root_vue,
    resolve_tab_root_sections,
    verify_tab_root_blueprint,
)
from batch.preview_fidelity_gate import PREVIEW_IMPL_LOCK


def test_blueprint_covers_all_tab_roots() -> None:
    assert set(TAB_ROOT_BLUEPRINT) == {"hub", "list", "settings"}
    assert verify_tab_root_blueprint() == []


def test_topology_trims_wizard_lane_on_default_hub() -> None:
    wizard = "wizard-lane"
    assert wizard in resolve_tab_root_sections("hub", "T4_wizard")
    assert wizard not in resolve_tab_root_sections("hub", "default")


def test_compose_list_has_run_card_landmark() -> None:
    vue = compose_tab_root_vue(
        "list",
        "T4_wizard",
        values={
            "{{PREFIX}}": "demo",
            "{{VIEW_STEM}}": "RunsView",
            "{{LIST_TITLE}}": "Runs",
            "{{LIST_EYEBROW}}": "e",
            "{{LIST_HEADLINE}}": "t",
            "{{LIST_SUB}}": "s",
        },
        title_key="LIST_TITLE",
    )
    assert "run-card" in vue
    assert "list-toolbar" in vue
    assert "Go to Prepare" in vue


def test_compose_settings_has_wallet_and_menu() -> None:
    vue = compose_tab_root_vue(
        "settings",
        "T4_wizard",
        values={
            "{{PREFIX}}": "demo",
            "{{VIEW_STEM}}": "SettingsView",
            "{{SETTINGS_TITLE}}": "Settings",
            "{{SETTINGS_EYEBROW}}": "e",
            "{{SETTINGS_HEADLINE}}": "t",
            "{{SETTINGS_SUB}}": "s",
        },
        title_key="SETTINGS_TITLE",
    )
    assert "settings-wallet" in vue
    assert "settings-menu" in vue
    assert "settings-top" in vue
    assert "wallet-duo" in vue
    assert "settings-block" in vue
    assert PREVIEW_IMPL_LOCK in vue.splitlines()[0]
    assert "Coin Store" in vue
