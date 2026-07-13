"""English-only copy helpers for visible H5 UI (scaffold + gates)."""

from __future__ import annotations

import json
import re
from pathlib import Path

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
_PRODUCT_FLOW_RE = re.compile(r"Product flow:\s*(.+?)(?:\s*;\s*|$)", re.I | re.S)

H5_UI_LOCALE = "en-US"


def contains_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text or ""))


def english_ui_text(text: str, *, fallback: str, max_len: int = 120) -> str:
    """Return *text* when it has no CJK; otherwise *fallback* (trimmed)."""
    cleaned = (text or "").strip()
    if cleaned and not contains_cjk(cleaned):
        return cleaned[:max_len]
    return fallback[:max_len]


def english_product_flow(product: dict[str, object]) -> str:
    direct = str(product.get("productFlow") or product.get("product_flow") or "").strip()
    if direct and not contains_cjk(direct):
        return direct
    angle = str(product.get("themeAngle") or "").strip()
    lower = angle.lower()
    marker = "product flow:"
    idx = lower.find(marker)
    if idx >= 0:
        flow = angle[idx + len(marker) :].strip()
        if flow and not contains_cjk(flow):
            return flow
    match = _PRODUCT_FLOW_RE.search(angle)
    if match:
        flow = match.group(1).strip()
        if flow and not contains_cjk(flow):
            return flow
    return ""


def _read_product(project: Path) -> dict[str, object]:
    ctx = project / "skill-input" / "context.json"
    if not ctx.is_file():
        return {}
    try:
        data = json.loads(ctx.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    product = data.get("product") if isinstance(data, dict) else None
    return product if isinstance(product, dict) else {}


def english_core_scene(product: dict[str, object], *, default: str) -> str:
    scene = english_ui_text(str(product.get("coreScene") or ""), fallback="", max_len=48)
    if scene:
        return scene
    flow = english_product_flow(product).lower()
    if any(token in flow for token in ("presentation", "speech", "lecture", "teleprompter")):
        return "Strictly timed classroom lectures"
    return default


def english_local_feature(product: dict[str, object], *, default: str) -> str:
    feature = english_ui_text(str(product.get("localFeature") or ""), fallback="", max_len=120)
    if feature:
        return feature
    flow = english_product_flow(product).lower()
    if "pace monitoring" in flow or "overtime" in flow:
        return "Live pace monitoring with structural overtime alerts"
    if "teleprompter" in flow:
        return "Time-mapped teleprompter with live pace monitoring"
    return default


def hero_copy(project: Path) -> dict[str, str]:
    product = _read_product(project)
    return {
        "{{HERO_EYEBROW}}": english_core_scene(
            product, default="Timed rehearsal coach"
        ),
        "{{HERO_TITLE}}": "Map your script to the clock",
        "{{HERO_SUB}}": english_local_feature(
            product,
            default=(
                "Import, time-map sections, rehearse with live pace monitoring — all on-device."
            ),
        ),
    }


def list_copy(project: Path) -> dict[str, str]:
    product = _read_product(project)
    return {
        "{{LIST_EYEBROW}}": english_core_scene(product, default="Session archive"),
        "{{LIST_HEADLINE}}": "Review by course",
        "{{LIST_SUB}}": english_local_feature(
            product,
            default=(
                "Filter rehearsal runs, spot overtime patterns, jump into run detail or export rhythm cards."
            ),
        ),
    }


def settings_copy(project: Path) -> dict[str, str]:
    product = _read_product(project)
    return {
        "{{SETTINGS_EYEBROW}}": english_core_scene(product, default="App preferences"),
        "{{SETTINGS_HEADLINE}}": "Settings & support",
        "{{SETTINGS_SUB}}": english_local_feature(
            product,
            default="Manage coins, legal documents, and rehearsal data on this device.",
        ),
    }


def welcome_copy(project: Path, *, app_name: str) -> dict[str, str]:
    product = _read_product(project)
    flow = english_product_flow(product)
    bullet2 = "Time-mapped teleprompter with live pace monitoring"
    if flow:
        parts = [p.strip() for p in flow.split(";") if p.strip()]
        if len(parts) >= 2 and not contains_cjk(parts[1]):
            bullet2 = parts[1][:80]
    return {
        "{{APP_NAME}}": app_name,
        "{{WELCOME_INTRO}}": english_local_feature(
            product,
            default="Offline rehearsal control for timed university presentations.",
        ),
        "{{TRUST_BULLET_1}}": english_core_scene(
            product, default="Offline rehearsal — no account or cloud sync required"
        ),
        "{{TRUST_BULLET_2}}": bullet2,
    }


def collect_h5_ui_cjk_violations(project: Path) -> list[str]:
    """Flag CJK in user-visible H5 Vue/TS (exclude legal bundled payloads)."""
    from batch.h5_vite_gate import h5_src_dir

    src = h5_src_dir(project)
    if not src.is_dir():
        return []
    issues: list[str] = []
    for path in sorted(src.rglob("*")):
        if not path.is_file() or path.suffix not in {".vue", ".ts"}:
            continue
        rel = str(path.relative_to(src))
        if rel.startswith("legal/") and "legal_bundled" in rel:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("//") or line.strip().startswith("*"):
                continue
            if contains_cjk(line):
                issues.append(f"H5 UI 禁止中文: {rel}:{i}")
                break
    return issues


def collect_h5_demo_seed_cjk_violations(project: Path) -> list[str]:
    """Hard gate: demo/seed/store defaults and Vue placeholders must be English."""
    from batch.h5_vite_gate import h5_src_dir

    src = h5_src_dir(project)
    if not src.is_dir():
        return []
    issues: list[str] = []
    seed_markers = ("demoplan", "seeddemo", "createblank", "placeholder=", "demo_")
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(src)).replace("\\", "/")
        if path.suffix not in {".ts", ".vue"}:
            continue
        if rel.startswith("legal/"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lower = text.lower()
        if path.suffix == ".ts" and not rel.startswith("store/"):
            if not any(m in lower for m in seed_markers):
                continue
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if not contains_cjk(line):
                continue
            if path.suffix == ".vue" and "placeholder=" not in line and "{{" in line:
                continue
            issues.append(f"H5 demo/seed 禁止中文: {rel}:{i}")
            break
    return issues


def collect_h5_stack_layout_violations(project: Path) -> list[str]:
    """Stack routes should use shared TopBar + page-stack (not ad-hoc wizard bars)."""
    from batch.h5_vite_gate import h5_src_dir

    src = h5_src_dir(project)
    views = src / "views"
    if not views.is_dir():
        return []
    issues: list[str] = []
    tab_roots = {
        "HubView.vue",
        "RunsView.vue",
        "SettingsView.vue",
        "InsightsView.vue",
        "SplashView.vue",
        "WelcomeView.vue",
        "PlazaView.vue",
    }
    for path in sorted(views.glob("*.vue")):
        if path.name in tab_roots:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "-wizard-bar" in text:
            issues.append(f"H5 stack 页须用 TopBar+page-stack，禁止 wizard-bar: {path.name}")
        if "<TopBar" not in text and "topbar__back" in text:
            issues.append(f"H5 stack 页须复用 TopBar 组件: {path.name}")
        if "<TopBar" in text and "page-stack" not in text and "page-full" not in text:
            issues.append(f"H5 stack 页内容区须用 page-stack 或 page-full: {path.name}")
    return issues


def collect_h5_welcome_demo_violations(project: Path) -> list[str]:
    """Hard gate: Welcome must not expose demo/sample seed CTAs."""
    from batch.h5_vite_gate import find_welcome_view_text, h5_src_dir

    welcome = find_welcome_view_text(project)
    if not welcome:
        return []
    logic_path = h5_src_dir(project) / "views" / "WelcomeView.logic.ts"
    audit = welcome
    if logic_path.is_file():
        try:
            audit += "\n" + logic_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            pass
    patterns = (
        r"showDemo",
        r"loadDemo",
        r"seedDemoData",
        r"Load demo",
        r"Try sample",
        r"demo plan",
        r"action--secondary",
    )
    issues: list[str] = []
    for pat in patterns:
        if re.search(pat, audit, re.I):
            issues.append("Welcome 页禁止 Load demo / showDemo / loadDemo 按钮")
            break
    return issues
