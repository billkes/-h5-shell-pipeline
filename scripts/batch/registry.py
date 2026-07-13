"""Registry and similarity checks for content packs."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


def format_already_used_block(registry_path: Path) -> str:
    if not registry_path.is_file():
        return (
            "No packages registered yet; this may be the first. "
            "Still ensure your theme and innovation feature are "
            "specific and well-defined."
        )
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        packages = data.get("packages") or []
    except (json.JSONDecodeError, OSError):
        packages = []
    if not packages:
        return (
            "No packages registered yet; this may be the first. "
            "Still ensure your theme and innovation feature are "
            "specific and well-defined."
        )
    lines = [
        "Already used — do NOT duplicate (your package must differ in "
        "theme, Innovation Tab/main feature, and layout/tabs):"
    ]
    for pkg in packages:
        name = pkg.get("name") or "?"
        theme = (pkg.get("themeAngle") or pkg.get("description") or "")[:60]
        feed = str(pkg.get("feedLayout") or "")[:80]
        detail = str(pkg.get("detailLayout") or "")[:80]
        profile = str(pkg.get("profileLayout") or "")[:60]
        layout_bits = " | ".join(
            bit for bit in (feed, detail, profile) if bit
        )
        if pkg.get("mainFeature") and pkg.get("tab1Name"):
            main = (pkg.get("mainFeature") or "?")[:50]
            tabs = " / ".join(
                str(pkg.get(k) or "?")
                for k in ("tab1Name", "tab2Name", "tab3Name")
            )
            lines.append(
                f'- {name}: theme "{theme}" | mainFeature "{main}" | tabs {tabs}'
                + (f" | layouts: {layout_bits}" if layout_bits else "")
            )
        else:
            lines.append(
                f'- {name}: theme "{theme}" | Innovation Tab '
                f'"{pkg.get("innovationTabName") or "?"}" '
                f'({str(pkg.get("innovationTabSummary") or "")[:50]})'
                + (f" | layouts: {layout_bits}" if layout_bits else "")
            )
    return "\n".join(lines)


def _norm(value: object) -> str:
    return str(value or "").strip().lower()


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z]+", _norm(value)))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = a & b
    union = a | b
    return len(inter) / len(union) if union else 0.0


def load_registry_packages(registry_path: Path) -> list[dict]:
    if not registry_path.is_file():
        return []
    try:
        reg = json.loads(registry_path.read_text(encoding="utf-8"))
        packages = reg.get("packages") or []
        return [p for p in packages if isinstance(p, dict)]
    except (json.JSONDecodeError, OSError):
        return []


def _similarity_conflicts(new_pkg: dict, existing_pkg: dict) -> list[str]:
    """Return conflict reason strings (without package name prefix)."""
    new_theme = new_pkg.get("themeAngle") or new_pkg.get("description") or ""
    new_tokens = _tokens(new_theme)
    new_tab = _norm(new_pkg.get("innovationTabName"))
    new_feed = _norm(new_pkg.get("feedLayout"))
    new_detail = _norm(new_pkg.get("detailLayout"))
    new_profile = _norm(new_pkg.get("profileLayout"))
    new_main = _tokens(str(new_pkg.get("mainFeature") or ""))

    ex_theme = existing_pkg.get("themeAngle") or existing_pkg.get("description") or ""
    ex_tokens = _tokens(ex_theme)
    ex_tab = _norm(existing_pkg.get("innovationTabName"))
    ex_feed = _norm(existing_pkg.get("feedLayout"))
    ex_detail = _norm(existing_pkg.get("detailLayout"))
    ex_main = _tokens(str(existing_pkg.get("mainFeature") or ""))

    conflicts: list[str] = []
    if new_tokens and ex_tokens and _jaccard(new_tokens, ex_tokens) >= 0.4:
        conflicts.append("themeAngle too similar")
    if new_main and ex_main and _jaccard(new_main, ex_main) >= 0.45:
        conflicts.append("mainFeature too similar")
    if new_tab and ex_tab and new_tab == ex_tab:
        conflicts.append(
            f'same Innovation Tab name "{existing_pkg.get("innovationTabName")}"'
        )
    elif (new_feed, new_detail, new_profile) == (
        ex_feed,
        ex_detail,
        _norm(existing_pkg.get("profileLayout")),
    ) and any((new_feed, new_detail, new_profile)):
        conflicts.append("same layout triple")
    elif new_feed and ex_feed and _jaccard(_tokens(new_feed), _tokens(ex_feed)) >= 0.35:
        conflicts.append("feedLayout too similar")
    elif (
        new_detail
        and ex_detail
        and _jaccard(_tokens(new_detail), _tokens(ex_detail)) >= 0.35
    ):
        conflicts.append("detailLayout too similar")
    return conflicts


def check_package_dict_similarity(
    new_pkg: dict,
    existing_packages: list[dict],
    *,
    skip_names: frozenset[str] | None = None,
) -> tuple[bool, str]:
    """Return (ok, conflict_report) for a registry-like package dict."""
    skip = skip_names or frozenset()
    conflicts: list[str] = []
    for pkg in existing_packages:
        name = str(pkg.get("name") or "?")
        if name in skip:
            continue
        for reason in _similarity_conflicts(new_pkg, pkg):
            conflicts.append(f"{name}: {reason}")
    if not conflicts:
        return True, ""
    report = "CONFLICTS (too similar; change theme/dimensions in task.csv prep):\n"
    report += "\n".join(f"  - {c}" for c in conflicts)
    return False, report


def registry_probe_from_task_row(row: object) -> dict:
    """Map task.csv row → registry-like dict for prep-phase similarity."""
    theme_angle = str(getattr(row, "theme_angle", "") or "").strip()
    theme_cn = str(getattr(row, "theme_cn", "") or "").strip()
    core_scene = str(getattr(row, "core_scene", "") or "").strip()
    local_feature = str(getattr(row, "local_feature", "") or "").strip()
    product_flow = str(getattr(row, "product_flow", "") or "").strip()
    track = str(getattr(row, "track", "") or "").strip()
    description = " ".join(p for p in (theme_cn, core_scene, local_feature) if p)
    return {
        "name": str(getattr(row, "name", "") or ""),
        "themeAngle": theme_angle or description,
        "description": description or theme_angle,
        "mainFeature": str(getattr(row, "main_feature", "") or ""),
        "feedLayout": product_flow,
        "detailLayout": local_feature,
        "profileLayout": track,
        "innovationTabName": "",
    }


def check_registry_similarity(
    registry_path: Path,
    package_path: Path,
) -> tuple[bool, str]:
    """Return (ok, conflict_report). ok=True means no conflict."""
    existing = load_registry_packages(registry_path)
    try:
        new_pkg = json.loads(package_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return True, ""
    if not isinstance(new_pkg, dict):
        return True, ""
    return check_package_dict_similarity(new_pkg, existing)


def append_to_registry(
    registry_path: Path,
    package_path: Path,
    workspace: Path,
    app_name: str,
    app_desc: str,
    *,
    batch_id: str = "",
) -> bool:
    try:
        reg = json.loads(registry_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        reg = {"packages": []}
    packages = reg.get("packages") or []
    try:
        pkg = json.loads(package_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    pkg["name"] = app_name
    pkg["description"] = app_desc
    pkg["registeredAt"] = datetime.now().strftime("%Y-%m-%d")
    if batch_id:
        pkg["batchId"] = batch_id
    combo = workspace / "本包代码组合.json"
    if combo.is_file():
        try:
            pkg["codeAntiCorrelation"] = json.loads(
                combo.read_text(encoding="utf-8")
            )
            pkg["usedAt"] = pkg["registeredAt"]
        except json.JSONDecodeError:
            pass
    packages.append(pkg)
    reg["packages"] = packages
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(reg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f">>> 已写入登记表: {app_name}")
    return True
