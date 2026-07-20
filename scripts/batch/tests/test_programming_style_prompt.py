"""Tests for runtime-aware programming style prompt blocks."""

from __future__ import annotations

from batch.csv_architecture import build_programming_style_prompt_block
from batch.csv_prompt_blocks import dimension_boundary_block
from batch.csv_tasks import CsvTaskRow


def _row(pack_type: str) -> CsvTaskRow:
    return CsvTaskRow(
        name="TestApp",
        full_name="TestApp",
        state_management="Provider",
        architecture_pattern="MVC",
        naming_obfuscation_rule="辅音核心策略",
        privacy_style="",
        privacy_file="",
        git_url="",
        first_product_code="",
        programming_style="德国人",
        pack_type=pack_type,
    )


def test_native_programming_style_prompt_dims_2_to_5() -> None:
    block = build_programming_style_prompt_block(_row("h5_swift_shell"), prefix="abcd")
    assert "dims 2–5" in block
    assert "编程人设风格.md" in block
    assert "Widget split: N/A" in block
    assert "bridgeDeckSelections" in block
    assert "every `.dart` file" not in block


def test_flutter_programming_style_prompt_all_7_dims() -> None:
    block = build_programming_style_prompt_block(_row("h5_flutter_shell"), prefix="abcd")
    assert "ALL 7 matrix cells" in block
    assert "every `.dart` file" in block


def test_dimension_boundary_native_shell() -> None:
    block = dimension_boundary_block(native_shell=True)
    assert "Flutter-only" in block
    assert "bridgeDeckSelections" in block
