"""Smoke tests for h5_oc_shell template apply and deck locking."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
TEMPLATE = ROOT / "data" / "static" / "templates" / "oc_shell" / "{{APP_NAME}}"
APPLY = ROOT / "data" / "static" / "templates" / "oc_shell" / "apply.py"


def test_locked_oc_bridge_deck() -> None:
    sys.path.insert(0, str(SCRIPTS))
    from batch.h5_shell_deck import LOCKED_NATIVE_OC_BRIDGE
    from batch.task_schema import COL_WEBVIEW_ENGINE, COL_BRIDGE_CALLBACK_STYLE

    assert LOCKED_NATIVE_OC_BRIDGE[COL_WEBVIEW_ENGINE] == "wkwebview_oc"
    assert "app-callback" in LOCKED_NATIVE_OC_BRIDGE[COL_BRIDGE_CALLBACK_STYLE]


def test_oc_shell_apply_produces_sources() -> None:
    if not TEMPLATE.is_dir() or not APPLY.is_file():
        return
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / "Mockoo"
        cmd = [
            sys.executable,
            str(APPLY),
            "--src",
            str(TEMPLATE),
            "--dst",
            str(dst),
            "--app-name",
            "Mockoo",
            "--prefix",
            "mocko",
            "--app-slug",
            "mockoo",
            "--h5-host",
            "test.darin.beauty",
            "--bundle-id",
            "test.duckegg.ios",
            "--team-id",
            "TEAMTEST",
            "--asset-scheme",
            "mockoasset",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, proc.stderr or proc.stdout
        assert (dst / "Mockoo" / "MockoHostController.m").is_file()
        assert (dst / "Mockoo.xcodeproj" / "project.pbxproj").is_file()
        pbx = (dst / "Mockoo.xcodeproj" / "project.pbxproj").read_text(encoding="utf-8")
        assert "Mockoo" in pbx
        assert "MockoHostController" in pbx
        host = (dst / "Mockoo" / "MockoHostController.m").read_text(encoding="utf-8")
        assert "WKWebView" in host
        assert "shellReady" in host
        assert "app-callback" in host
        assert "mockoasset" in host
        assert not list(dst.rglob("*.storekit"))
        pbx = (dst / "Mockoo.xcodeproj" / "project.pbxproj").read_text(encoding="utf-8")
        assert ".storekit" not in pbx
        scheme = (
            dst / "Mockoo.xcodeproj" / "xcshareddata" / "xcschemes" / "Mockoo.xcscheme"
        ).read_text(encoding="utf-8")
        assert "StoreKitConfigurationFileReference" not in scheme


def test_oc_shell_apply_empty_team_id_valid_pbxproj() -> None:
    if not TEMPLATE.is_dir() or not APPLY.is_file():
        return
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / "EmptyTeam"
        cmd = [
            sys.executable,
            str(APPLY),
            "--src",
            str(TEMPLATE),
            "--dst",
            str(dst),
            "--app-name",
            "EmptyTeam",
            "--prefix",
            "empt",
            "--app-slug",
            "emptyteam",
            "--h5-host",
            "test.darin.beauty",
            "--bundle-id",
            "test.empty.team",
            "--team-id",
            "",
            "--asset-scheme",
            "emptasset",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, proc.stderr or proc.stdout
        pbx = (dst / "EmptyTeam.xcodeproj" / "project.pbxproj").read_text(encoding="utf-8")
        assert "DEVELOPMENT_TEAM = ;" not in pbx
        assert 'DEVELOPMENT_TEAM = "";' not in pbx


def test_pipeline_steps_oc_no_native_check() -> None:
    sys.path.insert(0, str(SCRIPTS))
    from batch.pipeline_steps import steps_for_run

    steps = steps_for_run(pack_type="h5_oc_shell")
    assert "native.check" not in steps
    assert "dev.h5.gate" not in steps
    assert "dev.pubget" not in steps
