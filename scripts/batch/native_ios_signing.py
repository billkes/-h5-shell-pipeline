"""Validate and sync Manual iOS signing settings for Swift/OC H5 shells."""

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

__all__ = [
    "collect_native_ios_signing_violations",
    "sync_workspace_ios_signing_from_registration",
]


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


def _yaml_key_pattern(key: str) -> str:
    display = f'"{key}"' if "[" in key else key
    return rf"^(\s*{re.escape(display)}\s*:\s*).*$"


def _yaml_format_value(value: str) -> str:
    value = value.strip()
    if not value:
        return '""'
    if value in ('""', "''"):
        return '""'
    if value[0] in {'"', "'"}:
        return value
    if re.fullmatch(r"[A-Za-z0-9._-]+", value):
        return value
    return json.dumps(value)


def _patch_project_yml_signing(
    project_yml: Path,
    *,
    bundle_id: str,
    team_id: str,
    profile: str,
) -> bool:
    """Patch workspace-root project.yml Manual signing fields from registration."""
    original = project_yml.read_text(encoding="utf-8", errors="replace")
    text = original
    pairs: list[tuple[str, str]] = [("CODE_SIGN_STYLE", "Manual")]
    if bundle_id:
        pairs.append(("PRODUCT_BUNDLE_IDENTIFIER", bundle_id))
    pairs.append(("DEVELOPMENT_TEAM", ""))
    if team_id:
        pairs.append(("DEVELOPMENT_TEAM[sdk=iphoneos*]", team_id))
    pairs.append(("PROVISIONING_PROFILE_SPECIFIER", ""))
    if profile:
        pairs.append(("PROVISIONING_PROFILE_SPECIFIER[sdk=iphoneos*]", profile))

    for key, raw_val in pairs:
        val = _yaml_format_value(raw_val)
        pattern = _yaml_key_pattern(key)
        if re.search(pattern, text, flags=re.MULTILINE):
            text = re.sub(pattern, rf"\g<1>{val}", text, flags=re.MULTILINE)
            continue
        anchor = re.search(r"(\n\s*base:\s*\n)", text)
        if anchor is None:
            continue
        indent = "        "
        line = f"{indent}{key if '[' not in key else json.dumps(key)}: {val}\n"
        text = text[: anchor.end()] + line + text[anchor.end() :]

    if text == original:
        return False
    project_yml.write_text(text, encoding="utf-8")
    return True


def _batch_config_from_registration(reg: dict) -> "BatchConfig":
    from batch.config import BatchConfig

    bundle = str(reg.get("bundleId") or "").strip()
    team = str(reg.get("teamId") or "").strip()
    profile = str(reg.get("provisioningProfile") or "").strip()
    return BatchConfig(
        xcode_bundle_id=bundle or "test.duckegg.ios",
        xcode_development_team=team,
        xcode_provisioning_profile=profile,
    )


def sync_workspace_ios_signing_from_registration(
    workspace: Path,
    *,
    app_name: str = "",
) -> list[str]:
    """Read 本包登记信息.json, patch project.yml, regenerate xcodeproj, patch pbxproj."""
    ws = workspace.resolve()
    reg = _read_registration(ws)
    bundle = str(reg.get("bundleId") or "").strip()
    team = str(reg.get("teamId") or "").strip()
    profile = str(reg.get("provisioningProfile") or "").strip()
    if not (bundle or team or profile):
        return []

    changes: list[str] = []
    project_yml = ws / "project.yml"
    if project_yml.is_file():
        if _patch_project_yml_signing(
            project_yml,
            bundle_id=bundle,
            team_id=team,
            profile=profile,
        ):
            changes.append("project.yml: signing synced from registration")

        from batch.xcode_delivery import regenerate_xcodegen_project

        label = app_name or ws.name
        if regenerate_xcodegen_project(ws, app_name):
            changes.append(f"xcodegen: regenerate {label}.xcodeproj")

    from batch.xcode_delivery import apply_workspace_ios_signing

    cfg = _batch_config_from_registration(reg)
    if apply_workspace_ios_signing(cfg, ws):
        changes.append("pbxproj: Manual signing applied from registration")
    return changes


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
