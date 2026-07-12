"""Tests for h5_deflavor_audit."""

from __future__ import annotations

import json
from pathlib import Path

from batch.h5_deflavor_audit import verify_h5_deflavor_baseline


def _write_h5_vault(ws: Path, *, prefix: str = "paaow", bad_scrollbar: bool = False) -> None:
    vault = ws / "assets" / f"{prefix}_vault"
    vault.mkdir(parents=True)
    scrollbar = "display: block" if bad_scrollbar else "display: none"
    (vault / f"{prefix}_baseline.css").write_text(
        f"""
* {{ -webkit-tap-highlight-color: transparent; }}
::-webkit-scrollbar {{ {scrollbar}; }}
html, body, *:not(input):not(textarea) {{ user-select: none; }}
:root {{ --safe-top: env(safe-area-inset-top); }}
""",
        encoding="utf-8",
    )
    (vault / f"{prefix}_entry.htm").write_text(
        '<meta name="viewport" content="viewport-fit=cover">',
        encoding="utf-8",
    )
    (ws / "本包登记信息.json").write_text(
        json.dumps(
            {
                "packType": "h5_shell",
                "bundleEntryPath": f"assets/{prefix}_vault/{prefix}_entry.htm",
                "codeAntiCorrelation": {"dartCodePrefix": prefix},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_verify_h5_deflavor_baseline_ok(tmp_path: Path) -> None:
    _write_h5_vault(tmp_path)
    assert verify_h5_deflavor_baseline(tmp_path) == []


def test_verify_h5_deflavor_detects_scrollbar_regression(tmp_path: Path) -> None:
    _write_h5_vault(tmp_path, bad_scrollbar=True)
    issues = verify_h5_deflavor_baseline(tmp_path)
    assert any("display: block" in i for i in issues)


def test_verify_h5_deflavor_skips_non_h5(tmp_path: Path) -> None:
    (tmp_path / "本包登记信息.json").write_text(
        json.dumps({"packType": "tool_flutter"}),
        encoding="utf-8",
    )
    assert verify_h5_deflavor_baseline(tmp_path) == []
