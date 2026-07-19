"""Tests for skill_icons Phosphor mapping."""

from __future__ import annotations

from batch.skill_icons import (
    ALLOWED_ICON_PACKAGE,
    format_h5_icon_landing_block,
    h5_symbol_id,
    normalize_icon_slug,
    parse_icon_names_from_brief,
    phosphor_component_name,
)


def test_normalize_icon_slug_aliases_home_to_house() -> None:
    assert normalize_icon_slug("House") == "house"
    assert normalize_icon_slug("home") == "house"
    assert normalize_icon_slug("pencil-simple") == "pencil-simple"


def test_phosphor_component_name() -> None:
    assert phosphor_component_name("pencil-simple") == "PencilSimple"
    assert phosphor_component_name("house") == "House"


def test_h5_symbol_id_uses_prefix() -> None:
    assert h5_symbol_id("buildioo", "house") == "buildioo-ph-house"


def test_parse_icon_names_from_brief_ignores_category() -> None:
    text = "\n".join(
        [
            "## 1. Navigation",
            "- **Category:** Navigation",
            "- **Icon Name:** house",
            "- **Library:** Phosphor",
        ]
    )
    assert parse_icon_names_from_brief(text) == ["house"]


def test_format_h5_icon_landing_block_requires_phosphor() -> None:
    block = format_h5_icon_landing_block("buildioo")
    assert ALLOWED_ICON_PACKAGE in block
    assert "Phosphor" in block
    assert "icon-manifest.json" in block
    assert "iconfont" in block
    assert "Ignore `Library`" not in block
