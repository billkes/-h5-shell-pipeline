"""Tests for skill_tokens CSS generation."""

from __future__ import annotations

from batch.skill_tokens import _css_from_tokens, _css_has_declarations, _tokens_from_candidate


def test_css_has_declarations_detects_empty_node_output() -> None:
    empty = ":root {\n}\n"
    assert not _css_has_declarations(empty)
    assert _css_has_declarations(":root { --color-primary: #112233; }")


def test_tokens_from_candidate() -> None:
    candidate = {
        "colors": {
            "primary": "#112233",
            "background": "#FFFFFF",
        },
        "spacing_scale": {"md": "16px"},
    }
    tokens = _tokens_from_candidate(candidate)
    assert tokens["primitive"]["color.primary"] == "#112233"
    css = _css_from_tokens(tokens)
    assert "--color-primary: #112233" in css
