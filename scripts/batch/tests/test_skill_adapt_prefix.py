"""Tests for skill_adapt icon manifest prefix refresh."""

from __future__ import annotations

import json
from pathlib import Path

from batch.skill_adapt import refresh_icon_sprite_manifest_prefix


def test_refresh_icon_sprite_manifest_prefix(tmp_path: Path) -> None:
    ws = tmp_path
    (ws / "本包代码组合.json").write_text(
        json.dumps({"dartCodePrefix": "eebun"}),
        encoding="utf-8",
    )
    manifest = {
        "prefix": "apxxx",
        "symbols": [
            {"slug": "home", "symbolId": "apxxx-mark-home", "source": "canonical"},
            {"slug": "list", "symbolId": "apxxx-mark-list", "source": "uupm-icons"},
        ],
    }
    adapt = ws / "skill-adapt"
    adapt.mkdir()
    (adapt / "icon-sprite-manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    assert refresh_icon_sprite_manifest_prefix(ws) is True
    data = json.loads((adapt / "icon-sprite-manifest.json").read_text(encoding="utf-8"))
    assert data["prefix"] == "eebun"
    assert data["symbols"][0]["symbolId"] == "eebun-mark-home"
