"""Tests for skill_icons H5 sprite mapping."""

from __future__ import annotations

from batch.skill_icons import (
    format_h5_icon_landing_block,
    h5_symbol_id,
    normalize_icon_slug,
    parse_icon_names_from_brief,
)


def test_normalize_icon_slug_aliases_house_to_home() -> None:
    assert normalize_icon_slug("House") == "home"
    assert normalize_icon_slug("pencil-simple") == "edit"


def test_h5_symbol_id_uses_prefix() -> None:
    assert h5_symbol_id("buildioo", "home") == "buildioo-mark-home"


def test_parse_icon_names_from_brief_ignores_category() -> None:
    text = "\n".join(
        [
            "## 1. Navigation",
            "- **Category:** Navigation",
            "- **Icon Name:** house",
            "- **Library:** Phosphor",
        ]
    )
    assert parse_icon_names_from_brief(text) == ["home"]


def test_format_h5_icon_landing_block_includes_symbol_pattern() -> None:
    block = format_h5_icon_landing_block("buildioo")
    assert "buildioo-mark-home" in block
    assert "Import Code" in block
    assert "icon-sprite-manifest.json" in block
