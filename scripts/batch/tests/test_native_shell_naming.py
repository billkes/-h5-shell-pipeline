"""Tests for native shell Bridge folder naming."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from batch.native_shell_naming import (  # noqa: E402
    apply_native_bridge_folder_rename,
    collect_native_shell_naming_violations,
    collect_programming_style_sources,
    native_bridge_folder_basename,
    uses_semantic_bridge_dir,
)


def test_native_bridge_folder_basename_standard_persona() -> None:
    assert native_bridge_folder_basename("美国人", "bthfc") == "Bridge"
    assert uses_semantic_bridge_dir("英国人") is True


def test_native_bridge_folder_basename_obfuscated_persona() -> None:
    assert native_bridge_folder_basename("法国人", "bthfc") == "bthfc_shell"
    assert uses_semantic_bridge_dir("法国人") is False


def test_collect_violation_when_bridge_dir_on_french_persona() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        app = ws / "ios" / "Teavoo"
        (app / "Bridge").mkdir(parents=True)
        (ws / "本包登记信息.json").write_text(
            json.dumps(
                {
                    "appName": "Teavoo",
                    "packType": "h5_swift_shell",
                    "shellRuntime": "swift",
                    "codeAntiCorrelation": {"dartCodePrefix": "bthfc", "programmingStyle": "法国人"},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        issues = collect_native_shell_naming_violations(ws)
        assert any("Bridge" in i for i in issues)


def test_apply_rename_bridge_to_prefix_shell() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        app = ws / "ios" / "Mockoo"
        bridge = app / "Bridge"
        bridge.mkdir(parents=True)
        (bridge / "WebBridgeHandler.swift").write_text("// stub", encoding="utf-8")
        (ws / "本包登记信息.json").write_text(
            json.dumps(
                {
                    "appName": "Mockoo",
                    "packType": "h5_swift_shell",
                    "shellRuntime": "swift",
                    "codeAntiCorrelation": {"dartCodePrefix": "mocko", "programmingStyle": "德国人"},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        changed = apply_native_bridge_folder_rename(ws, persona="德国人", prefix="mocko")
        assert changed
        assert (app / "mocko_shell" / "WebBridgeHandler.swift").is_file()
        assert not bridge.is_dir()
        assert collect_native_shell_naming_violations(ws) == []


def test_programming_style_mismatch_across_ledgers() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        app = ws / "ios" / "Teavoo"
        (app / "bthfc_shell").mkdir(parents=True)
        (ws / "本包登记信息.json").write_text(
            json.dumps(
                {
                    "appName": "Teavoo",
                    "packType": "h5_swift_shell",
                    "h5VaultLayout": "assets_prefix_surfaces_glyphs",
                    "h5VaultPattern": "h5_modular_svg",
                    "codeAntiCorrelation": {
                        "dartCodePrefix": "bthfc",
                        "programmingStyle": "法国人",
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (ws / "本包代码组合.json").write_text(
            json.dumps({"programmingStyle": "德国人", "dartCodePrefix": "bthfc"}, ensure_ascii=False),
            encoding="utf-8",
        )
        issues = collect_native_shell_naming_violations(ws)
        assert any("台账不一致" in i for i in issues)


def test_architecture_folders_must_match_disk() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        app = ws / "ios" / "Teavoo"
        (app / "bthfc_shell").mkdir(parents=True)
        (app / "bthfc_pulse_mesh").mkdir()
        (ws / "本包登记信息.json").write_text(
            json.dumps(
                {
                    "appName": "Teavoo",
                    "packType": "h5_swift_shell",
                    "h5VaultLayout": "assets_prefix_surfaces_glyphs",
                    "h5VaultPattern": "h5_modular_svg",
                    "codeAntiCorrelation": {
                        "dartCodePrefix": "bthfc",
                        "programmingStyle": "法国人",
                        "architectureFolders": {
                            "views": {"folderBasename": "bthfc_ember_nest"},
                        },
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        issues = collect_native_shell_naming_violations(ws)
        assert any("bthfc_ember_nest" in i for i in issues)
        assert any("bthfc_pulse_mesh" in i for i in issues)


def test_collect_programming_style_sources() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        (ws / "本包登记信息.json").write_text(
            json.dumps({"codeAntiCorrelation": {"programmingStyle": "法国人"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        (ws / "本包代码组合.json").write_text(
            json.dumps({"programmingStyle": "法国人"}, ensure_ascii=False),
            encoding="utf-8",
        )
        sources = collect_programming_style_sources(ws)
        assert sources["本包登记信息.json"] == "法国人"
        assert sources["本包代码组合.json"] == "法国人"
