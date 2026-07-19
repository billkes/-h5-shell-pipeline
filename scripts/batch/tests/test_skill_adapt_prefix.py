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
    assert manifest["delivery"] == "phosphor-vue"
    assert manifest["package"] == "@phosphor-icons/vue"
    for entry in manifest["icons"]:
        assert entry["component"]
        assert entry["package"] == "@phosphor-icons/vue"
    # Legacy symbols[] maps symbolId → Phosphor component name (not sprite id).
    assert manifest["symbols"][0]["symbolId"] == "House"
