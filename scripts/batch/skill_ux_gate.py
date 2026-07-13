"""UX checklist gate — script-level checks against H5 entry.htm."""

from __future__ import annotations

import json
import re
from pathlib import Path

from batch.h5_site_paths import site_entry_rel


def _resolve_entry(project: Path) -> Path | None:
    reg_path = project / "本包登记信息.json"
    if not reg_path.is_file():
        for path in project.rglob("*_entry.htm"):
            return path
        return None
    try:
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(reg, dict):
        return None
    rel = site_entry_rel(reg, str(reg.get("prefix") or "app"))
    entry = project / rel
    if entry.is_file():
        return entry
    from batch.h5_bundle_gate import bundle_entry_path

    bundle_rel = bundle_entry_path(reg)
    if bundle_rel:
        entry = project / bundle_rel
        if entry.is_file():
            return entry
    return None


def verify_skill_ux_gate(project: Path) -> list[str]:
    """Cross-check entry.htm against ux-checklist expectations."""
    issues: list[str] = []
    entry = _resolve_entry(project)
    if entry is None:
        return issues

    text = entry.read_text(encoding="utf-8", errors="replace")
    style_blocks = re.findall(r"<style[^>]*>([\s\S]*?)</style>", text, re.I)
    css = "\n".join(style_blocks)

    if not re.search(r"prefers-reduced-motion", css, re.I):
        issues.append("UX Gate: 缺少 prefers-reduced-motion 媒体查询")

    if re.search(r"font-size:\s*(\d+)px", css):
        for m in re.finditer(r"font-size:\s*(\d+)px", css):
            if int(m.group(1)) < 12:
                issues.append("UX Gate: 存在 font-size < 12px 的正文样式")
                break

    if re.search(r"outline:\s*none", css, re.I) and not re.search(r":focus-visible", css, re.I):
        issues.append("UX Gate: outline:none 但未提供 :focus-visible 替代")

    if "cursor:pointer" not in css.replace(" ", "") and "cursor: pointer" not in css:
        issues.append("UX Gate WARN: 未检测到 cursor:pointer（可点击元素）")

    ux_path = None
    for p in project.glob("design-system/*/ux-checklist.md"):
        ux_path = p
        break
    if ux_path is None:
        issues.append("UX Gate: 缺少 design-system/*/ux-checklist.md")

    return issues
