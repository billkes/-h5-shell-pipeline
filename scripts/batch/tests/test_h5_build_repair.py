"""Tests for dev.h5.build compile repair helpers."""

from __future__ import annotations

from batch.h5_build_repair import (
    build_focus_for_issues,
    h5_build_repair_max_rounds,
    is_repairable_build_failure,
)


def test_max_rounds_default_three(monkeypatch) -> None:
    monkeypatch.delenv("H5_BUILD_REPAIR_MAX_ROUNDS", raising=False)
    assert h5_build_repair_max_rounds() == 3


def test_non_repairable_missing_npm() -> None:
    assert not is_repairable_build_failure(["MISSING: npm (Node.js) — required for dev.h5.build"])


def test_non_repairable_missing_scaffold() -> None:
    assert not is_repairable_build_failure(
        ["MISSING: h5/package.json (run lock.dimensions scaffold)"]
    )


def test_repairable_vite_error() -> None:
    issues = ["npm run build:deploy failed (exit 1): error TS2304: Cannot find name 'foo'"]
    assert is_repairable_build_failure(issues)
    assert "TypeScript" in build_focus_for_issues(issues)
