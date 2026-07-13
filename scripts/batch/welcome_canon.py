"""Welcome Gate Canon — Plan gate helpers and H5 implementer audits."""

from __future__ import annotations

import json
import re
from pathlib import Path

from batch.h5_vite_gate import find_welcome_view_text, h5_src_dir, is_h5_vite_project, vite_css_text
from batch.pack_type import is_h5_shell

WELCOME_LAYOUT_VARIANTS: frozenset[str] = frozenset(
    {
        "hero-top-card-legal",
        "hero-split-trust",
        "hero-minimal-pinned",
        "hero-hex-brand",
    }
)

_WELCOME_VARIANT_ALIASES: dict[str, str] = {
    "centered-card": "hero-top-card-legal",
    "centered_card": "hero-top-card-legal",
    "card": "hero-top-card-legal",
    "top-card-legal": "hero-top-card-legal",
}


def _normalize_welcome_layout_variant(variant: str) -> str:
    cleaned = variant.strip()
    if cleaned in WELCOME_LAYOUT_VARIANTS:
        return cleaned
    return _WELCOME_VARIANT_ALIASES.get(cleaned, cleaned)

_GLOBAL_INPUT_APPEARANCE_NONE = re.compile(
    r"input\s*,\s*textarea\s*\{[^}]*appearance\s*:\s*none",
    re.I | re.S,
)
_CHECKBOX_EXCLUSION = re.compile(
    r'input:not\(\[type=["\']checkbox["\']\]\)',
    re.I,
)
_WELCOME_MICRO_FONT = re.compile(
    r"\.c-[\w-]*welcome-(?:age|check)[^{]*\{[^}]*font-micro",
    re.I | re.S,
)
_RENDER_WELCOME_FN = re.compile(
    r"function\s+renderWelcome\s*\(\s*\)\s*\{",
    re.I,
)


def _read_register(project: Path) -> dict:
    for name in ("本包登记信息.json", "package-register.json"):
        path = project / name
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}
    return {}


def is_h5_shell_project(project: Path) -> bool:
    return is_h5_shell(str(_read_register(project).get("packType") or ""))


def _extract_render_welcome(render_text: str) -> str:
    match = _RENDER_WELCOME_FN.search(render_text)
    if not match:
        return ""
    start = match.end()
    depth = 1
    i = start
    while i < len(render_text) and depth > 0:
        ch = render_text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return render_text[start:i]
        i += 1
    return render_text[start:]


def _baseline_css_text(project: Path) -> str:
    from batch.h5_legal_ui import resolve_vault_css_text

    return resolve_vault_css_text(project) or ""


def _render_js_text(project: Path) -> str:
    from batch.h5_legal_ui import resolve_vault_js_text

    text, _ = resolve_vault_js_text(project)
    return text or ""


def verify_welcome_blueprint_section(
    visual_text: str,
    *,
    spec_text: str = "",
) -> list[str]:
    """Plan gate: 视觉蓝图 Welcome Gate Canon depth (only if PM lists Welcome)."""
    if spec_text:
        from batch.screen_inventory import parse_h5_routes

        if "/welcome" not in parse_h5_routes(spec_text):
            return []
    issues: list[str] = []
    if not re.search(r"welcome\s+gate\s+canon", visual_text, re.I):
        issues.append("视觉蓝图.md 缺少 V2 章节: Welcome Gate Canon")
        return issues

    section_match = re.search(
        r"(?is)(?:^|\n)#+\s*.*welcome\s+gate\s+canon.*?\n(.*?)(?:\n#+\s|\Z)",
        visual_text,
    )
    section = section_match.group(1) if section_match else ""
    if not section.strip():
        issues.append("视觉蓝图.md Welcome Gate Canon 章节为空")
        return issues

    rows = [
        line
        for line in section.splitlines()
        if line.strip().startswith("|") and not re.match(r"^\s*\|[-:\s|]+\|\s*$", line)
    ]
    if len(rows) < 4:
        issues.append(
            "视觉蓝图.md Welcome Gate Canon 须含槽位表（≥4 行：hero/trust/legal/cta 等）"
        )

    trust_rows = [
        r
        for r in rows
        if re.search(r"trust|trustbullet|卖点", r, re.I)
    ]
    if not trust_rows:
        issues.append("视觉蓝图.md Welcome Gate Canon 须声明 trustBullets 槽位")

    if not re.search(r"labelMedium|bodyLarge|chip-label|14px|14pt", section, re.I):
        issues.append(
            "视觉蓝图.md Welcome Gate Canon 须声明合规文案字号下限（≥ labelMedium / 14px）"
        )
    if re.search(r"font-micro|bodySmall|11px|11pt", section, re.I) and not re.search(
        r"禁止|must not|never|不得|勿",
        section,
        re.I,
    ):
        issues.append(
            "视觉蓝图.md Welcome Gate Canon 若提及 micro/bodySmall 须标注为禁止用于合规区"
        )
    return issues


def verify_welcome_visual_lock(
    data: dict,
    *,
    spec_text: str = "",
) -> list[str]:
    """Plan gate: 本包视觉锁 welcomeSpec (only if PM lists Welcome)."""
    if spec_text:
        from batch.screen_inventory import parse_h5_routes

        if "/welcome" not in parse_h5_routes(spec_text):
            return []
    issues: list[str] = []
    spec = data.get("welcomeSpec")
    if not isinstance(spec, dict) or not spec:
        issues.append("本包视觉锁.json 缺少 V2 字段: welcomeSpec（非空 object）")
        return issues

    variant = str(spec.get("layoutVariant") or "").strip()
    normalized = _normalize_welcome_layout_variant(variant)
    if not variant:
        issues.append("本包视觉锁.json welcomeSpec.layoutVariant 必填")
    elif normalized not in WELCOME_LAYOUT_VARIANTS:
        issues.append(
            f"本包视觉锁.json welcomeSpec.layoutVariant 非法: {variant!r} "
            f"(allowed: {sorted(WELCOME_LAYOUT_VARIANTS)})"
        )

    bullets = spec.get("trustBulletSource")
    if not isinstance(bullets, list) or len(bullets) < 2:
        issues.append("本包视觉锁.json welcomeSpec.trustBulletSource 须为 ≥2 项 array")

    typography = spec.get("typography")
    if isinstance(typography, dict):
        legal = str(typography.get("legalBody") or typography.get("ageNotice") or "")
        if legal and re.search(r"micro|bodySmall|11", legal, re.I):
            issues.append(
                "本包视觉锁.json welcomeSpec.typography 合规区不得使用 micro/bodySmall"
            )
    return issues


def _verify_h5_welcome_vite(project: Path) -> list[str]:
    """Hard audit: WelcomeView.vue checkbox/typography for h5_vite."""
    issues: list[str] = []
    welcome = find_welcome_view_text(project)
    if not welcome:
        issues.append("MISSING: WelcomeView.vue for welcome audit (h5_vite)")
        return issues

    audit_surface = welcome
    logic_path = h5_src_dir(project) / "views" / "WelcomeView.logic.ts"
    if logic_path.is_file():
        try:
            audit_surface += "\n" + logic_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            pass

    if not re.search(
        r"welcome-title|welcome-intro|c-[\w-]+-welcome-title|<h1",
        welcome,
        re.I,
    ):
        issues.append("MISSING: welcome brand title slot (welcome-title / h1)")

    trust_li = len(re.findall(r"welcome-trust[\s\S]*?<li", welcome, re.I))
    plain_li = welcome.count("<li>")
    if trust_li < 2 and plain_li < 2:
        issues.append("MISSING: ≥2 trust bullet rows in WelcomeView")

    if 'type="checkbox"' not in welcome:
        issues.append("MISSING: consent checkbox in WelcomeView")

    if not re.search(r":disabled|disabled.*Continue|Continue.*disabled", welcome, re.I):
        issues.append("MISSING: disabled Agree CTA until checkbox checked")

    if not re.search(
        r"#/legal|legal\?doc=|path:\s*['\"]/legal|/legal|openLegal\s*\(|Privacy Agreement",
        audit_surface,
        re.I,
    ):
        issues.append("MISSING: Privacy/Terms legal links in WelcomeView")

    if not re.search(r"\b18\b|18\s*\+|older", welcome, re.I):
        issues.append("MISSING: 18+ age notice in WelcomeView")

    from batch.h5_ui_copy import collect_h5_welcome_demo_violations

    issues.extend(collect_h5_welcome_demo_violations(project))

    css = vite_css_text(project)
    if css:
        if _GLOBAL_INPUT_APPEARANCE_NONE.search(css) and not _CHECKBOX_EXCLUSION.search(css):
            issues.append(
                "global.css: input,textarea { appearance:none } 未排除 checkbox/radio"
            )
        if _WELCOME_MICRO_FONT.search(css):
            issues.append("welcome-age/check must not use --font-micro token")

    return issues


def verify_h5_welcome_canon(project: Path) -> list[str]:
    """Hard audit: H5 renderWelcome + baseline checkbox/typography."""
    project = project.expanduser().resolve()
    issues: list[str] = []

    if not is_h5_shell_project(project):
        return issues

    from batch.screen_inventory import project_includes_route

    if not project_includes_route(project, "/welcome"):
        return issues

    if is_h5_vite_project(project):
        return _verify_h5_welcome_vite(project)

    render_text = _render_js_text(project)
    if not render_text:
        issues.append("MISSING: *_render.js for welcome audit")
        return issues

    welcome = _extract_render_welcome(render_text)
    if not welcome:
        issues.append("MISSING: renderWelcome() in render module")
        return issues

    if not re.search(r"welcome-title|welcome-intro|c-[\w-]+-welcome-title", welcome, re.I):
        issues.append("MISSING: welcome brand title slot (welcome-title / welcome-intro)")

    trust_li = len(re.findall(r"welcome-trust[\s\S]*?<li", welcome, re.I))
    plain_li = welcome.count("<li>")
    if trust_li < 2 and plain_li < 2:
        issues.append("MISSING: ≥2 trust bullet rows in renderWelcome")

    if 'type="checkbox"' not in welcome:
        issues.append("MISSING: consent checkbox in renderWelcome")

    if not re.search(r"welcome-go|welcome.*disabled|disabled.*Agree", welcome, re.I):
        issues.append("MISSING: disabled Agree CTA until checkbox checked")

    if not re.search(r"#/legal|legal\?doc=", welcome, re.I):
        issues.append("MISSING: Privacy/Terms legal links in renderWelcome")

    if not re.search(r"\b18\b|18\s*\+|older", welcome, re.I):
        issues.append("MISSING: 18+ age notice in renderWelcome")

    css = _baseline_css_text(project)
    if css:
        if _GLOBAL_INPUT_APPEARANCE_NONE.search(css) and not _CHECKBOX_EXCLUSION.search(css):
            issues.append(
                "baseline.css: input,textarea { appearance:none } 未排除 checkbox/radio"
            )
        if _WELCOME_MICRO_FONT.search(css):
            issues.append("welcome-age/check must not use --font-micro token")

    return issues
