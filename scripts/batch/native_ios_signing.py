"""Validate Manual iOS signing settings for Swift/OC H5 shells."""

from __future__ import annotations

import json
import re
from pathlib import Path

_IPHONEOS_TEAM_RE = re.compile(
    r'"DEVELOPMENT_TEAM\[sdk=iphoneos\*\]"\s*=\s*([^;]+);'
)
_IPHONEOS_PROFILE_RE = re.compile(
    r'"PROVISIONING_PROFILE_SPECIFIER\[sdk=iphoneos\*\]"\s*=\s*([^;]+);'
)


def _read_registration(workspace: Path) -> dict:
    reg = workspace / "本包登记信息.json"
    if not reg.is_file():
        return {}
    try:
        data = json.loads(reg.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _pbx_value(raw: str) -> str:
    return raw.strip().strip('"')


def collect_native_ios_signing_violations(workspace: Path) -> list[str]:
    """Ensure workspace uses Manual signing with bundle id + provisioning profile."""
    issues: list[str] = []
    ws = workspace.resolve()
    pbx_files = list(ws.glob("*.xcodeproj/project.pbxproj"))
    if not pbx_files:
        return issues

    text = pbx_files[0].read_text(encoding="utf-8", errors="replace")
    reg = _read_registration(ws)
    expected_bundle = str(reg.get("bundleId") or "").strip()
    expected_team = str(reg.get("teamId") or "").strip()
    expected_profile = str(reg.get("provisioningProfile") or "").strip()

    if "CODE_SIGN_STYLE = Automatic" in text:
        issues.append("Signing: CODE_SIGN_STYLE 仍为 Automatic（须 Manual）")
    if "CODE_SIGN_STYLE = Manual" not in text:
        issues.append("Signing: 缺少 CODE_SIGN_STYLE = Manual")

    if expected_bundle and expected_bundle not in text:
        issues.append(f"Signing: pbxproj 未包含登记 bundleId {expected_bundle}")

    if re.search(r"DEVELOPMENT_TEAM = ;", text):
        issues.append("Signing: DEVELOPMENT_TEAM 损坏（`DEVELOPMENT_TEAM = ;`）")

    team_match = _IPHONEOS_TEAM_RE.search(text)
    if expected_team:
        if not team_match:
            issues.append(
                "Signing: pbxproj 缺少 DEVELOPMENT_TEAM[sdk=iphoneos*]（真机 Team 必填）",
            )
        elif _pbx_value(team_match.group(1)) != expected_team:
            issues.append(
                f"Signing: DEVELOPMENT_TEAM[sdk=iphoneos*] 与登记 teamId 不一致 "
                f"({_pbx_value(team_match.group(1))} != {expected_team})",
            )

    profile_match = _IPHONEOS_PROFILE_RE.search(text)
    if expected_profile:
        if not profile_match:
            issues.append(
                "Signing: pbxproj 缺少 PROVISIONING_PROFILE_SPECIFIER[sdk=iphoneos*]",
            )
        elif _pbx_value(profile_match.group(1)) != expected_profile:
            issues.append(
                f"Signing: PROVISIONING_PROFILE_SPECIFIER[sdk=iphoneos*] 与登记不一致 "
                f"({_pbx_value(profile_match.group(1))} != {expected_profile})",
            )
    elif not profile_match:
        issues.append("Signing: 缺少 PROVISIONING_PROFILE_SPECIFIER[sdk=iphoneos*]")

    project_yml = ws / "project.yml"
    if project_yml.is_file():
        yml = project_yml.read_text(encoding="utf-8", errors="replace")
        if "CODE_SIGN_STYLE: Automatic" in yml:
            issues.append("Signing: project.yml 仍为 Automatic")
        if "CODE_SIGN_STYLE: Manual" not in yml:
            issues.append("Signing: project.yml 缺少 CODE_SIGN_STYLE: Manual")
        if expected_profile and expected_profile not in yml:
            issues.append(
                f"Signing: project.yml 未包含 provisioningProfile {expected_profile}",
            )
        if expected_team and expected_team not in yml:
            issues.append(f"Signing: project.yml 未包含 teamId {expected_team}")

    if expected_team and not reg.get("teamId"):
        issues.append("Signing: 本包登记信息.json 缺少 teamId")

    if expected_profile and not reg.get("provisioningProfile"):
        issues.append("Signing: 本包登记信息.json 缺少 provisioningProfile")

    return issues
