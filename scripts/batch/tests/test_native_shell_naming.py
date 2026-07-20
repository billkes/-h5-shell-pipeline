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
    apply_native_architecture_folder_rename,
    apply_native_bridge_folder_rename,
    collect_native_shell_naming_violations,
    collect_programming_style_sources,
    native_bridge_folder_basename,
    resolve_native_bridge_folder_basename,
    uses_semantic_bridge_dir,
)

_V2_META = {
    "ruleKey": "consonant_core",
    "packageSeed": "mocko",
    "affix": "prefix",
    "lengthRange": [4, 12],
    "joinStyles": {"swiftClass": "PascalCase"},
}


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
                    "codeAntiCorrelation": {
                        "dartCodePrefix": "mocko",
                        "programmingStyle": "德国人",
                        "namingRuleMeta": _V2_META,
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (ws / "本包代码组合.json").write_text(
            json.dumps({"namingRuleMeta": _V2_META}, ensure_ascii=False),
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


def test_resolve_native_bridge_folder_basename_prefers_native_shell_dir() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        (ws / "本包登记信息.json").write_text(
            json.dumps(
                {
                    "codeAntiCorrelation": {
                        "dartCodePrefix": "turcd",
                        "programmingStyle": "法国人",
                        "nativeShellDir": "ty_bridge_shell_do",
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        assert resolve_native_bridge_folder_basename(ws, "法国人", "turcd") == "ty_bridge_shell_do"


def test_apply_architecture_folder_rename_from_template() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        app = ws / "ios" / "Seriyy"
        models = app / "turcd_ember_pulse" / "turcd_ember_pulse_leaf"
        models.mkdir(parents=True)
        (models / "WebContentSource.swift").write_text("// stub", encoding="utf-8")
        (ws / "本包登记信息.json").write_text(
            json.dumps(
                {
                    "appName": "Seriyy",
                    "packType": "h5_swift_shell",
                    "shellRuntime": "swift",
                    "codeAntiCorrelation": {
                        "dartCodePrefix": "turcd",
                        "programmingStyle": "法国人",
                        "architectureFolders": {
                            "models": {
                                "folderBasename": "turcd_flux_pulse",
                                "stubBasename": "turcd_dock_wave_anchor",
                            }
                        },
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        changed = apply_native_architecture_folder_rename(ws, prefix="turcd", app_name="Seriyy")
        assert changed
        assert (app / "turcd_flux_pulse" / "turcd_dock_wave_anchor" / "WebContentSource.swift").is_file()
        assert not (app / "turcd_ember_pulse").is_dir()


def _write_register(ws: Path, app_name: str, prefix: str) -> None:
    (ws / "本包登记信息.json").write_text(
        json.dumps(
            {
                "appName": app_name,
                "packType": "h5_swift_shell",
                "shellRuntime": "swift",
                "codeAntiCorrelation": {
                    "dartCodePrefix": prefix,
                    "programmingStyle": "美国人",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_bridge_channel_mismatch_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        bridge_dir = ws / "ios" / "Monthio" / "Bridge"
        bridge_dir.mkdir(parents=True)
        (bridge_dir / "WebBridgeHandler.swift").write_text(
            'config.userContentController.add(handler, name: "monthioBridge")\n'
            "let script = \"window.monthioBridgeCallback('\\(id)', \\(json));\"\n",
            encoding="utf-8",
        )
        h5 = ws / "h5" / "src" / "bridge"
        h5.mkdir(parents=True)
        (h5 / "index.ts").write_text(
            "const handler = window.webkit?.messageHandlers?.furfbBridge;\n"
            "window.furfbBridgeCallback = (id, data) => {};\n",
            encoding="utf-8",
        )
        _write_register(ws, "Monthio", "furfb")
        issues = collect_native_shell_naming_violations(ws)
        assert any("桥通道名不一致" in i for i in issues)
        assert any("桥回调名不一致" in i for i in issues)


def test_bridge_channel_match_no_violation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        bridge_dir = ws / "ios" / "Yeario" / "Bridge"
        bridge_dir.mkdir(parents=True)
        (bridge_dir / "WebBridgeHandler.swift").write_text(
            'config.userContentController.add(handler, name: "yearioBridge")\n'
            "let script = \"window.yearioBridgeCallback('\\(id)', \\(json));\"\n",
            encoding="utf-8",
        )
        h5 = ws / "h5" / "src" / "bridge"
        h5.mkdir(parents=True)
        (h5 / "index.ts").write_text(
            "const nativeHandler = 'yearioBridge';\n"
            "const handler = window.webkit?.messageHandlers?.[nativeHandler];\n"
            "window.yearioBridgeCallback = (id, envelope) => {};\n",
            encoding="utf-8",
        )
        _write_register(ws, "Yeario", "zpwcq")
        issues = collect_native_shell_naming_violations(ws)
        assert not any("桥通道名不一致" in i for i in issues)
        assert not any("桥回调名不一致" in i for i in issues)


def test_apply_replacements_handles_static_func_signatures() -> None:
    from batch.native_shell_obfuscation import _apply_replacements

    replacements = {
        "static func install()": "static func ddclinstallDeflavorBi()",
        "static func apply(to webView: WKWebView)": (
            "static func ptbdapplyDeflavorCl(to webView: WKWebView)"
        ),
    }
    source = "\n".join(
        [
            "    static func install() {",
            "    static func apply(to webView: WKWebView) {",
        ]
    )
    out = _apply_replacements(source, replacements)
    assert "static func install()" not in out
    assert "ddclinstallDeflavorBi()" in out
    assert "ptbdapplyDeflavorCl(to webView: WKWebView)" in out
