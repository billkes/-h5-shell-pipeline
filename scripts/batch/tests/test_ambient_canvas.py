"""Tests for ambient canvas brief generation."""

from __future__ import annotations

from batch.ambient_canvas import (
    _motif_key,
    build_ambient_canvas_brief,
    format_ambient_canvas_prompt_block,
)


def _buildioo_candidate() -> dict:
    return {
        "style": {
            "name": "Predictive Analytics",
            "effects": "Forecast line animation, confidence band fade-in",
            "best_for": "Forecasting dashboards, budget planning",
        },
        "colors": {
            "primary": "#EC4899",
            "secondary": "#F472B6",
            "accent": "#0284C7",
            "background": "#FDF2F8",
        },
        "pattern": {"name": "Hero + Features + CTA"},
    }


def _prompio_candidate() -> dict:
    return {
        "style": {
            "name": "Inclusive Design",
            "effects": "focus indicators, voice guidance",
            "best_for": "education, accessible consumer",
        },
        "colors": {
            "primary": "#0D9488",
            "secondary": "#2DD4BF",
            "accent": "#D97706",
            "background": "#F0FDFA",
        },
        "pattern": {
            "name": "Horizontal Scroll Journey",
            "color_strategy": "Continuous palette transition. Chapter colors.",
        },
    }


def test_motif_key_differentiates_buildioo_vs_prompio() -> None:
    assert _motif_key(_buildioo_candidate()) == "predictive_analytics"
    assert _motif_key(_prompio_candidate()) == "horizontal_journey"


def test_brief_includes_scene_and_token_contract() -> None:
    brief = build_ambient_canvas_brief(
        _buildioo_candidate(),
        designer={
            "heroVisualMotif": "budget planning",
            "navigationPattern": "Hero + Features + CTA",
        },
    )
    assert "predictive_analytics" in brief
    assert "u-{prefix}-ambient" in brief
    assert "data-{prefix}-scene" in brief
    assert "heroVisualMotif" in brief
    assert "--{prefix}-ambient-a" in brief


def test_prompt_block_references_brief_path() -> None:
    block = format_ambient_canvas_prompt_block("skill-adapt/ambient-canvas-brief.md")
    assert "Ambient Canvas" in block
    assert "skill-adapt/ambient-canvas-brief.md" in block
