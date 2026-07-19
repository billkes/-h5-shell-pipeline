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

WELCOME_IMPL_LOCK = "WELCOME-IMPL:locked"
AGENT_IMPL_LOCK = "AGENT-IMPL:locked"
WELCOME_STUB_MARKER = "WELCOME-STUB:pipeline"
SCAFFOLD_PIPELINE_MARKER = "<!-- SCAFFOLD:pipeline:start"
DEFAULT_WELCOME_LAYOUT_VARIANT = "hero-top-card-legal"

_WELCOME_VARIANT_ALIASES: dict[str, str] = {
    "centered-card": "hero-top-card-legal",
    "centered_card": "hero-top-card-legal",
    "card": "hero-top-card-legal",
    "top-card-legal": "hero-top-card-legal",
    "split-trust": "hero-split-trust",
    "hero-split": "hero-split-trust",
    "minimal-pinned": "hero-minimal-pinned",
    "hex-brand": "hero-hex-brand",
}


def _normalize_welcome_layout_variant(variant: str) -> str:
    cleaned = variant.strip()
    if cleaned in WELCOME_LAYOUT_VARIANTS:
        return cleaned
    return _WELCOME_VARIANT_ALIASES.get(cleaned, cleaned)


def _welcome_layout_from_pages_md(project: Path) -> str | None:
    for path in sorted(project.glob("design-system/*/pages/welcome.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        match = re.search(
            r"\*\*Layout variant:\*\*\s*`?([a-z0-9_-]+)`?",
            text,
            re.I,
        )
        if match:
            normalized = _normalize_welcome_layout_variant(match.group(1))
            if normalized in WELCOME_LAYOUT_VARIANTS:
                return normalized
        lower = text.lower()
        if "horizontal scroll journey" in lower:
            return "hero-split-trust"
        if "minimal" in lower and "pinned" in lower:
            return "hero-minimal-pinned"
        if "hex" in lower or "bauhaus" in lower:
            return "hero-hex-brand"
    return None


def resolve_welcome_layout_variant(project: Path) -> str:
    """Resolve canonical welcome layout from visual lock or design-system pages."""
    project = project.expanduser().resolve()
    lock_path = project / "本包视觉锁.json"
    if lock_path.is_file():
        try:
            data = json.loads(lock_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            spec = data.get("welcomeSpec")
            if isinstance(spec, dict):
                variant = str(spec.get("layoutVariant") or "").strip()
                if variant:
                    normalized = _normalize_welcome_layout_variant(variant)
                    if normalized in WELCOME_LAYOUT_VARIANTS:
                        return normalized
    from_pages = _welcome_layout_from_pages_md(project)
    if from_pages:
        return from_pages
    return DEFAULT_WELCOME_LAYOUT_VARIANT


WELCOME_LAYOUT_HINTS: dict[str, str] = {
    "hero-top-card-legal": "Single centered card: title, intro, trust bullets, 18+ notice, consent, Continue.",
    "hero-split-trust": "Split hero + trust/legal panel — journey-style emphasis.",
    "hero-minimal-pinned": "Minimal hero; consent + CTA pinned to bottom safe area.",
    "hero-hex-brand": "Brand motif + card body; geometric/Bauhaus accent per design-system.",
}


def format_welcome_spec_doc_refs(project: Path) -> list[str]:
    """Welcome norm doc paths only — for tests / tooling; not inlined into Agent prompt."""
    project = project.expanduser().resolve()
    refs: list[str] = []
    for path in sorted(project.glob("design-system/*/pages/welcome.md")):
        try:
            refs.append(path.relative_to(project).as_posix())
        except ValueError:
            refs.append(str(path))
    lock = project / "本包视觉锁.json"
    if lock.is_file():
        refs.append("本包视觉锁.json")
    return refs


def is_pipeline_welcome_stub(text: str) -> bool:
    return WELCOME_STUB_MARKER in text or "implement per 功能文档" in text


def should_skip_welcome_vue_overwrite(text: str) -> bool:
    if WELCOME_IMPL_LOCK in text or AGENT_IMPL_LOCK in text:
        return True
    if SCAFFOLD_PIPELINE_MARKER in text:
        return True
    if is_pipeline_welcome_stub(text):
        return False
    return bool(text.strip())


def should_skip_tab_root_vue_overwrite(text: str) -> bool:
    if AGENT_IMPL_LOCK in text:
        return True
    if SCAFFOLD_PIPELINE_MARKER in text:
        return False
    return bool(text.strip())

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

    # Product-bound narrative depth (not a fixed carousel template).
    if not re.search(
        r"onboarding|carousel|dialogue|typewriter|narrative|scene|coreScene|"
        r"emotional|immers|beat|journey|preview",
        section,
        re.I,
    ):
        issues.append(
            "视觉蓝图.md Welcome Gate Canon 须声明产品绑定的引导形态"
            "（onboarding pattern / scene narrative — 禁止仅写合规骨架）"
        )
    if not re.search(
        r"audience|core\s*scene|product\s*flow|使用|人群|场景|"
        r"usage\s*moment|onboarding\s*pattern|scene\s*beat|"
        r"primary\s*zone|tab\s*1|identity|month|habit|streak|reflection",
        section,
        re.I,
    ):
        issues.append(
            "视觉蓝图.md Welcome Gate Canon 须引用 audience / coreScene / productFlow"
            "（或等价的场景/人群/时机描述 — 禁止套用他包模板）"
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


def _load_product_context(project: Path) -> dict:
    ctx_path = project / "skill-input" / "context.json"
    if not ctx_path.is_file():
        return {}
    try:
        data = json.loads(ctx_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


_WELCOME_STEP_LOGIC = re.compile(
    r"currentStep|activeStep|stepIndex|phaseIndex|onboardingStep|"
    r"goNext|nextStep|nextBeat|advanceStep|"
    r"WELCOME_STEPS|welcomeSteps|"
    r"v-if\s*=\s*[\"'][^\"']*step|v-show\s*=\s*[\"'][^\"']*step|"
    r"typewriter|carousel|dialogue",
    re.I,
)


def _has_welcome_step_logic(surface: str) -> bool:
    """True when welcome implements multi-beat onboarding (not CSS class names alone)."""
    return bool(_WELCOME_STEP_LOGIC.search(surface))


def _welcome_static_dump_issues(welcome: str) -> list[str]:
    """Reject single-screen stacks of beats + trust bullets (gate-passing skeleton)."""
    issues: list[str] = []
    beat_count = len(re.findall(r"welcome-beat|c-[\w-]+-welcome-beat", welcome, re.I))
    has_trust_ul = bool(re.search(r"welcome-trust|c-[\w-]+-welcome-trust", welcome, re.I))
    has_step_cond = bool(re.search(r"v-if|v-show", welcome, re.I))
    if beat_count >= 2 and has_trust_ul and not has_step_cond:
        issues.append(
            "WelcomeView: 禁止一屏堆叠多段 beat + trust bullet 列表"
            " — 须分步 narrative/carousel/dialogue，合规区仅在最终 beat"
        )
    return issues


def _welcome_scene_binding_issues(project: Path, welcome: str, audit_surface: str) -> list[str]:
    """Welcome route must drive ambient scene + readable token aliases."""
    issues: list[str] = []
    surface = f"{welcome}\n{audit_surface}"
    router_path = h5_src_dir(project) / "router" / "index.ts"
    router_text = ""
    if router_path.is_file():
        try:
            router_text = router_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            pass

    has_meta_scene = bool(re.search(r"['\"]welcome['\"][^}]*scene\s*:\s*['\"]welcome['\"]|scene\s*:\s*['\"]welcome['\"]", router_text, re.I))
    has_set_scene = bool(re.search(r"setScene\s*\(\s*['\"]welcome['\"]", surface, re.I))
    if not has_meta_scene and not has_set_scene:
        issues.append(
            "WelcomeView/router: 须 route meta.scene='welcome' 或 WelcomeView 内 setScene('welcome')"
        )

    from batch.h5_theme_tokens import THEME_END, THEME_START, resolve_prefix

    prefix = resolve_prefix(project).lower()
    css = vite_css_text(project)
    if prefix and css and THEME_START in css and THEME_END in css:
        theme_slice = css.split(THEME_START, 1)[1].split(THEME_END, 1)[0]
        for alias in ("foreground", "background", "on-ambient"):
            token = f"--{prefix}-{alias}"
            if token not in theme_slice:
                issues.append(f"WelcomeView/theme: THEME 块缺少 {token}（welcome 文字可能不可读）")
    return issues


def _welcome_product_relevance_issues(project: Path, welcome: str, audit_surface: str) -> list[str]:
    """Product-binding checks when skill-input/context.json has product fields."""
    ctx = _load_product_context(project)
    product = ctx.get("product") if isinstance(ctx.get("product"), dict) else {}
    core_scene = str(product.get("coreScene") or "").strip()
    audience = str(product.get("audience") or "").strip()
    if not core_scene and not audience:
        return []

    issues: list[str] = []
    surface = f"{welcome}\n{audit_surface}"

    if not _has_welcome_step_logic(surface):
        issues.append(
            "WelcomeView: 须有产品绑定的引导结构"
            "（step/carousel/typewriter/dialogue 等任一，禁止单屏功能 bullet 卡）"
        )

    # Sole generic welcome headline is insufficient when coreScene is known.
    if re.search(r"Welcome\s+to\s+\w+", welcome, re.I) and not re.search(
        r"<h1[^>]*>\s*(?!Welcome\s+to)",
        welcome,
        re.I,
    ):
        # Only flag if h1 looks like pure "Welcome to X"
        h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", welcome, re.I | re.S)
        if h1s and all(re.search(r"^\s*Welcome\s+to\b", re.sub(r"<[^>]+>", "", h), re.I) for h in h1s):
            issues.append(
                "WelcomeView: 主标题不得仅是 'Welcome to {App}' — "
                f"须体现 coreScene（{core_scene or '—'}）"
            )

    # Scene / motion hint in welcome CSS or template.
    css = vite_css_text(project)
    if css and not re.search(
        r"gradient|blur|keyframes|animation|@keyframes|transform",
        css + welcome,
        re.I,
    ):
        issues.append(
            "WelcomeView: 须有场景化视觉线索（gradient/blur/animation）呼应 coreScene"
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
    has_scene_structure = _has_welcome_step_logic(audit_surface)
    if trust_li < 2 and plain_li < 2 and not has_scene_structure:
        issues.append("MISSING: ≥2 trust bullet rows in WelcomeView")

    if 'type="checkbox"' not in welcome:
        issues.append("MISSING: consent checkbox in WelcomeView")

    if not re.search(r":disabled|disabled.*Continue|Continue.*disabled", welcome, re.I):
        issues.append("MISSING: disabled Agree CTA until checkbox checked")

    if not re.search(
        r"openLegal\s*\(|LegalOverlay|Privacy Agreement",
        audit_surface,
        re.I,
    ):
        issues.append("MISSING: Privacy/Terms legal links in WelcomeView")

    if not re.search(r"\b18\b|18\s*\+|older", welcome, re.I):
        issues.append("MISSING: 18+ age notice in WelcomeView")

    from batch.h5_ui_copy import collect_h5_welcome_demo_violations

    issues.extend(collect_h5_welcome_demo_violations(project))
    issues.extend(_welcome_static_dump_issues(welcome))
    issues.extend(_welcome_scene_binding_issues(project, welcome, audit_surface))
    issues.extend(_welcome_product_relevance_issues(project, welcome, audit_surface))

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

    if not re.search(r"openLegal|LegalOverlay|Privacy Agreement", welcome, re.I):
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
