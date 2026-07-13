"""Tests for skill_stack_brief translator."""

from __future__ import annotations

from batch.skill_stack_brief import translate_tailwind_to_h5_vanilla


def test_translate_tailwind_to_h5_vanilla() -> None:
    stack = "# Stack\n\nUse `bg-primary` and `hidden md:block`"
    text = translate_tailwind_to_h5_vanilla(stack, "--color-primary: #fff")
    assert "h5-vanilla" in text
    assert "No `@apply`" in text
    assert "bg-primary" in text
