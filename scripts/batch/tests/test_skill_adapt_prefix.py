"""Icon manifest prefix comes from early dimension lock (prepare.context), not lock refresh."""

from __future__ import annotations

import json
from pathlib import Path

from batch.skill_adapt import _build_icon_sprite_manifest


def test_icon_manifest_uses_early_dart_prefix(tmp_path: Path) -> None:
    ws = tmp_path
    (ws / "本包代码组合.json").write_text(
        json.dumps({"dartCodePrefix": "eebun"}),
        encoding="utf-8",
    )
    candidate: dict = {"style": {}, "pattern": {}}
    designer = {"iconStyle": "Phosphor outlined regular"}
    manifest = _build_icon_sprite_manifest(ws, candidate, designer)
    assert manifest["prefix"] == "eebun"
    for entry in manifest["symbols"]:
        assert entry["symbolId"].startswith("eebun-mark-")
