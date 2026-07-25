"""Tests for native shell merge-apply into V3 workspaces."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from batch.h5_site_paths import LAUNCH_PLACEHOLDER_ASSET_URI  # noqa: E402
from batch.h5_shell_placeholders import (  # noqa: E402
    apply_shell_placeholders,
    collect_placeholder_violations,
    legacy_h5_launch_path,
)
from batch.native_shell_apply import (  # noqa: E402
    clear_stale_native_shell,
    ensure_native_shell_scaffold,
    find_xcode_projects,
    has_launch_screen,
    has_root_xcode_project,
    native_shell_layout_ok,
)
from batch.tests.pipeline_fixtures import sample_csv_row  # noqa: E402


def _write_combo(ws: Path, prefix: str = "mocko") -> None:
    (ws / "本包代码组合.json").write_text(
        json.dumps({"dartCodePrefix": prefix}, ensure_ascii=False),
        encoding="utf-8",
    )
    (ws / "本包登记信息.json").write_text(
        json.dumps(
            {
                "appName": "Mockoo",
                "shellRuntime": "oc",
                "launchPlaceholderAsset": LAUNCH_PLACEHOLDER_ASSET_URI,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_find_xcode_projects_prefers_shallow() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        nested = ws / "Nested" / "App.xcodeproj"
        nested.mkdir(parents=True)
        (ws / "Root.xcodeproj").mkdir()
        found = find_xcode_projects(ws)
        assert found[0].name == "Root.xcodeproj"


def test_clear_stale_native_shell_removes_nested_xcodeproj() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        nested = ws / "Temioo" / "Temioo.xcodeproj"
        nested.mkdir(parents=True)
        removed = clear_stale_native_shell(ws, "Temioo")
        assert not find_xcode_projects(ws)
        assert any("Temioo.xcodeproj" in item for item in removed)


def test_ensure_native_shell_scaffold_merges_at_workspace_root() -> None:
    template = ROOT / "data" / "static" / "templates" / "oc_shell" / "{{APP_NAME}}"
    apply_script = ROOT / "data" / "static" / "templates" / "oc_shell" / "apply.py"
    if not template.is_dir() or not apply_script.is_file():
        return

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "Mockoo"
        ws.mkdir()
        _write_combo(ws, "mocko")
        (ws / "h5").mkdir()
        (ws / "skill-input").mkdir()

        merged = ensure_native_shell_scaffold(
            project_dir=ROOT,
            workspace=ws,
            row=sample_csv_row("Mockoo", pack_type="h5_oc_shell"),
            bundle_id="test.duckegg.ios",
            force=True,
        )
        apply_shell_placeholders(ws, prefix="mocko", force=True)
        assert merged
        assert has_root_xcode_project(ws)
        assert native_shell_layout_ok(ws, "Mockoo")
        assert (ws / "Mockoo.xcodeproj" / "project.pbxproj").is_file()
        launch = ws / "Mockoo" / "Assets.xcassets" / "launch_placeholder.imageset" / "launch_placeholder.png"
        assert launch.is_file()
        legacy = legacy_h5_launch_path(ws, "mocko")
        assert legacy is not None and not legacy.is_file()
        assert not collect_placeholder_violations(ws)


def test_ensure_native_shell_scaffold_idempotent_when_layout_ok() -> None:
    template = ROOT / "data" / "static" / "templates" / "oc_shell" / "{{APP_NAME}}"
    if not template.is_dir():
        return

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "Mockoo"
        ws.mkdir()
        _write_combo(ws, "mocko")
        (ws / "h5").mkdir()

        first = ensure_native_shell_scaffold(
            project_dir=ROOT,
            workspace=ws,
            row=sample_csv_row("Mockoo", pack_type="h5_oc_shell"),
            bundle_id="test.duckegg.ios",
            force=True,
        )
        assert first
        second = ensure_native_shell_scaffold(
            project_dir=ROOT,
            workspace=ws,
            row=sample_csv_row("Mockoo", pack_type="h5_oc_shell"),
            bundle_id="test.duckegg.ios",
            force=False,
        )
        assert second == []


def test_ensure_native_shell_scaffold_swift_uses_skeleton_without_xcodegen() -> None:
    skeleton = ROOT / "data" / "static" / "templates" / "ios_app_skeleton" / "{{APP_NAME}}"
    shell = ROOT / "data" / "static" / "templates" / "swift_shell" / "{{APP_NAME}}"
    if not skeleton.is_dir() or not shell.is_dir():
        return

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "Mockoo"
        ws.mkdir()
        (ws / "本包代码组合.json").write_text(
            json.dumps({"dartCodePrefix": "mocko"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (ws / "本包登记信息.json").write_text(
            json.dumps(
                {
                    "appName": "Mockoo",
                    "shellRuntime": "swift",
                    "launchPlaceholderAsset": LAUNCH_PLACEHOLDER_ASSET_URI,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (ws / "h5").mkdir()

        merged = ensure_native_shell_scaffold(
            project_dir=ROOT,
            workspace=ws,
            row=sample_csv_row("Mockoo", pack_type="h5_swift_shell"),
            bundle_id="test.duckegg.ios",
            force=True,
        )
        assert merged
        assert any("ios_app_skeleton" in item for item in merged)
        assert has_root_xcode_project(ws)
        assert native_shell_layout_ok(ws, "Mockoo")
        pbx = ws / "Mockoo.xcodeproj" / "project.pbxproj"
        assert pbx.is_file()
        text = pbx.read_text(encoding="utf-8")
        assert "path = ios/Mockoo;" in text
        assert "ContentView.swift" not in text
        assert (ws / "ios" / "Mockoo").is_dir()
        assert (ws / "project.yml").is_file()


def test_has_launch_screen_swift_accepts_ui_launch_screen() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        ios = ws / "ios" / "Mockoo"
        ios.mkdir(parents=True)
        (ios / "Info.plist").write_text(
            "<key>UILaunchScreen</key><dict><key>UIColorName</key><string>LaunchBackground</string></dict>",
            encoding="utf-8",
        )
        colorset = ios / "Assets.xcassets" / "LaunchBackground.colorset"
        colorset.mkdir(parents=True)
        (colorset / "Contents.json").write_text("{}", encoding="utf-8")
        assert has_launch_screen(ws, "swift")
        assert not has_launch_screen(ws, "oc")


def test_has_launch_screen_accepts_storyboard() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        story = ws / "ios" / "Mockoo" / "Base.lproj"
        story.mkdir(parents=True)
        (story / "LaunchScreen.storyboard").write_text("<document/>", encoding="utf-8")
        assert has_launch_screen(ws, "swift")
        assert has_launch_screen(ws, "oc")
