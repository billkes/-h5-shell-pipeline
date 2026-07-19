"""Tests for skill_stack_brief H5 runtime contract."""

from __future__ import annotations

from pathlib import Path

from batch.skill_stack_brief import (
    translate_tailwind_to_h5_vite,
    write_h5_runtime_brief,
)


def test_translate_tailwind_to_h5_vite_is_runtime_stub() -> None:
    text = translate_tailwind_to_h5_vite("# Stack\n\nUse `bg-primary`", "--color-primary: #fff")
    assert "stack-html-tailwind" in text or "stack-vue" in text
    assert "vite-plugin-singlefile" in text or "5174" in text


def test_write_h5_runtime_brief_points_to_skill_stacks(tmp_path: Path) -> None:
    out = write_h5_runtime_brief(tmp_path, "DemoApp")
    assert out is not None
    text = out.read_text(encoding="utf-8")
    assert "stack-vue.md" in text
    assert "stack-html-tailwind.md" in text
    assert "@phosphor-icons/vue" in text
    assert "Tailwind → Vue/CSS mapping" not in text
    # Legacy compat file should be removed if present
    legacy = out.parent / "stack-h5-vite.md"
    legacy.write_text("old", encoding="utf-8")
    write_h5_runtime_brief(tmp_path, "DemoApp")
    assert not legacy.is_file()
