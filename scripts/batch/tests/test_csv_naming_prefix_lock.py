"""Tests for dartCodePrefix preservation across lock.dimensions."""

from __future__ import annotations

import json
from pathlib import Path

from batch.csv_architecture import apply_csv_to_code_combo
from batch.csv_naming import apply_naming_rule_to_combo
from batch.csv_tasks import CsvTaskRow


def _row(**overrides: str) -> CsvTaskRow:
    base = dict(
        name="Buildioo",
        full_name="Buildioo - Calm & List",
        state_management="SetState",
        architecture_pattern="MVC",
        naming_obfuscation_rule="双随机首段策略",
        privacy_style="",
        privacy_file="",
        git_url="",
        first_product_code="",
        programming_style="德国人",
        pack_type="h5_swift_shell",
        audience="",
        core_scene="",
        local_feature="",
        product_flow="",
    )
    base.update(overrides)
    return CsvTaskRow(**base)


def test_apply_naming_rule_preserves_combo_prefix(tmp_path: Path) -> None:
    ws = tmp_path
    combo = ws / "本包代码组合.json"
    combo.write_text(
        json.dumps({"dartCodePrefix": "dofqm", "namingRuleMeta": {"packageSeed": "dofqm"}}),
        encoding="utf-8",
    )
    data = json.loads(combo.read_text(encoding="utf-8"))
    apply_naming_rule_to_combo(ws, _row(), data)
    assert data["dartCodePrefix"] == "dofqm"
    meta = data["namingRuleMeta"]
    assert meta.get("ruleKey") == "dual_random_head"
    assert meta.get("packageSeed") == "dofqm"
    assert meta.get("affix")
    assert meta.get("lengthRange")
    assert meta.get("joinStyles")


def test_apply_naming_rule_reads_prefix_from_lock(tmp_path: Path) -> None:
    ws = tmp_path
    (ws / "本包代码组合.json").write_text(json.dumps({}), encoding="utf-8")
    (ws / "本包维度锁.json").write_text(
        json.dumps({"namingObfuscationRule": {"dartCodePrefix": "ghlvi"}}),
        encoding="utf-8",
    )
    data: dict = {}
    apply_naming_rule_to_combo(ws, _row(), data)
    assert data["dartCodePrefix"] == "ghlvi"


def test_apply_naming_rule_prefers_lock_over_stale_combo(tmp_path: Path) -> None:
    ws = tmp_path
    (ws / "本包代码组合.json").write_text(
        json.dumps({"dartCodePrefix": "hobud"}),
        encoding="utf-8",
    )
    (ws / "本包维度锁.json").write_text(
        json.dumps({"namingObfuscationRule": {"dartCodePrefix": "dofqm"}}),
        encoding="utf-8",
    )
    data = json.loads((ws / "本包代码组合.json").read_text(encoding="utf-8"))
    apply_naming_rule_to_combo(ws, _row(), data)
    assert data["dartCodePrefix"] == "dofqm"


def test_apply_csv_to_code_combo_syncs_folders_from_lock(tmp_path: Path) -> None:
    ws = tmp_path
    lock_folders = {
        "models": {
            "role": "models",
            "folderBasename": "dofqm_mesh_hub",
            "stubBasename": "dofqm_spark_port_anchor",
        }
    }
    (ws / "本包维度锁.json").write_text(
        json.dumps(
            {
                "namingObfuscationRule": {"dartCodePrefix": "dofqm"},
                "architectureFolders": lock_folders,
            }
        ),
        encoding="utf-8",
    )
    (ws / "本包代码组合.json").write_text(
        json.dumps(
            {
                "dartCodePrefix": "hobud",
                "stateManagement": "setstate",
                "architecturePattern": "mvc",
            }
        ),
        encoding="utf-8",
    )
    apply_csv_to_code_combo(ws, _row())
    data = json.loads((ws / "本包代码组合.json").read_text(encoding="utf-8"))
    assert data["dartCodePrefix"] == "dofqm"
    assert data["architectureFolders"] == lock_folders
