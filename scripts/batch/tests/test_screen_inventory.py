"""Tests for PM Screen Inventory route parsing."""

from __future__ import annotations

from batch.screen_inventory import (
    ambient_scene_min_rows,
    filter_blueprint_v2_sections,
    filter_visual_lock_v2_keys,
    parse_h5_routes,
    project_includes_route,
)
from batch.pipeline_gates import VISUAL_BLUEPRINT_V2_SECTIONS, VISUAL_LOCK_V2_KEYS


SPEC_WITH_WELCOME = """
## Screen Inventory

| Route | Screen | Layer |
|-------|--------|-------|
| #/splash | Splash | H5 |
| #/welcome | Welcome Gate | H5 |
| #/hub | Prepare Hub | H5 Tab |
| #/legal | Legal Modal | H5 Overlay |
| #/plaza | Bridge Plaza | H5 Hidden |
| #/store | Coin Store | H5 |
| — | WKWebView Host | OC Shell |
"""


SPEC_HUB_ONLY = """
## Screen Inventory

| Route | Screen | Layer |
|-------|--------|-------|
| #/hub | Prepare Hub | H5 Tab |
"""


def test_parse_h5_routes_from_inventory_table() -> None:
    routes = parse_h5_routes(SPEC_WITH_WELCOME)
    assert routes == frozenset(
        {"/splash", "/welcome", "/hub", "/legal", "/plaza", "/store"}
    )


def test_parse_skips_native_shell_rows() -> None:
    routes = parse_h5_routes(SPEC_HUB_ONLY)
    assert routes == frozenset({"/hub"})


def test_filter_blueprint_sections_without_welcome() -> None:
    routes = parse_h5_routes(SPEC_HUB_ONLY)
    filtered = filter_blueprint_v2_sections(VISUAL_BLUEPRINT_V2_SECTIONS, routes)
    assert "Welcome Gate Canon" not in filtered
    assert "IAP Store Layout" not in filtered
    assert "Ambient Canvas" in filtered


def test_filter_visual_lock_without_welcome() -> None:
    routes = parse_h5_routes(SPEC_HUB_ONLY)
    filtered = filter_visual_lock_v2_keys(VISUAL_LOCK_V2_KEYS, routes)
    assert "welcomeSpec" not in filtered
    assert "ambientCanvas" in filtered


def test_ambient_scene_min_rows_scales_with_inventory() -> None:
    assert ambient_scene_min_rows(frozenset({"/hub"})) == 2
    assert ambient_scene_min_rows(frozenset({f"/p{i}" for i in range(6)})) == 4


def test_project_includes_route(tmp_path) -> None:
    (tmp_path / "功能文档.md").write_text(SPEC_WITH_WELCOME, encoding="utf-8")
    assert project_includes_route(tmp_path, "#/welcome")
    assert not project_includes_route(tmp_path, "#/missing")
