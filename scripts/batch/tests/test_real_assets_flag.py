"""Tests for task.csv「真图」flag and H5 shell raster slots."""

from __future__ import annotations

import pytest

from batch.asset_naming import build_h5_shell_raster_slots
from batch.naming import NamingMeta
from batch.pipeline_steps import (
    AGENT_ASSETS,
    AGENT_PLAN_PACK,
    AGENT_SHELL,
    steps_for_run,
)
from batch.task_schema import COL_REAL_ASSETS, STANDARD_COLUMNS, parse_real_assets_flag


def test_standard_columns_include_real_assets() -> None:
    assert COL_REAL_ASSETS == "真图"
    assert COL_REAL_ASSETS in STANDARD_COLUMNS
    assert STANDARD_COLUMNS[-1] == COL_REAL_ASSETS


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", False),
        ("0", False),
        ("1", True),
        ("true", True),
        ("YES", True),
        ("no", False),
        ("off", False),
    ],
)
def test_parse_real_assets_flag(raw: str, expected: bool) -> None:
    assert parse_real_assets_flag(raw) is expected


def test_parse_real_assets_flag_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="真图"):
        parse_real_assets_flag("maybe")


def test_agent_assets_between_pack_and_shell() -> None:
    steps = steps_for_run(pack_type="h5_swift_shell")
    assert AGENT_ASSETS in steps
    assert steps.index(AGENT_PLAN_PACK) < steps.index(AGENT_ASSETS)
    assert steps.index(AGENT_ASSETS) < steps.index(AGENT_SHELL)


def test_h5_shell_raster_slots_are_six() -> None:
    meta = NamingMeta(rule_key="consonant_core", package_seed="karwj")
    slots = build_h5_shell_raster_slots(
        "assets_images",
        rule_key="consonant_core",
        meta=meta,
        prefix="karwj",
        theme_hint="lens diary",
    )
    assert len(slots) == 6
    assert {s["slot"] for s in slots} == {
        "logo",
        "launch_light",
        "launch_dark",
        "global_bg_light",
        "global_bg_dark",
        "retry_illustration",
    }
