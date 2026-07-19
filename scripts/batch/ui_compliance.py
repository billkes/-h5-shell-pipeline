"""UI compliance prompt blocks (IAP / Welcome / Bottom Nav — no scheme lottery)."""

from __future__ import annotations

import shutil
from pathlib import Path

IAP_FILE = "ios-iap-page-schemes.md"
IAP_SOURCE = Path("docs") / "内购页方案.md"


def no_scheme_lottery_policy() -> str:
    """Shared rule: no random/fixed scheme catalogs for key surfaces."""
    return (
        "[UI Layout — NO Scheme Lottery]\n"
        "IAP store, Welcome Page, and Bottom Navigation MUST NOT use "
        "fixed scheme IDs (#1–#N), random draws, or legacy scheme markdown "
        "(`ios-bottom-nav-schemes.md`, `ios-welcome-page-schemes.md`, "
        "IAP Page Scheme #N, etc.).\n"
        "Visual layout differentiates per app theme, palette, and "
        "programming-style rules only. Mandatory compliance structures "
        "stay fixed: Welcome = Checkbox + Confirm + `welcomeAccepted`; "
        "IAP = dual sections + catalog SKUs; Bottom nav = 3 tabs from "
        "功能文档.md.\n"
    )


def welcome_gate_block() -> str:
    return (
        "[Welcome Page IS the First-Launch Gate — AUTHORITATIVE]\n"
        "The Welcome Page is the SOLE first-launch Terms & Privacy gate. "
        "It MUST include: consent Checkbox + Confirm button + in-Checkbox "
        "protocol links (Terms / Privacy via `webview_flutter`).\n"
        "- Persist acceptance with SharedPreferences key `welcomeAccepted` "
        "(bool). Router: splash → if `welcomeAccepted == true` then Home "
        "tabs, else Welcome Page.\n"
        "- The Confirm button is the ONLY place that sets "
        "`welcomeAccepted = true` and navigates to Home.\n"
        "- HARD-FORBIDDEN: any AlertDialog / BottomSheet / showDialog / "
        "showModalBottomSheet / second consent card after the Welcome Page.\n"
        "- Profile/Settings Privacy entry is read-only; no second Agree "
        "checkbox there.\n"
        "- Welcome layout/visual is NOT tied to a fixed scheme catalog; "
        "differentiate per project theme and programming-style rules.\n"
        "- Plan MUST author 视觉蓝图.md **Welcome Gate Canon** table + "
        "本包视觉锁.json **welcomeSpec** (layoutVariant + trustBulletSource ≥2). "
        "Implementer MUST fill brand/trust slots — not minimal 18+ line only.\n"
        "- Welcome / Tab1 specs are **product-bound** (coreScene × audience × "
        "topology) — do not copy another pack's onboarding or hub pattern.\n"
        "- Plan MUST author **Hub Home Canon** for Tab 1 (primary zone + empty + "
        "signature binding). H5 gates: `verify_h5_welcome_canon()` / "
        "`verify_h5_hub_canon()`.\n"
    )


def bottom_nav_compliance_block() -> str:
    return (
        "[Bottom Navigation — IMPLEMENTATION]\n"
        "Implement the 3-tab bottom navigation per 功能文档.md (tab names, "
        "icons, and purposes). Visual style (standard bar, floating capsule, "
        "segment rail, etc.) varies per theme — **no bottom-nav scheme "
        "catalog or random draw**.\n"
        "- Wrap the bar in `SafeArea` with bottom minimum inset per product "
        "requirements.\n"
        "- Do NOT copy another batch app's nav skeleton verbatim.\n"
    )


def copy_iap_spec_file(source: Path, workspace: Path) -> None:
    """Copy docs/内购页方案.md into workspace as ios-iap-page-schemes.md."""
    if not source.is_file():
        raise FileNotFoundError(f"IAP 方案文件缺失: {source}")
    shutil.copy2(source, workspace / IAP_FILE)


def main() -> int:
    from batch.config import _project_root

    iap = _project_root() / IAP_SOURCE
    if not iap.is_file():
        print(f"警告: {IAP_SOURCE} 不存在")
        return 1
    print(f"IAP 规范文档就绪: {IAP_SOURCE} → workspace `{IAP_FILE}`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
