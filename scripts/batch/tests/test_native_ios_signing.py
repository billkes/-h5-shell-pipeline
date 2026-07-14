"""Tests for Manual iOS signing validation and pbxproj patching."""

from __future__ import annotations

import json
from pathlib import Path

from batch.config import BatchConfig
from batch.native_ios_signing import collect_native_ios_signing_violations
from batch.xcode_delivery import _patch_ios_app_build_settings


def _write_min_pbxproj(path: Path, *, style: str, team: str, profile: str, bundle: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""
/* Begin XCBuildConfiguration section */
\t\t243B183422D0415881220658 /* Debug */ = {{
\t\t\tisa = XCBuildConfiguration;
\t\t\tbuildSettings = {{
\t\t\t\tCODE_SIGN_STYLE = {style};
\t\t\t\tDEVELOPMENT_TEAM = "";
\t\t\t\t"DEVELOPMENT_TEAM[sdk=iphoneos*]" = {team};
\t\t\t\tPROVISIONING_PROFILE_SPECIFIER = "";
\t\t\t\t"PROVISIONING_PROFILE_SPECIFIER[sdk=iphoneos*]" = {profile};
\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = {bundle};
\t\t\t}};
\t\t\tname = Debug;
\t\t}};
/* End XCBuildConfiguration section */
""".strip(),
        encoding="utf-8",
    )


def test_patch_ios_app_build_settings_manual_profile(tmp_path: Path) -> None:
    pbx = tmp_path / "App.xcodeproj" / "project.pbxproj"
    _write_min_pbxproj(
        pbx,
        style="Automatic",
        team="WRONGTEAM",
        profile="oldProfile",
        bundle="com.example.old",
    )
    original = pbx.read_text(encoding="utf-8")
    cfg = BatchConfig(
        xcode_bundle_id="test.duckegg.ios",
        xcode_development_team="995HYU84B7",
        xcode_provisioning_profile="duckeggkaifaProfile",
    )
    patched = _patch_ios_app_build_settings(original, cfg)
    assert "CODE_SIGN_STYLE = Manual;" in patched
    assert 'DEVELOPMENT_TEAM = "";' in patched
    assert '"DEVELOPMENT_TEAM[sdk=iphoneos*]" = 995HYU84B7;' in patched
    assert 'PROVISIONING_PROFILE_SPECIFIER = "";' in patched
    assert '"PROVISIONING_PROFILE_SPECIFIER[sdk=iphoneos*]" = duckeggkaifaProfile;' in patched
    assert "PRODUCT_BUNDLE_IDENTIFIER = test.duckegg.ios;" in patched


def test_collect_native_ios_signing_violations_ok(tmp_path: Path) -> None:
    ws = tmp_path / "Teavoo"
    ws.mkdir()
    pbx = ws / "Teavoo.xcodeproj" / "project.pbxproj"
    _write_min_pbxproj(
        pbx,
        style="Manual",
        team="995HYU84B7",
        profile="duckeggkaifaProfile",
        bundle="test.duckegg.ios",
    )
    (ws / "project.yml").write_text(
        "\n".join(
            [
                "CODE_SIGN_STYLE: Manual",
                'DEVELOPMENT_TEAM: ""',
                '"DEVELOPMENT_TEAM[sdk=iphoneos*]": 995HYU84B7',
                'PROVISIONING_PROFILE_SPECIFIER: ""',
                '"PROVISIONING_PROFILE_SPECIFIER[sdk=iphoneos*]": "duckeggkaifaProfile"',
            ]
        ),
        encoding="utf-8",
    )
    (ws / "本包登记信息.json").write_text(
        json.dumps(
            {
                "bundleId": "test.duckegg.ios",
                "teamId": "995HYU84B7",
                "provisioningProfile": "duckeggkaifaProfile",
            }
        ),
        encoding="utf-8",
    )
    assert collect_native_ios_signing_violations(ws) == []


def test_collect_native_ios_signing_violations_automatic(tmp_path: Path) -> None:
    ws = tmp_path / "Teavoo"
    ws.mkdir()
    pbx = ws / "Teavoo.xcodeproj" / "project.pbxproj"
    _write_min_pbxproj(
        pbx,
        style="Automatic",
        team="995HYU84B7",
        profile='""',
        bundle="test.duckegg.ios",
    )
    issues = collect_native_ios_signing_violations(ws)
    assert any("Automatic" in issue for issue in issues)
    assert any("Manual" in issue for issue in issues)
