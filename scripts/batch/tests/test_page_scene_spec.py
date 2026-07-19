"""Tests for product-bound welcome/hub page scene specs."""

from __future__ import annotations

from batch.page_scene_spec import (
    build_hub_scene_spec,
    build_welcome_scene_spec,
    hub_pattern_for_topology,
)
from batch.screen_inventory import page_slugs_from_spec, parse_tab1_route


def test_welcome_specs_differ_by_core_scene() -> None:
    a = build_welcome_scene_spec(
        {
            "product": {
                "audience": "Pros",
                "coreScene": "Elevator glance before meeting",
                "localFeature": "Dossier cards",
            }
        },
        product_flow="Glance; Rehearse; Ready",
    )
    b = build_welcome_scene_spec(
        {
            "product": {
                "audience": "Night owls",
                "coreScene": "Soul question before sleep",
                "localFeature": "Reminder ring",
            }
        },
        product_flow="Ask; Light ring; Yearbook",
    )
    assert "Elevator glance" in a["scene_brief"]
    assert "Soul question" in b["scene_brief"]
    assert a["scene_brief"] != b["scene_brief"]
    assert "Onboarding Pattern Guidance" == a["guidance_heading"]


def test_hub_specs_follow_topology() -> None:
    workspace = build_hub_scene_spec(
        {
            "product": {"coreScene": "Month-end habit review", "audience": "Self-improvers"},
            "constraints": {
                "interactionTopology": "T5_workspace",
                "interactionTopologyLabel": "Single workspace",
            },
        }
    )
    ring = build_hub_scene_spec(
        {
            "product": {"coreScene": "Nightly question", "audience": "Journalers"},
            "constraints": {
                "interactionTopology": "T8_reminder_ring",
                "interactionTopologyLabel": "Reminder ring",
            },
        }
    )
    assert "T5_workspace" in workspace["scene_brief"]
    assert "canvas" in workspace["layout"]["Layout"].lower() or "workspace" in workspace["layout"]["Layout"].lower()
    assert "T8_reminder_ring" in ring["scene_brief"]
    assert "ring" in ring["layout"]["Layout"].lower()
    assert workspace["scene_brief"] != ring["scene_brief"]


def test_hub_pattern_markers_exist() -> None:
    p = hub_pattern_for_topology("T8_reminder_ring")
    assert "ring" in p["markers"]
    unknown = hub_pattern_for_topology("T99_unknown")
    assert "primary zone" in unknown["primary_zone"].lower() or "Derive" in unknown["primary_zone"]


def test_tab1_route_maps_to_hub_slug() -> None:
    spec = """
## Screen Inventory
| Route | Screen | Purpose | Note |
|-------|--------|---------|------|
| `#/splash` | Splash | boot | Cold start |
| `#/welcome` | Welcome | gate | First launch |
| `#/today` | Today Canvas | Daily check-in | Tab 1 |
| `#/trends` | Trends | Charts | Tab 2 |

## Tab navigation (h5_shell)
| # | Label | Route | Icon |
|---|-------|-------|------|
| 1 | Today | `#/today` | calendar |
| 2 | Trends | `#/trends` | chart |
"""
    assert parse_tab1_route(spec) == "/today"
    slugs = page_slugs_from_spec(spec)
    assert "hub" in slugs
    assert "today" not in slugs
