"""Tests for native shell obfuscation directory renames."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS))

from batch.native_shell_obfuscation import apply_native_shell_obfuscation, build_native_obfuscation_map  # noqa: E402

_V2_META = {
    "ruleKey": "consonant_core",
    "packageSeed": "beydd",
    "affix": "prefix",
    "lengthRange": [4, 12],
    "joinStyles": {"swiftClass": "PascalCase"},
}


def test_obfuscation_renames_prefix_shell_when_bridge_already_renamed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        app = ws / "ios" / "Peopio"
        shell = app / "beydd_shell"
        shell.mkdir(parents=True)
        (shell / "WebBridgeHandler.swift").write_text(
            "import WebKit\nfinal class WebBridgeHandler: NSObject, WKScriptMessageHandler {}\n",
            encoding="utf-8",
        )
        (app / "PeopioApp.swift").write_text(
            "import SwiftUI\n@main struct PeopioApp: App { var body: some Scene { WindowGroup {} } }\n",
            encoding="utf-8",
        )
        (app / "Info.plist").write_text("<plist></plist>", encoding="utf-8")
        (ws / "project.yml").write_text("name: Peopio\n", encoding="utf-8")
        (ws / "本包登记信息.json").write_text(
            json.dumps(
                {
                    "appName": "Peopio",
                    "packType": "h5_swift_shell",
                    "shellRuntime": "swift",
                    "codeAntiCorrelation": {
                        "dartCodePrefix": "beydd",
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

        obf = build_native_obfuscation_map(ws, app_name="Peopio")
        changed = apply_native_shell_obfuscation(ws, app_name="Peopio")

        assert (app / obf.shell_dir).is_dir()
        assert not shell.is_dir()
        assert any(obf.shell_dir in entry for entry in changed)
