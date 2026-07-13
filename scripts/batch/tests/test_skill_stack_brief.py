"""Tests for skill_stack_brief translator."""

from __future__ import annotations

from batch.skill_stack_brief import translate_tailwind_to_h5_vite


def test_translate_tailwind_to_h5_vite() -> None:
    stack = "# Stack\n\nUse `bg-primary` and `hidden md:block`"
    text = translate_tailwind_to_h5_vite(stack, "--color-primary: #fff")
    assert "h5-vite" in text
    assert "vite-plugin-singlefile" in text
    assert "5174" in text
    assert "bg-primary" in text
