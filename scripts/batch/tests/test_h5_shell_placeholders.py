"""Tests for H5 shell placeholder assets."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from batch.h5_post_delivery import run_post_delivery  # noqa: E402
from batch.h5_shell_placeholders import (  # noqa: E402
    LAUNCH_PLACEHOLDER_ASSET_URI,
    apply_shell_placeholders,
    collect_placeholder_violations,
    legacy_h5_launch_path,
)
from batch.h5_site_paths import LAUNCH_PLACEHOLDER_ASSET_URI as SITE_LAUNCH_URI  # noqa: E402


def _stub_workspace(tmp: Path, *, prefix: str = "klhvl") -> Path:
    ws = tmp / "DemoApp"
    icon_set = ws / "DemoApp" / "Assets.xcassets" / "AppIcon.appiconset"
    icon_set.mkdir(parents=True)
    (icon_set / "Contents.json").write_text(
        json.dumps(
            {
                "images": [
                    {
                        "filename": "AppIcon-1024.png",
                        "idiom": "universal",
                        "platform": "ios",
                        "size": "1024x1024",
                    }
                ],
                "info": {"version": 1, "author": "xcode"},
            }
        ),
        encoding="utf-8",
    )
    launch_set = ws / "DemoApp" / "Assets.xcassets" / "launch_placeholder.imageset"
    launch_set.mkdir(parents=True)
    (launch_set / "Contents.json").write_text(
        json.dumps(
            {
                "images": [{"filename": "launch_placeholder.png", "idiom": "universal", "scale": "3x"}],
                "info": {"version": 1, "author": "xcode"},
            }
        ),
        encoding="utf-8",
    )
    (ws / "本包登记信息.json").write_text(
        json.dumps(
            {
                "appSlug": "demoapp",
                "h5EntryUrl": "https://test.example/demoapp/",
                "h5EntryUrlProd": "https://test.example/demoapp/",
                "codeAntiCorrelation": {"dartCodePrefix": prefix},
                "launchPlaceholderAsset": LAUNCH_PLACEHOLDER_ASSET_URI,
            }
        ),
        encoding="utf-8",
    )
    h5_main = ws / "h5" / "src"
    h5_main.mkdir(parents=True)
    (h5_main / "main.ts").write_text(
        "bridge.call('shellReady', {});\nfunction boot() {}\n",
        encoding="utf-8",
    )
    return ws


def test_launch_placeholder_asset_uri_is_native_only() -> None:
    assert LAUNCH_PLACEHOLDER_ASSET_URI == SITE_LAUNCH_URI
    assert LAUNCH_PLACEHOLDER_ASSET_URI.startswith("native:")


def test_apply_shell_placeholders_writes_native_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = _stub_workspace(Path(tmp))
        changed = apply_shell_placeholders(ws, prefix="klhvl", force=True)
        assert changed
        icon = ws / "DemoApp" / "Assets.xcassets" / "AppIcon.appiconset" / "AppIcon-1024.png"
        launch = ws / "DemoApp" / "Assets.xcassets" / "launch_placeholder.imageset" / "launch_placeholder.png"
        h5_launch = legacy_h5_launch_path(ws, "klhvl")
        assert icon.is_file() and icon.stat().st_size > 1000
        assert launch.is_file() and launch.stat().st_size > 1000
        assert h5_launch is not None and not h5_launch.is_file()
        assert collect_placeholder_violations(ws) == []


def test_collect_placeholder_violations_flags_legacy_h5_mirror() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = _stub_workspace(Path(tmp))
        legacy = legacy_h5_launch_path(ws, "klhvl")
        assert legacy is not None
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_bytes(b"legacy")
        issues = collect_placeholder_violations(ws)
        assert any("冗余 H5 launch 副本" in i for i in issues)


def test_post_delivery_fix_clears_factory_assets() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ws = _stub_workspace(Path(tmp))
        icon = ws / "DemoApp" / "Assets.xcassets" / "AppIcon.appiconset" / "AppIcon-1024.png"
        icon.write_bytes(b"\x00" * 104_895)
        fixes, issues = run_post_delivery(ws, fix=True, sync_dev_url=False)
        assert fixes
        assert icon.stat().st_size != 104_895
        assert "AppIcon 仍为厂包真图" not in "\n".join(issues)
