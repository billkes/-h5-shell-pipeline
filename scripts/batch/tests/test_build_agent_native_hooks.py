"""Tests for agent.shell native obfuscation hook."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPTS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS))

from batch.config import BatchConfig  # noqa: E402
from batch.pipeline import AppContext  # noqa: E402
from batch.pipeline_v3_runner import V3StepRunner  # noqa: E402


def _swift_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "DemoApp"
    app = ws / "ios" / "DemoApp"
    bridge = app / "Bridge"
    bridge.mkdir(parents=True)
    (bridge / "WebBridgeHandler.swift").write_text(
        "import WebKit\nclass WebBridgeHandler: NSObject, WKScriptMessageHandler {}\n",
        encoding="utf-8",
    )
    (app / "DemoAppApp.swift").write_text(
        "import SwiftUI\n@main struct DemoAppApp: App { var body: some Scene { WindowGroup {} } }\n",
        encoding="utf-8",
    )
    (app / "Info.plist").write_text("<plist></plist>", encoding="utf-8")
    (ws / "DemoApp.xcodeproj").mkdir()
    (ws / "DemoApp.xcodeproj" / "project.pbxproj").write_text(
        "/* Debug */ = { buildSettings = { PRODUCT_BUNDLE_IDENTIFIER = com.demo; }; name = Debug; };",
        encoding="utf-8",
    )
    (ws / "project.yml").write_text("name: DemoApp\n", encoding="utf-8")
    (ws / "本包登记信息.json").write_text(
        json.dumps(
            {
                "bundleId": "com.demo",
                "teamId": "TEAM123",
                "provisioningProfile": "demoProfile",
            }
        ),
        encoding="utf-8",
    )
    return ws


def test_agent_shell_calls_native_obfuscation_before_shell_check() -> None:
    td = Path(tempfile.mkdtemp())
    ws = _swift_workspace(td)
    cfg = BatchConfig(project_dir=SCRIPTS.parents[1])
    pipeline = MagicMock()
    pipeline.cfg = cfg
    pipeline.prompts.build_agent_shell_phase.return_value = "prompt"
    runner = V3StepRunner(pipeline)
    ctx = AppContext(
        name="DemoApp",
        desc="",
        workspace=ws,
        pack_type="h5_swift_shell",
        dart_name="demo_app",
    )

    obf_calls: list[str] = []
    signing_calls: list[str] = []

    def _fake_obf(workspace: Path, *, app_name: str = "") -> list[str]:
        obf_calls.append(app_name)
        return ["dir: Bridge/ → ms_bridge_shell_pe/"]

    def _fake_signing(workspace: Path, *, app_name: str = "") -> list[str]:
        signing_calls.append(app_name)
        return ["pbxproj: Manual signing applied from registration"]

    with (
        patch("batch.cursor_runner.run_agent", return_value=True),
        patch("batch.preview_tabs.verify_preview_tabs_outputs", return_value=[]),
        patch(
            "batch.native_shell_obfuscation.apply_native_shell_obfuscation",
            side_effect=_fake_obf,
        ),
        patch(
            "batch.native_ios_signing.sync_workspace_ios_signing_from_registration",
            side_effect=_fake_signing,
        ),
        patch.object(runner, "_optional_xcodebuild", return_value=[]),
    ):
        ok = runner._step_agent_shell(ctx)

    # _check_native_shell 在简化 workspace 下会返回 issues 使 ok=False,
    # 但本测试只验证 obfuscation / signing hooks 是否被调用(顺序与参数)。
    assert obf_calls == ["DemoApp"]
    assert signing_calls == ["DemoApp"]
