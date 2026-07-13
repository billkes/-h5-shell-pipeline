"""Native IAP policy: forbid local StoreKit Configuration (*.storekit)."""

from __future__ import annotations

import re
from pathlib import Path

_STOREKIT_FILE_REF = re.compile(
    r"^\t\t[A-F0-9]+ /\* .*\.storekit \*/ = "
    r"\{isa = PBXFileReference;[^\n]*\n",
    re.MULTILINE,
)
_STOREKIT_GROUP_CHILD = re.compile(
    r"^\t\t\t\t[A-F0-9]+ /\* .*\.storekit \*/,\n",
    re.MULTILINE,
)
_STOREKIT_SCHEME_BLOCK = re.compile(
    r"\s*<StoreKitConfigurationFileReference(?:[\s\S]*?</StoreKitConfigurationFileReference>|[^>]*/>)\n?",
)


def strip_storekit_from_pbxproj(text: str) -> str:
    text = _STOREKIT_FILE_REF.sub("", text)
    return _STOREKIT_GROUP_CHILD.sub("", text)


def strip_storekit_from_xcscheme(text: str) -> str:
    return _STOREKIT_SCHEME_BLOCK.sub("\n", text)


def collect_storekit_violations(workspace: Path) -> list[str]:
    """Return human-readable issues when workspace violates no-storekit policy."""
    issues: list[str] = []
    ws = workspace.resolve()

    for path in sorted(ws.rglob("*.storekit")):
        if "/build/" in str(path):
            continue
        rel = path.relative_to(ws)
        issues.append(f"禁止本地 StoreKit 配置: {rel}")

    for pbx in ws.rglob("project.pbxproj"):
        if "/build/" in str(pbx):
            continue
        text = pbx.read_text(encoding="utf-8", errors="replace")
        if ".storekit" in text:
            rel = pbx.relative_to(ws)
            issues.append(f"project.pbxproj 仍引用 .storekit: {rel}")

    for scheme in ws.rglob("*.xcscheme"):
        if "/build/" in str(scheme):
            continue
        text = scheme.read_text(encoding="utf-8", errors="replace")
        if "StoreKitConfigurationFileReference" in text:
            rel = scheme.relative_to(ws)
            issues.append(f"xcscheme 仍绑定 StoreKitConfiguration: {rel}")

    return issues


def enforce_no_storekit(workspace: Path) -> list[str]:
    """Remove forbidden StoreKit artifacts; return paths that were changed."""
    changed: list[str] = []
    ws = workspace.resolve()

    for path in list(ws.rglob("*.storekit")):
        if "/build/" in str(path):
            continue
        path.unlink()
        changed.append(str(path.relative_to(ws)))

    for pbx in ws.rglob("project.pbxproj"):
        if "/build/" in str(pbx):
            continue
        original = pbx.read_text(encoding="utf-8", errors="replace")
        cleaned = strip_storekit_from_pbxproj(original)
        if cleaned != original:
            pbx.write_text(cleaned, encoding="utf-8")
            changed.append(str(pbx.relative_to(ws)))

    for scheme in ws.rglob("*.xcscheme"):
        if "/build/" in str(scheme):
            continue
        original = scheme.read_text(encoding="utf-8", errors="replace")
        cleaned = strip_storekit_from_xcscheme(original)
        if cleaned != original:
            scheme.write_text(cleaned, encoding="utf-8")
            changed.append(str(scheme.relative_to(ws)))

    return changed
