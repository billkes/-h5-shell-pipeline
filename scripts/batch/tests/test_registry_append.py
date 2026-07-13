"""append_to_registry writes package metadata."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from batch.registry import (
    append_to_registry,
    audit_registry_duplicate_names,
    check_registry_similarity,
    ensure_contentpack_registry,
    find_package_by_name,
    registry_probe_from_task_row,
)
from batch.task_audit import audit_task_registry_similarity
from batch.tests.pipeline_fixtures import sample_csv_row


def test_ensure_contentpack_registry_creates_file(tmp_path: Path) -> None:
    registry = tmp_path / "contentpack-registry.json"
    ensure_contentpack_registry(registry)
    data = json.loads(registry.read_text(encoding="utf-8"))
    assert data == {"packages": []}


def test_append_to_registry_adds_package(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text('{"packages": []}', encoding="utf-8")
    workspace = tmp_path / "ws"
    workspace.mkdir()
    pkg = workspace / "本包登记信息.json"
    pkg.write_text(
        json.dumps({"themeAngle": "unique", "mainFeature": "x"}),
        encoding="utf-8",
    )
    combo = workspace / "本包代码组合.json"
    combo.write_text('{"dartCodePrefix": "ab"}', encoding="utf-8")

    ok = append_to_registry(
        registry, pkg, workspace, "TestPkg", "desc", batch_id="b-1"
    )
    assert ok
    data = json.loads(registry.read_text(encoding="utf-8"))
    assert len(data["packages"]) == 1
    assert data["packages"][0]["name"] == "TestPkg"
    assert data["packages"][0]["batchId"] == "b-1"
    assert "codeAntiCorrelation" in data["packages"][0]


def test_append_to_registry_upsert_replaces_same_name(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps({"packages": [{"name": "TestPkg", "themeAngle": "old"}]}),
        encoding="utf-8",
    )
    workspace = tmp_path / "ws"
    workspace.mkdir()
    pkg = workspace / "本包登记信息.json"
    pkg.write_text(json.dumps({"themeAngle": "new"}), encoding="utf-8")

    ok = append_to_registry(
        registry, pkg, workspace, "TestPkg", "new desc", upsert=True
    )
    assert ok
    data = json.loads(registry.read_text(encoding="utf-8"))
    assert len(data["packages"]) == 1
    assert data["packages"][0]["themeAngle"] == "new"
    assert data["packages"][0]["description"] == "new desc"


def test_find_package_by_name_matches_app_name(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps({"packages": [{"appName": "Hathoo", "registeredAt": "2026-01-01"}]}),
        encoding="utf-8",
    )
    found = find_package_by_name(registry, "Hathoo")
    assert found is not None
    assert found["registeredAt"] == "2026-01-01"


def test_audit_registry_duplicate_names_flags_existing(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps({"packages": [{"name": "Buildioo", "registeredAt": "2026-07-01"}]}),
        encoding="utf-8",
    )
    row = sample_csv_row("Buildioo", pack_type="h5_swift_shell", product_code="Buil00")
    issues = audit_registry_duplicate_names([row], registry)
    assert issues
    assert "Buildioo" in issues[0]
    assert "2026-07-01" in issues[0]


def test_check_registry_similarity_detects_duplicate_tab(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "packages": [
                    {
                        "name": "Old",
                        "themeAngle": "completely different words here",
                        "innovationTabName": "SameTab",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    new_pkg = tmp_path / "new.json"
    new_pkg.write_text(
        json.dumps(
            {
                "themeAngle": "another unique angle",
                "innovationTabName": "SameTab",
            }
        ),
        encoding="utf-8",
    )
    ok, report = check_registry_similarity(registry, new_pkg)
    assert ok is False
    assert "SameTab" in report or "Innovation Tab" in report


def test_audit_task_registry_similarity_flags_history(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "packages": [
                    {
                        "name": "OldPkg",
                        "themeAngle": "yoga school progression paths duration stats",
                        "mainFeature": "Sketch and mark visual notes",
                        "feedLayout": "Horizontal timeline with milestone cards",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    row = replace(
        sample_csv_row("Hathoo", pack_type="h5_swift_shell", product_code="Hatha00"),
        theme_cn="瑜伽流派进阶",
        core_scene="瑜伽流派进阶路径与各流派时长统计",
        local_feature="速查对照表",
        product_flow="Horizontal timeline with milestone cards",
    )
    issues = audit_task_registry_similarity([row], registry)
    assert issues
    assert any("OldPkg" in i or "feedLayout" in i or "mainFeature" in i for i in issues)
