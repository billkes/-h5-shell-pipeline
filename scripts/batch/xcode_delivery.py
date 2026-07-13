"""Apply fixed Xcode delivery settings (signing, AppIcon, PrivacyInfo, IAP)."""

from __future__ import annotations

import re
import secrets
import shutil
from pathlib import Path

from batch.config import BatchConfig

_PRIVACY_INDEX_RE = re.compile(r"(\d+)")


def parse_privacy_file_index(label: str) -> int | None:
    """Parse CSV 隐私文件 value like ``4号`` → ``4``."""
    match = _PRIVACY_INDEX_RE.search((label or "").strip())
    if not match:
        return None
    index = int(match.group(1))
    if 1 <= index <= 10:
        return index
    return None


def _runner_pbxproj(ios_root: Path) -> Path | None:
    candidates = [
        p
        for p in ios_root.rglob("project.pbxproj")
        if "build" not in p.parts and "DerivedData" not in p.parts
    ]
    return candidates[0] if candidates else None


def _pbxproj_braces_balanced(text: str) -> bool:
    """Lightweight balance check for OpenStep pbxproj text.

    Strips ``/* ... */`` comments and ``"..."`` strings before counting
    ``{}`` / ``()`` pairs. Imbalance means the file was edited incorrectly
    and Xcode/xcodebuild will fail to parse it.
    """
    no_comments = re.sub(r"/\*[\s\S]*?\*/", "", text)
    no_strings = re.sub(r'"(?:[^"\\]|\\.)*"', '""', no_comments)
    return (
        no_strings.count("{") == no_strings.count("}")
        and no_strings.count("(") == no_strings.count(")")
    )


def apply_default_app_icon(ios_root: Path, assets_dir: Path) -> bool:
    """Copy shared AppIcon into Runner/Assets.xcassets/AppIcon.appiconset."""
    source = assets_dir / "default-app-icon.png"
    template = assets_dir / "AppIcon.appiconset" / "Contents.json"
    icon_sets = list(ios_root.rglob("AppIcon.appiconset"))
    if not icon_sets:
        print("  >>> AppIcon: 未找到 AppIcon.appiconset，跳过")
        return False
    if not source.is_file():
        print(f"  >>> AppIcon: 缺少原图 {source.name}，跳过")
        return False

    icon_set = icon_sets[0]
    for old in icon_set.iterdir():
        if old.name != "Contents.json":
            old.unlink(missing_ok=True)
    names = ("AppIcon.png", "AppIcon-dark.png", "AppIcon-tinted.png")
    for name in names:
        shutil.copy2(source, icon_set / name)
    if template.is_file():
        shutil.copy2(template, icon_set / "Contents.json")
    print(f"  >>> AppIcon 已写入 {icon_set.relative_to(ios_root)}")
    return True


def apply_privacy_manifest(
    ios_root: Path,
    assets_dir: Path,
    privacy_index: int,
) -> bool:
    """Copy PrivacyInfo_vN.xcprivacy → Runner/PrivacyInfo.xcprivacy."""
    src = assets_dir / "PrivacyInfo" / f"PrivacyInfo_v{privacy_index}.xcprivacy"
    if not src.is_file():
        print(f"  >>> PrivacyInfo: 模板不存在 PrivacyInfo_v{privacy_index}.xcprivacy")
        return False

    runner = ios_root / "Runner"
    runner.mkdir(parents=True, exist_ok=True)
    dest = runner / "PrivacyInfo.xcprivacy"
    shutil.copy2(src, dest)
    pbx = _runner_pbxproj(ios_root)
    if pbx is None:
        print("  >>> PrivacyInfo: project.pbxproj 未找到")
        return False

    text = pbx.read_text(encoding="utf-8", errors="replace")
    updated = _ensure_privacy_in_pbxproj(text)
    if updated != text:
        pbx.write_text(updated, encoding="utf-8")
    print(f"  >>> PrivacyInfo 已应用 v{privacy_index} → Runner/PrivacyInfo.xcprivacy")
    return True


def _ensure_privacy_in_pbxproj(text: str) -> str:
    if "PrivacyInfo.xcprivacy" in text:
        return text

    file_ref = secrets.token_hex(12).upper()
    build_file = secrets.token_hex(12).upper()

    build_entry = (
        f"\t\t{build_file} /* PrivacyInfo.xcprivacy in Resources */ = "
        f"{{isa = PBXBuildFile; fileRef = {file_ref} "
        f"/* PrivacyInfo.xcprivacy */; }};\n"
    )
    text = text.replace(
        "/* End PBXBuildFile section */",
        build_entry + "/* End PBXBuildFile section */",
    )

    file_entry = (
        f"\t\t{file_ref} /* PrivacyInfo.xcprivacy */ = "
        f"{{isa = PBXFileReference; lastKnownFileType = text.xml; "
        f"path = PrivacyInfo.xcprivacy; sourceTree = \"<group>\"; }};\n"
    )
    text = text.replace(
        "/* End PBXFileReference section */",
        file_entry + "/* End PBXFileReference section */",
    )

    runner_group = re.search(
        r"(97C146F01CF9000F007C117D /\* Runner \*/ = \{[\s\S]*?children = \(\n)"
        r"([\s\S]*?)(\t\t\t\);\n\t\t\tpath = Runner;)",
        text,
    )
    if runner_group:
        insert = f"\t\t\t\t{file_ref} /* PrivacyInfo.xcprivacy */,\n"
        text = (
            text[: runner_group.end(2)]
            + insert
            + text[runner_group.end(2) :]
        )

    resources = re.search(
        r"(97C146EC1CF9000F007C117D /\* Resources \*/ = \{[\s\S]*?files = \(\n)"
        r"([\s\S]*?)(\t\t\t\);\n\t\t\trunOnlyForDeploymentPostprocessing)",
        text,
    )
    if resources:
        insert = (
            f"\t\t\t\t{build_file} /* PrivacyInfo.xcprivacy in Resources */,\n"
        )
        text = text[: resources.end(2)] + insert + text[resources.end(2) :]

    return text


def _ensure_storekit_in_pbxproj(text: str) -> str:
    if "StoreKit.framework" in text:
        return text

    file_ref = secrets.token_hex(12).upper()
    build_file = secrets.token_hex(12).upper()

    build_entry = (
        f"\t\t{build_file} /* StoreKit.framework in Frameworks */ = "
        f"{{isa = PBXBuildFile; fileRef = {file_ref} "
        f"/* StoreKit.framework */; }};\n"
    )
    text = text.replace(
        "/* End PBXBuildFile section */",
        build_entry + "/* End PBXBuildFile section */",
    )

    file_entry = (
        f"\t\t{file_ref} /* StoreKit.framework */ = "
        f"{{isa = PBXFileReference; lastKnownFileType = wrapper.framework; "
        f"name = StoreKit.framework; "
        f"path = System/Library/Frameworks/StoreKit.framework; "
        f"sourceTree = SDKROOT; }};\n"
    )
    text = text.replace(
        "/* End PBXFileReference section */",
        file_entry + "/* End PBXFileReference section */",
    )

    frameworks_group = re.search(
        r"(E7CF0873D2D39B358DCE462C /\* Frameworks \*/ = \{[\s\S]*?children = \(\n)"
        r"([\s\S]*?)(\t\t\t\);\n\t\t\tname = Frameworks;)",
        text,
    )
    if frameworks_group:
        insert = f"\t\t\t\t{file_ref} /* StoreKit.framework */,\n"
        text = (
            text[: frameworks_group.end(2)]
            + insert
            + text[frameworks_group.end(2) :]
        )
    else:
        alt = re.search(
            r"(/\* Frameworks \*/ = \{[\s\S]*?children = \(\n)([\s\S]*?)(\t\t\t\);)",
            text,
        )
        if alt:
            insert = f"\t\t\t\t{file_ref} /* StoreKit.framework */,\n"
            text = text[: alt.end(2)] + insert + text[alt.end(2) :]

    runner_frameworks = re.search(
        r"(97C146EB1CF9000F007C117D /\* Frameworks \*/ = \{[\s\S]*?files = \(\n)"
        r"([\s\S]*?)(\t\t\t\);\n\t\t\trunOnlyForDeploymentPostprocessing)",
        text,
    )
    if runner_frameworks:
        insert = (
            f"\t\t\t\t{build_file} /* StoreKit.framework in Frameworks */,\n"
        )
        text = (
            text[: runner_frameworks.end(2)]
            + insert
            + text[runner_frameworks.end(2) :]
        )

    return text


def _ensure_iap_capability(text: str) -> str:
    """Inject InAppPurchase capability into Runner target attributes.

    Replaces only the inner body of the Runner target's attribute dict and
    keeps its closing ``};`` intact, so the surrounding TargetAttributes /
    attributes / PBXProject dicts stay balanced.
    """
    if "com.apple.InAppPurchase" in text:
        return text

    pattern = re.compile(
        r"(97C146ED1CF9000F007C117D = \{\n)"
        r"([\s\S]*?)"
        r"(\n\t{5}\};)"
    )
    match = pattern.search(text)
    if not match:
        return text

    body = (
        "\t\t\t\t\t\tCreatedOnToolsVersion = 7.3.1;\n"
        "\t\t\t\t\t\tLastSwiftMigration = 1100;\n"
        "\t\t\t\t\t\tSystemCapabilities = {\n"
        "\t\t\t\t\t\t\tcom.apple.InAppPurchase = {\n"
        "\t\t\t\t\t\t\t\tenabled = 1;\n"
        "\t\t\t\t\t\t\t};\n"
        "\t\t\t\t\t\t};"
    )
    return (
        text[: match.start()]
        + match.group(1)
        + body
        + match.group(3)
        + text[match.end() :]
    )


def _set_or_replace_setting(block: str, key: str, value: str) -> str:
    pattern = rf"(\t\t\t\t{re.escape(key)} = )[^;]+;"
    if re.search(pattern, block):
        return re.sub(pattern, lambda m: f"{m.group(1)}{value};", block)
    insert_at = block.rfind("\t\t\t};")
    if insert_at == -1:
        return block
    line = f"\t\t\t\t{key} = {value};\n"
    return block[:insert_at] + line + block[insert_at:]


def _patch_runner_build_settings(text: str, cfg: BatchConfig) -> str:
    """Patch Runner target Debug/Release/Profile build settings."""
    if not cfg.xcode_bundle_id:
        return text

    def patch_block(match: re.Match[str]) -> str:
        block = match.group(0)
        if "ASSETCATALOG_COMPILER_APPICON_NAME" not in block:
            return block
        block = _set_or_replace_setting(block, "CODE_SIGN_STYLE", "Manual")
        block = _set_or_replace_setting(block, "DEVELOPMENT_TEAM", '""')
        if cfg.xcode_development_team:
            block = _set_or_replace_setting(
                block,
                '"DEVELOPMENT_TEAM[sdk=iphoneos*]"',
                cfg.xcode_development_team,
            )
        block = _set_or_replace_setting(
            block,
            "PRODUCT_BUNDLE_IDENTIFIER",
            cfg.xcode_bundle_id,
        )
        block = _set_or_replace_setting(
            block,
            "PROVISIONING_PROFILE_SPECIFIER",
            '""',
        )
        if cfg.xcode_provisioning_profile:
            block = _set_or_replace_setting(
                block,
                '"PROVISIONING_PROFILE_SPECIFIER[sdk=iphoneos*]"',
                cfg.xcode_provisioning_profile,
            )
        block = _set_or_replace_setting(
            block,
            "SUPPORTED_PLATFORMS",
            '"iphoneos iphonesimulator"',
        )
        block = _set_or_replace_setting(
            block,
            "SUPPORTS_MACCATALYST",
            "NO",
        )
        block = _set_or_replace_setting(
            block,
            "SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD",
            "NO",
        )
        block = _set_or_replace_setting(
            block,
            "SUPPORTS_XR_DESIGNED_FOR_IPHONE_IPAD",
            "NO",
        )
        block = _set_or_replace_setting(block, "TARGETED_DEVICE_FAMILY", "1")
        return block

    for config_name in ("Debug", "Release", "Profile"):
        pattern = (
            rf"(/\* {config_name} \*/ = \{{[\s\S]*?"
            rf"\n\t\t\tname = {config_name};\n\t\t\}};)"
        )
        text = re.sub(pattern, patch_block, text)
    return text


def _patch_project_wide_settings(text: str) -> str:
    replacements = {
        "SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD = YES": (
            "SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD = NO"
        ),
        "SUPPORTS_MACCATALYST = YES": "SUPPORTS_MACCATALYST = NO",
        "SUPPORTS_XR_DESIGNED_FOR_IPHONE_IPAD = YES": (
            "SUPPORTS_XR_DESIGNED_FOR_IPHONE_IPAD = NO"
        ),
        'TARGETED_DEVICE_FAMILY = "1,2"': "TARGETED_DEVICE_FAMILY = 1",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _remove_scene_delegate(ios_root: Path) -> None:
    for pattern in ("SceneDelegate.swift", "SceneDelegate.m", "SceneDelegate.h"):
        for path in ios_root.rglob(pattern):
            if "build" in path.parts:
                continue
            path.unlink(missing_ok=True)

    plist_files = [
        p
        for p in ios_root.rglob("Info.plist")
        if "build" not in p.parts and "Pods" not in p.parts
    ]
    if not plist_files:
        return
    try:
        import plistlib

        plist = plist_files[0]
        with plist.open("rb") as f:
            data = plistlib.load(f)
        if "UIApplicationSceneManifest" in data:
            del data["UIApplicationSceneManifest"]
            with plist.open("wb") as f:
                plistlib.dump(data, f)
    except (OSError, ValueError, ImportError):
        pass


def apply_xcode_delivery_settings(
    cfg: BatchConfig,
    ios_root: Path,
    *,
    privacy_file_label: str = "",
) -> None:
    """Apply AppIcon, PrivacyInfo, signing, destinations, and IAP capability."""
    assets_dir = cfg.static_dir
    apply_default_app_icon(ios_root, assets_dir)

    privacy_index = parse_privacy_file_index(privacy_file_label)
    if privacy_index is not None:
        apply_privacy_manifest(ios_root, assets_dir, privacy_index)
    elif privacy_file_label.strip():
        print(f"  >>> PrivacyInfo: 无法解析「{privacy_file_label}」，跳过")

    pbx = _runner_pbxproj(ios_root)
    if pbx is None:
        print("  >>> Xcode: 未找到 project.pbxproj")
        return

    original = pbx.read_text(encoding="utf-8", errors="replace")
    text = _patch_project_wide_settings(original)
    text = _patch_runner_build_settings(text, cfg)
    text = _ensure_storekit_in_pbxproj(text)
    text = _ensure_iap_capability(text)
    if not _pbxproj_braces_balanced(text):
        backup = pbx.with_suffix(pbx.suffix + ".broken")
        backup.write_text(text, encoding="utf-8")
        pbx.write_text(original, encoding="utf-8")
        raise RuntimeError(
            "project.pbxproj 注入后括号失衡，已回滚原文件；"
            f"调试副本: {backup}"
        )
    pbx.write_text(text, encoding="utf-8")

    if cfg.xcode_bundle_id:
        print(f"  >>> Bundle ID = {cfg.xcode_bundle_id}")
    if cfg.xcode_provisioning_profile:
        print(f"  >>> Provisioning Profile = {cfg.xcode_provisioning_profile}")

    _remove_scene_delegate(ios_root)
