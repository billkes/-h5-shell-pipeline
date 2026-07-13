"""Bridge Plaza QA purchase SKU — fixed test product id 311400."""

from __future__ import annotations

import re
from pathlib import Path

PLAZA_TEST_PURCHASE_PRODUCT_ID = "311400"

_PURCHASE_LITERAL_RE = re.compile(
    r"action\s*===\s*['\"]purchase['\"][\s\S]{0,160}?\{[^}]*productId\s*:\s*['\"]([^'\"]+)['\"]",
    re.I,
)
_PLAZA_CONST_RE = re.compile(
    r"PLAZA_TEST_PURCHASE_PRODUCT_ID\s*=\s*['\"]([^'\"]+)['\"]",
    re.I,
)
_PLAZA_CONST_USE_RE = re.compile(
    r"action\s*===\s*['\"]purchase['\"][\s\S]{0,160}?productId\s*:\s*PLAZA_TEST_PURCHASE_PRODUCT_ID\b",
    re.I,
)


def find_plaza_view(project: Path) -> Path | None:
    from batch.h5_vite_gate import h5_src_dir

    for name in ("PlazaView.vue", "BridgePlazaView.vue"):
        path = h5_src_dir(project) / "views" / name
        if path.is_file():
            return path
    return None


def plaza_view_text(project: Path) -> str:
    from batch.h5_vite_gate import h5_src_dir

    parts: list[str] = []
    for name in ("PlazaView.vue", "PlazaView.logic.ts"):
        path = h5_src_dir(project) / "views" / name
        if path.is_file():
            try:
                parts.append(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    if parts:
        return "\n".join(parts)
    path = find_plaza_view(project)
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _plaza_purchase_product_id(text: str) -> str | None:
    const_match = _PLAZA_CONST_RE.search(text)
    if const_match and _PLAZA_CONST_USE_RE.search(text):
        return const_match.group(1).strip()
    literal = _PURCHASE_LITERAL_RE.search(text)
    if literal:
        return literal.group(1).strip()
    return None


def collect_h5_plaza_purchase_violations(project: Path) -> list[str]:
    """Hard gate: Bridge Plaza `purchase` must use QA SKU 311400."""
    from batch.screen_inventory import project_includes_route

    if not project_includes_route(project, "/plaza"):
        return []
    text = plaza_view_text(project)
    if not text:
        return []
    if "purchase" not in text:
        return []
    pid = _plaza_purchase_product_id(text)
    if pid is None:
        return [
            "Bridge Plaza purchase 须传 productId "
            f"{PLAZA_TEST_PURCHASE_PRODUCT_ID!r}（QA 测购 SKU）"
        ]
    if pid != PLAZA_TEST_PURCHASE_PRODUCT_ID:
        return [
            f"Bridge Plaza purchase 须用 {PLAZA_TEST_PURCHASE_PRODUCT_ID!r}，"
            f"当前为 {pid!r}（商店页用 catalog，广场测购固定 311400）"
        ]
    return []
