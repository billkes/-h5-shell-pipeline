"""Generate kit CSS skeleton from skill.adapt candidate — Agent extends, does not replace."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SKILL_ADAPT_DIR = "skill-adapt"
KIT_SKELETON = "kit-skeleton.css"

_DEFAULT_COMPONENTS: tuple[str, ...] = (
    "btn",
    "btn--secondary",
    "btn--destructive",
    "input",
    "checkbox",
    "checkbox-row",
    "chip",
    "chip--active",
    "snackbar",
    "link",
    "welcome-title",
    "welcome-beat",
    "welcome-trust",
    "welcome-hex",
)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def resolve_prefix(project: Path) -> str:
    reg = _read_json(project / "本包登记信息.json")
    anti = reg.get("codeAntiCorrelation") or {}
    if isinstance(anti, dict):
        prefix = str(anti.get("dartCodePrefix") or "").strip().lower()
        if prefix:
            return prefix
    from batch.workspace import dart_prefix

    return dart_prefix(project).lower()


def _shape_tokens(shape_language: str) -> tuple[str, str, str]:
    """Return (radius, shadow, active_translate) from shape language text."""
    blob = (shape_language or "").lower()
    if "bauhaus" in blob or "包豪斯" in shape_language or "brutal" in blob:
        return "4px", "4px 4px 0 var(--{p}-primary)", "translate(2px, 2px)"
    if "pill" in blob or "squircle" in blob or "soft rounded" in blob:
        return "999px", "0 2px 8px rgba(15, 23, 42, 0.12)", "scale(0.98)"
    return "12px", "0 1px 3px rgba(15, 23, 42, 0.08)", "scale(0.98)"


def build_kit_css_skeleton(
    prefix: str,
    *,
    candidate: dict[str, Any] | None = None,
    designer: dict[str, str] | None = None,
) -> str:
    """Build prefixed kit component CSS skeleton bound to theme tokens."""
    p = prefix.lower()
    candidate = candidate or {}
    designer = designer or {}
    design = candidate.get("designSystem") if "designSystem" in candidate else candidate
    if not isinstance(design, dict):
        design = candidate
    colors = design.get("colors") if isinstance(design.get("colors"), dict) else {}
    typo = design.get("typography") if isinstance(design.get("typography"), dict) else {}
    style = design.get("style") if isinstance(design.get("style"), dict) else {}

    shape_lang = str(
        designer.get("shapeLanguage")
        or style.get("name")
        or style.get("keywords")
        or ""
    )
    radius_tpl, shadow_tpl, active_tpl = _shape_tokens(shape_lang)
    radius = radius_tpl
    shadow = shadow_tpl.format(p=p)
    heading = str(typo.get("heading") or "inherit")
    body = str(typo.get("body") or "inherit")

    lines = [
        f"/* KIT:pipeline — kit skeleton for c-{p}-*; extend in h5/src/styles/kit.css */",
        f"/* Shape: {shape_lang or 'default'} */",
        "",
        f".c-{p}-btn {{",
        "  display: inline-flex;",
        "  align-items: center;",
        "  justify-content: center;",
        "  min-height: 44px;",
        "  padding: 0 16px;",
        f"  border: 2px solid var(--{p}-primary);",
        f"  border-radius: {radius};",
        f"  background: var(--{p}-accent);",
        f"  color: var(--{p}-on-primary);",
        f"  font-family: {body}, system-ui, sans-serif;",
        "  font-size: 14px;",
        "  font-weight: 600;",
        f"  box-shadow: {shadow};",
        "  cursor: pointer;",
        "}",
        "",
        f".c-{p}-btn:active {{",
        f"  transform: {active_tpl};",
        f"  box-shadow: none;",
        "}",
        "",
        f".c-{p}-btn--secondary {{",
        f"  background: var(--{p}-muted);",
        f"  color: var(--{p}-foreground);",
        "}",
        "",
        f".c-{p}-btn--destructive {{",
        f"  background: var(--{p}-destructive);",
        "}",
        "",
        f".c-{p}-btn:disabled {{",
        "  opacity: 0.45;",
        "  pointer-events: none;",
        "}",
        "",
        f".c-{p}-input {{",
        "  width: 100%;",
        "  min-height: 44px;",
        "  padding: 10px 12px;",
        f"  border: 2px solid var(--{p}-border);",
        f"  border-radius: {radius};",
        f"  background: var(--{p}-background);",
        f"  color: var(--{p}-foreground);",
        f"  font-family: {body}, system-ui, sans-serif;",
        "  font-size: 16px;",
        "}",
        "",
        f".c-{p}-checkbox-row {{",
        "  display: flex;",
        "  gap: 8px;",
        "  align-items: flex-start;",
        "  min-height: 44px;",
        f"  color: var(--{p}-foreground);",
        "  font-size: 14px;",
        "  line-height: 1.45;",
        "}",
        "",
        f".c-{p}-checkbox {{",
        "  width: 20px;",
        "  height: 20px;",
        "  margin-top: 2px;",
        "  flex-shrink: 0;",
        "  accent-color: var(--{p}-accent);".format(p=p),
        "}",
        "",
        f".c-{p}-link {{",
        f"  color: var(--{p}-accent);",
        "  text-decoration: underline;",
        "  text-underline-offset: 2px;",
        "  cursor: pointer;",
        "}",
        "",
        f".c-{p}-chip {{",
        "  display: inline-flex;",
        "  align-items: center;",
        "  min-height: 32px;",
        "  padding: 0 12px;",
        f"  border: 1px solid var(--{p}-border);",
        f"  border-radius: {radius};",
        f"  background: var(--{p}-muted);",
        f"  color: var(--{p}-foreground);",
        "  font-size: 12px;",
        "  font-weight: 600;",
        "  cursor: pointer;",
        "}",
        "",
        f".c-{p}-chip--active {{",
        f"  border-color: var(--{p}-primary);",
        f"  box-shadow: {shadow};",
        "}",
        "",
        f".c-{p}-snackbar {{",
        "  position: fixed;",
        "  left: 16px;",
        "  right: 16px;",
        f"  bottom: calc(var(--{p}-page-inset-bottom, 56px) + 12px);",
        "  z-index: 60;",
        "  padding: 12px 16px;",
        f"  border-radius: {radius};",
        f"  background: var(--{p}-primary);",
        f"  color: var(--{p}-on-primary);",
        "  font-size: 14px;",
        f"  box-shadow: {shadow};",
        "}",
        "",
        f".c-{p}-welcome-title {{",
        f"  font-family: {heading}, serif;",
        "  font-size: 28px;",
        "  text-align: center;",
        "  margin: 0 0 12px;",
        f"  color: inherit;",
        "}",
        "",
        f".c-{p}-welcome-beat {{",
        "  font-size: 16px;",
        "  margin-bottom: 12px;",
        "  line-height: 1.5;",
        f"  color: inherit;",
        "}",
        "",
        f".c-{p}-welcome-trust {{",
        "  margin: 16px 0;",
        "  padding-left: 20px;",
        "  font-size: 14px;",
        f"  color: inherit;",
        "}",
        "",
        f".c-{p}-welcome-trust li {{",
        "  margin-bottom: 8px;",
        "}",
        "",
        f".c-{p}-welcome-hex {{",
        "  width: 72px;",
        "  height: 72px;",
        f"  background: var(--{p}-accent);",
        "  clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%);",
        "  margin: 0 auto 16px;",
        "}",
        "",
        "/* KIT:end */",
        "",
    ]
    if colors.get("primary"):
        lines.insert(3, f"/* Primary: {colors.get('primary')} | Accent: {colors.get('accent', '?')} */")
    return "\n".join(lines)


def sync_kit_css_skeleton(project: Path, *, write: bool = True) -> Path | None:
    """Write skill-adapt/kit-skeleton.css from selected-candidate + designer deck."""
    project = project.expanduser().resolve()
    prefix = resolve_prefix(project)
    if not prefix:
        return None

    adapt = project / SKILL_ADAPT_DIR
    candidate = _read_json(adapt / "selected-candidate.json")
    designer_doc = _read_json(adapt / "selected-designer.json")
    designer = designer_doc.get("designerDeckSelections")
    if not isinstance(designer, dict):
        designer = {}

    css = build_kit_css_skeleton(prefix, candidate=candidate, designer=designer)
    out = adapt / KIT_SKELETON
    if write:
        adapt.mkdir(parents=True, exist_ok=True)
        out.write_text(css, encoding="utf-8")
    return out


def kit_skeleton_component_classes(prefix: str) -> list[str]:
    p = prefix.lower()
    return [f"c-{p}-{name}" for name in _DEFAULT_COMPONENTS]


_BARE_BUTTON = re.compile(r"<button\b(?![^>]*\bclass\s*=)[^>]*>", re.I)
_BARE_CHECKBOX = re.compile(
    r"<input\b(?=[^>]*\btype\s*=\s*['\"]checkbox['\"])(?![^>]*\bclass\s*=)[^>]*>",
    re.I,
)
_BARE_INPUT = re.compile(
    r"<input\b(?![^>]*\btype\s*=\s*['\"]checkbox['\"])(?![^>]*\bclass\s*=)[^>]*>",
    re.I,
)
_BARE_LINK = re.compile(r"<a\b(?![^>]*\bclass\s*=)[^>]*>", re.I)


def verify_h5_bare_kit_elements(project: Path) -> list[str]:
    """L1 deflavor: interactive elements must use kit component classes."""
    project = project.expanduser().resolve()
    src = project / "h5" / "src"
    if not src.is_dir():
        return []

    prefix = resolve_prefix(project)
    issues: list[str] = []
    kit_class_hint = f"c-{prefix}-" if prefix else "c-"

    for path in sorted(src.rglob("*.vue")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        template_match = re.search(r"<template[^>]*>([\s\S]*?)</template>", text, re.I)
        if not template_match:
            continue
        tpl = template_match.group(1)
        rel = path.relative_to(project).as_posix()

        if _BARE_BUTTON.search(tpl):
            issues.append(
                f"H5 kit: 裸 <button> 未绑定 {kit_class_hint}btn（{rel}）"
            )
        if _BARE_CHECKBOX.search(tpl):
            issues.append(
                f"H5 kit: 裸 checkbox 未绑定 {kit_class_hint}checkbox（{rel}）"
            )
        if _BARE_INPUT.search(tpl):
            issues.append(
                f"H5 kit: 裸 <input> 未绑定 {kit_class_hint}input（{rel}）"
            )
        for match in _BARE_LINK.finditer(tpl):
            tag = match.group(0)
            if "@click.prevent" in tag or "href=" in tag:
                issues.append(
                    f"H5 kit: 裸 <a> 链接未绑定 {kit_class_hint}link（{rel}）"
                )
                break

    kit_css = project / "h5" / "src" / "styles" / "kit.css"
    if kit_css.is_file() and prefix:
        try:
            css_text = kit_css.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            css_text = ""
        required = (f".c-{prefix}-btn", f".c-{prefix}-input", f".c-{prefix}-checkbox-row")
        for sel in required:
            if sel not in css_text:
                issues.append(f"H5 kit: kit.css 缺少 {sel}")
    elif prefix and (project / "h5" / "package.json").is_file():
        issues.append("H5 kit: 缺少 h5/src/styles/kit.css（须从 skill-adapt/kit-skeleton.css 扩展）")

    return issues
