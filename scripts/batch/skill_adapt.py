"""Select uupm design candidate and convert to pipeline-facing skill-adapt artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SKILL_ADAPT_DIR = "skill-adapt"
SELECTED_CANDIDATE = "selected-candidate.json"
SELECTED_DESIGNER = "selected-designer.json"
DESIGN_BRIEF = "design-brief.md"
IMPL_UI_INPUT = "impl-ui-input.md"
AMBIENT_CANVAS_BRIEF = "ambient-canvas-brief.md"
CSS_MOTION_BRIEF = "css-motion-brief.md"
ICON_SPRITE_MANIFEST = "icon-sprite-manifest.json"  # legacy alias filename
ICON_MANIFEST = "icon-manifest.json"
KIT_SKELETON = "kit-skeleton.css"


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _candidate_blob(candidate: dict[str, Any]) -> str:
    style = candidate.get("style") or {}
    colors = candidate.get("colors") or {}
    typo = candidate.get("typography") or {}
    pattern = candidate.get("pattern") or {}
    parts = [
        str(style.get("name") or ""),
        str(style.get("keywords") or ""),
        str(colors.get("notes") or ""),
        str(colors.get("primary") or ""),
        str(typo.get("mood") or ""),
        str(pattern.get("name") or ""),
        str(candidate.get("anti_patterns") or ""),
    ]
    return " ".join(parts)


def _avoid_blob(anti: dict[str, Any]) -> list[tuple[str, set[str]]]:
    blobs: list[tuple[str, set[str]]] = []
    for item in anti.get("sameBatchUsed") or []:
        if isinstance(item, dict):
            text = " ".join(str(v) for v in item.values())
            blobs.append((str(item.get("name") or "batch"), _tokenize(text)))
    for i, phrase in enumerate(anti.get("historicalAvoid") or []):
        blobs.append((f"hist-{i}", _tokenize(str(phrase))))
    return blobs


def _sibling_visual_fingerprints(anti: dict[str, Any]) -> list[dict[str, str]]:
    fps: list[dict[str, str]] = []
    for raw in anti.get("sameBatchVisualFingerprints") or []:
        if isinstance(raw, dict) and raw:
            fps.append(raw)
    for item in anti.get("sameBatchUsed") or []:
        if not isinstance(item, dict):
            continue
        vf = item.get("visualFingerprint")
        if isinstance(vf, dict) and vf:
            fps.append(vf)
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for fp in fps:
        key = json.dumps(fp, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(fp)
    return unique


def collision_score(candidate: dict[str, Any], anti: dict[str, Any]) -> float:
    """Lower is better. Text overlap + weighted visual fingerprint vs batch siblings."""
    from batch.design_diversity import fingerprint_batch_collision

    sibling_fps = _sibling_visual_fingerprints(anti)
    visual = fingerprint_batch_collision(candidate, sibling_fps)

    cand_tokens = _tokenize(_candidate_blob(candidate))
    text_score = 0.0
    text_count = 0
    for _label, avoid_tokens in _avoid_blob(anti):
        if not avoid_tokens:
            continue
        inter = len(cand_tokens & avoid_tokens)
        union = len(cand_tokens | avoid_tokens)
        text_score += inter / union if union else 0.0
        text_count += 1
    text_avg = text_score / text_count if text_count else 0.0

    # Visual identity dominates — same palette/fonts/pattern must not win.
    return min(1.0, visual * 0.72 + text_avg * 0.28)


def theme_fit_score(candidate: dict[str, Any], product_text: str) -> float:
    """Higher is better — overlap between candidate semantics and product brief."""
    product_tokens = _tokenize(product_text)
    if not product_tokens:
        return 0.5
    cand_tokens = _tokenize(_candidate_blob(candidate))
    cand_tokens |= _tokenize(str(candidate.get("category") or ""))
    inter = len(cand_tokens & product_tokens)
    union = len(cand_tokens | product_tokens)
    return inter / union if union else 0.0


def audience_mismatch_penalty(candidate: dict[str, Any], audience: str) -> float:
    """Penalty 0–0.4 added to combined score when typography mood clashes with audience."""
    mood = str((candidate.get("typography") or {}).get("mood") or "").lower()
    aud = (audience or "").lower()
    if not mood or not aud:
        return 0.0
    adult_markers = ("大学生", "university", "student", "adult", "成年人", "职场")
    kid_markers = ("kids", "child", "toddler", "幼儿", "幼教", "kindergarten")
    if any(m in aud for m in adult_markers) and any(m in mood for m in kid_markers):
        return 0.35
    parent_markers = ("家长", "parent", "陪读", "亲子")
    bi_markers = ("forecast", "anomaly detection", "predictive analytics", "ai-driven insights")
    style_name = str((candidate.get("style") or {}).get("name") or "").lower()
    if any(m in aud for m in parent_markers):
        blob = f"{style_name} {mood}"
        if any(m in blob for m in bi_markers):
            return 0.2
    return 0.0


def _combined_pick_score(
    candidate: dict[str, Any],
    anti: dict[str, Any],
    *,
    product_text: str,
    audience: str,
) -> float:
    collision = collision_score(candidate, anti)
    theme = theme_fit_score(candidate, product_text)
    penalty = audience_mismatch_penalty(candidate, audience)
    from batch.skill_product_bind import domain_theme_boost

    boost = domain_theme_boost(candidate, product_text)
    return collision * 0.42 + (1.0 - theme) * 0.42 + penalty - boost


def pick_candidate(
    candidates: list[dict[str, Any]],
    anti: dict[str, Any],
    *,
    product_text: str = "",
    audience: str = "",
) -> tuple[dict[str, Any], str]:
    if not candidates:
        raise RuntimeError("skill.adapt: candidates.json 为空")

    from batch.design_diversity import fingerprint_batch_collision, visual_fingerprint

    sibling_fps = _sibling_visual_fingerprints(anti)
    scored: list[tuple[float, dict[str, Any]]] = []
    for cand in candidates:
        score = _combined_pick_score(
            cand,
            anti,
            product_text=product_text,
            audience=audience,
        )
        scored.append((score, cand))
    scored.sort(key=lambda x: x[0])

    best_score, best = scored[0]
    rejected: list[str] = []

    # Hard reject: too close to a sibling visual fingerprint (generic SaaS convergence).
    if sibling_fps and fingerprint_batch_collision(best, sibling_fps) >= 0.55:
        for score, cand in scored[1:]:
            if fingerprint_batch_collision(cand, sibling_fps) < 0.55:
                rejected.append(
                    f"c1 visual overlap {fingerprint_batch_collision(best, sibling_fps):.2f} — "
                    f"switched to {cand.get('id', '?')}"
                )
                best_score, best = score, cand
                break

    rationale = (
        f"Selected combined score {best_score:.3f} among {len(candidates)} candidate(s)"
        f" (collision + theme-fit + audience)."
    )
    if rejected:
        rationale += " " + "; ".join(rejected)
    if sibling_fps:
        fp = visual_fingerprint(best)
        rationale += (
            f" Visual: {fp.get('style')} / {fp.get('primary')} / {fp.get('heading')} / {fp.get('pattern')}."
        )
    if best_score > 0.45:
        rationale += " Warning: overlap with batch/registry context remains elevated."
    return best, rationale


def _hex_eq(a: str, b: str) -> bool:
    return (a or "").strip().upper() == (b or "").strip().upper()


def _candidate_primary_accent(cand: dict[str, Any]) -> tuple[str, str]:
    colors = cand.get("colors") if isinstance(cand.get("colors"), dict) else {}
    primary = str(colors.get("primary") or "")
    accent = str(colors.get("accent") or colors.get("cta") or "")
    return primary, accent


def candidate_aligned_to_master(
    candidates: list[dict[str, Any]],
    master_text: str,
) -> tuple[dict[str, Any], str]:
    """Build adapt candidate from skill.design MASTER — no second visual pick.

    Matches a factory candidate whose palette equals MASTER when possible, then
    overlays MASTER colors/typography/style so brief/token/skeleton cannot drift.
    """
    from batch.uupm_design_system import (
        parse_master_palette,
        parse_master_style_meta,
        parse_master_typography,
    )

    if not master_text.strip():
        raise RuntimeError("skill.adapt: MASTER.md 为空 — 请先运行 skill.design")

    palette = parse_master_palette(master_text)
    typo = parse_master_typography(master_text)
    style_meta = parse_master_style_meta(master_text)
    if not palette:
        raise RuntimeError("skill.adapt: MASTER.md 缺少 Color Palette — 无法对齐")

    matched: dict[str, Any] | None = None
    m_primary = palette.get("primary") or ""
    m_accent = palette.get("accent") or ""
    for cand in candidates:
        c_primary, c_accent = _candidate_primary_accent(cand)
        if _hex_eq(c_primary, m_primary) and (not m_accent or _hex_eq(c_accent, m_accent)):
            matched = cand
            break
    if matched is None:
        for cand in candidates:
            c_primary, _ = _candidate_primary_accent(cand)
            if _hex_eq(c_primary, m_primary):
                matched = cand
                break
    if matched is None and candidates:
        matched = candidates[0]

    base: dict[str, Any] = dict(matched) if matched else {"id": "master"}
    colors = dict(base.get("colors") or {})
    colors.update(palette)
    if palette.get("accent"):
        colors["cta"] = palette["accent"]
    if palette.get("foreground"):
        colors["text"] = palette["foreground"]
    if style_meta.get("color_notes"):
        colors["notes"] = style_meta["color_notes"]
    base["colors"] = colors

    typography = dict(base.get("typography") or {})
    typography.update({k: v for k, v in typo.items() if v})
    if style_meta.get("mood"):
        typography["mood"] = style_meta["mood"]
    if typo.get("google_fonts_url") and not typography.get("css_import"):
        typography["css_import"] = f"@import url('{typo['google_fonts_url']}');"
    base["typography"] = typography

    style = dict(base.get("style") or {})
    if style_meta.get("style_name"):
        style["name"] = style_meta["style_name"]
    if style_meta.get("style_keywords"):
        style["keywords"] = style_meta["style_keywords"]
    base["style"] = style

    pattern = dict(base.get("pattern") or {})
    if style_meta.get("pattern_name"):
        pattern["name"] = style_meta["pattern_name"]
    base["pattern"] = pattern

    if style_meta.get("anti_patterns"):
        base["anti_patterns"] = style_meta["anti_patterns"]

    cid = str(base.get("id") or "master")
    rationale = (
        f"Aligned to skill.design MASTER (factory output; no re-pick). "
        f"Matched candidate {cid}; primary {m_primary} accent {m_accent or '?'}."
    )
    return base, rationale


def designer_selections_from_candidate(
    candidate: dict[str, Any],
    seeds: dict[str, str],
    *,
    product_bind: dict[str, Any] | None = None,
    project_dir: Path | None = None,
) -> dict[str, str]:
    """Map uupm candidate + CSV seeds → designerDeckSelections."""
    from batch.skill_product_bind import hero_visual_motif, navigation_pattern_canon

    style = candidate.get("style") or {}
    colors = candidate.get("colors") or {}
    typo = candidate.get("typography") or {}
    pattern = candidate.get("pattern") or {}
    dials = candidate.get("dials") or {}
    bind = product_bind or {}

    color_temp = colors.get("notes") or colors.get("primary") or seeds.get("colorTemperature") or ""
    shape = style.get("name") or style.get("keywords") or seeds.get("shapeLanguage") or ""
    typography = typo.get("heading") or typo.get("mood") or seeds.get("typographyPersonality") or ""
    navigation = (
        navigation_pattern_canon(
            bind,
            project_dir=project_dir or Path("."),
            fallback=str(pattern.get("name") or seeds.get("navigationPattern") or ""),
        )
        if bind
        else (pattern.get("name") or seeds.get("navigationPattern") or "")
    )
    hero = hero_visual_motif(bind) if bind else (seeds.get("heroVisualMotif") or preset_motif_from_style(style))
    motion_label = dials.get("motion_label") or seeds.get("interactionFlavor") or ""
    icon = seeds.get("iconStyle") or "Phosphor outlined regular"

    return {
        "colorTemperature": str(color_temp)[:120],
        "shapeLanguage": str(shape)[:120],
        "typographyPersonality": str(typography)[:120],
        "navigationPattern": str(navigation)[:120],
        "heroVisualMotif": str(hero)[:120],
        "interactionFlavor": str(motion_label)[:120],
        "iconStyle": str(icon)[:120],
    }


def preset_motif_from_style(style: dict[str, Any]) -> str:
    keywords = str(style.get("keywords") or style.get("name") or "")
    return keywords[:120] if keywords else "Domain-specific mobile surfaces"


def _build_css_motion_brief(candidate: dict[str, Any]) -> str:
    dials = candidate.get("dials") or {}
    motion_snippet = candidate.get("motion_snippet") or {}
    tier = motion_snippet.get("Intensity Tier") or dials.get("motion_label") or "Standard"
    duration = motion_snippet.get("Duration") or "200ms"
    easing = motion_snippet.get("Easing") or "ease-out"
    trigger = motion_snippet.get("Trigger") or "on mount / on reveal"
    gsap = motion_snippet.get("GSAP Snippet") or ""

    lines = [
        "# CSS Motion Brief (skill.adapt)",
        "",
        f"**Intensity:** {tier} (dial {dials.get('motion', '?')}/10)",
        "",
        "## CSS equivalents (H5 monolith — no GSAP)",
        "",
        "```css",
        "@media (prefers-reduced-motion: no-preference) {",
        "  .u-motion-fade {",
        f"    transition: opacity {duration} {easing}, transform {duration} {easing};",
        "  }",
        "  .u-motion-rise {",
        f"    animation: u-rise {duration} {easing} both;",
        "  }",
        "}",
        "@media (prefers-reduced-motion: reduce) {",
        "  .u-motion-fade, .u-motion-rise { transition: none; animation: none; }",
        "}",
        "@keyframes u-rise {",
        "  from { opacity: 0; transform: translateY(8px); }",
        "  to { opacity: 1; transform: translateY(0); }",
        "}",
        "```",
        "",
        f"- **Trigger:** {trigger}",
        f"- **Reference (GSAP source):** {gsap[:200]}{'...' if len(str(gsap)) > 200 else ''}",
        "",
        "## Rules",
        "- Micro-interactions: 150–300ms; decorative ambient: up to 1.2s.",
        "- Always provide reduced-motion off switch.",
        "- Prefer `transform` + `opacity` — avoid layout-thrashing properties.",
        "",
    ]
    return "\n".join(lines)


def _build_icon_sprite_manifest(workspace: Path, candidate: dict[str, Any], designer: dict[str, str]) -> dict[str, Any]:
    """Build Phosphor icon manifest from skill icon-brief (unified with uupm icons.csv)."""
    from batch.skill_icons import (
        ALLOWED_ICON_LIBRARY,
        ALLOWED_ICON_PACKAGE,
        CANONICAL_ICON_SLUGS,
        FORBIDDEN_ICON_LIBRARIES,
        parse_icon_names_from_brief,
        phosphor_component_name,
    )
    from batch.workspace import dart_prefix

    del candidate, designer
    prefix = dart_prefix(workspace)
    icons: list[dict[str, str]] = []
    icon_brief = None
    for path in workspace.glob("design-system/*/icon-brief.md"):
        icon_brief = path
        break
    if icon_brief and icon_brief.is_file():
        text = icon_brief.read_text(encoding="utf-8", errors="replace")
        for slug in parse_icon_names_from_brief(text):
            icons.append(
                {
                    "slug": slug,
                    "component": phosphor_component_name(slug),
                    "package": ALLOWED_ICON_PACKAGE,
                    "source": "uupm-icons",
                }
            )
    seen = {i["slug"] for i in icons}
    for slug in CANONICAL_ICON_SLUGS:
        if slug not in seen:
            icons.append(
                {
                    "slug": slug,
                    "component": phosphor_component_name(slug),
                    "package": ALLOWED_ICON_PACKAGE,
                    "source": "canonical",
                }
            )
            seen.add(slug)
    icons = icons[:20]
    return {
        "prefix": prefix,
        "delivery": "phosphor-vue",
        "library": ALLOWED_ICON_LIBRARY,
        "package": ALLOWED_ICON_PACKAGE,
        "style": "Phosphor outlined icons via @phosphor-icons/vue (skill icons.csv)",
        "forbiddenLibraries": list(FORBIDDEN_ICON_LIBRARIES),
        "icons": icons,
        # Legacy field for design_diversity / older readers.
        "symbols": [
            {
                "slug": i["slug"],
                "symbolId": i["component"],
                "source": i["source"],
            }
            for i in icons
        ],
    }


def format_css_motion_block(workspace: Path) -> str:
    path = workspace / SKILL_ADAPT_DIR / CSS_MOTION_BRIEF
    if not path.is_file():
        return ""
    rel = path.relative_to(workspace).as_posix()
    return f"[CSS Motion — read `{rel}` for H5 animation canon]"


def format_icon_manifest_block(workspace: Path) -> str:
    path = workspace / SKILL_ADAPT_DIR / ICON_MANIFEST
    if not path.is_file():
        path = workspace / SKILL_ADAPT_DIR / ICON_SPRITE_MANIFEST
    if not path.is_file():
        return ""
    rel = path.relative_to(workspace).as_posix()
    return (
        f"[Icon Manifest — read `{rel}`; import Phosphor components from "
        "`@phosphor-icons/vue` per skill icon-brief — no iconfont/Font Awesome]"
    )


def _ambient_canvas_lock_seed(
    candidate: dict[str, Any],
    designer: dict[str, str],
) -> dict[str, Any]:
    from batch.ambient_canvas import _motif_key, ambient_canvas_tokens

    colors = candidate.get("colors") or {}
    primary = str(colors.get("primary") or "#2563EB")
    secondary = str(colors.get("secondary") or primary)
    accent = str(colors.get("accent") or colors.get("cta") or primary)
    motif_key = _motif_key(candidate)
    tokens = ambient_canvas_tokens(primary, secondary, accent)
    return {
        "motifKey": motif_key,
        "heroVisualMotif": designer.get("heroVisualMotif") or "",
        "navigationPattern": designer.get("navigationPattern") or "",
        "domRoot": "u-{prefix}-ambient",
        "sceneAttribute": "data-{prefix}-scene",
        "tokens": tokens,
        "scenes": {
            "splash": "splash",
            "welcome": "welcome",
            "tab1": "hub",
            "tab2": "list",
            "tab3": "detail",
            "export": "export",
        },
    }


def _design_brief_md(
    candidate: dict[str, Any],
    *,
    master_rel: str,
    stack_rel: str,
    selection_rationale: str,
    product_bind: dict[str, Any] | None = None,
    project_dir: Path | None = None,
) -> str:
    from batch.skill_product_bind import product_navigation_brief

    style = candidate.get("style") or {}
    colors = candidate.get("colors") or {}
    typo = candidate.get("typography") or {}
    lines = [
        "# Design Brief (skill.adapt)",
        "",
        f"**Selection:** {selection_rationale}",
        "",
    ]
    if product_bind and project_dir:
        lines.append(product_navigation_brief(product_bind, project_dir))
    lines.extend(
        [
            "## Primary Sources",
            f"- `{master_rel}` — full design system (ui-ux-pro-max MASTER)",
            f"- `{stack_rel}` — stack implementation guidelines",
            "- `design-system/*/pages/*.md` — per-screen overrides (override MASTER)",
            "- `design-system/*/ux-checklist.md` — UX/a11y acceptance checklist",
            "- `design-system/*/h5-interface-brief.md` — H5 monolith Do/Don't",
            "- `design-system/*/style-brief.md` — style keywords + CSS hints (ui-ux-pro-max)",
            "- `design-system/*/typography-brief.md` — font pairings",
            "- `design-system/*/color-brief.md` — palette guidance",
            "- `skill-adapt/kit-skeleton.css` — prefixed kit component classes (extend in kit.css)",
            "",
            "## Visual Identity (colors & typography — IA from Product Navigation Canon)",
            f"- **Style:** {style.get('name', '?')} — {style.get('keywords', '')}",
            f"- **Colors:** primary `{colors.get('primary', '?')}`, background `{colors.get('background', '?')}`",
            f"- **Typography:** {typo.get('heading', '?')} / {typo.get('body', '?')} ({typo.get('mood', '')})",
            f"- **uupm pattern (visual tone only):** {(candidate.get('pattern') or {}).get('name', '?')}",
            "",
            "## Ambient Canvas",
            "Implement per `skill-adapt/ambient-canvas-brief.md` + `design-system/*/pages/*.md`.",
            "Motif follows **interaction topology**, not generic SaaS style keywords.",
            "",
            "## Anti-Patterns (hard avoid in H5 UI)",
            str(candidate.get("anti_patterns") or "(see MASTER §Anti-Patterns)"),
            "",
            "## Agent Rule",
            "IA + workflows: topology + productFlow. Visual: MASTER + pages. Do not copy uupm pattern name as navigation.",
            "",
        ]
    )
    return "\n".join(lines)


def write_skill_adapt_outputs(
    workspace: Path,
    *,
    candidate: dict[str, Any],
    seeds: dict[str, str],
    selection_rationale: str,
    master_path: Path,
    stack_path: Path | None,
    project_dir: Path | None = None,
) -> Path:
    from batch.skill_product_bind import load_product_bind

    root = workspace / SKILL_ADAPT_DIR
    root.mkdir(parents=True, exist_ok=True)
    bind = load_product_bind(workspace)
    pdir = project_dir or workspace

    designer = designer_selections_from_candidate(
        candidate, seeds, product_bind=bind, project_dir=pdir
    )
    selected = {
        "candidateId": candidate.get("id") or "c1",
        "selectionRationale": selection_rationale,
        "designSystem": {
            "style": candidate.get("style"),
            "colors": candidate.get("colors"),
            "typography": candidate.get("typography"),
            "pattern": candidate.get("pattern"),
            "dials": candidate.get("dials"),
        },
    }
    (root / SELECTED_CANDIDATE).write_text(
        json.dumps(selected, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / SELECTED_DESIGNER).write_text(
        json.dumps({"designerDeckSelections": designer}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    master_rel = master_path.relative_to(workspace).as_posix() if master_path.is_file() else ""
    stack_rel = (
        stack_path.relative_to(workspace).as_posix()
        if stack_path and stack_path.is_file()
        else ""
    )
    brief = _design_brief_md(
        candidate,
        master_rel=master_rel,
        stack_rel=stack_rel,
        selection_rationale=selection_rationale,
        product_bind=bind,
        project_dir=pdir,
    )
    (root / DESIGN_BRIEF).write_text(brief, encoding="utf-8")

    from batch.ambient_canvas import build_ambient_canvas_brief

    ambient = build_ambient_canvas_brief(
        candidate,
        designer=designer,
        product_bind=bind,
        project_dir=pdir,
    )
    (root / AMBIENT_CANVAS_BRIEF).write_text(ambient, encoding="utf-8")

    from batch.skill_resolve import integration_enabled
    from batch.config import BatchConfig

    cfg = BatchConfig.from_env()
    if integration_enabled(cfg, "motion_css"):
        (root / CSS_MOTION_BRIEF).write_text(_build_css_motion_brief(candidate), encoding="utf-8")

    if integration_enabled(cfg, "icon_brief"):
        manifest = _build_icon_sprite_manifest(workspace, candidate, designer)
        payload = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        (root / ICON_MANIFEST).write_text(payload, encoding="utf-8")
        # Keep legacy filename for older design_diversity readers.
        (root / ICON_SPRITE_MANIFEST).write_text(payload, encoding="utf-8")

    from batch.h5_kit_skeleton import build_kit_css_skeleton, resolve_prefix as kit_prefix
    from batch.uupm_design_system import parse_master_typography

    prefix = kit_prefix(workspace)
    master_text = ""
    master_typo: dict[str, str] = {}
    if master_path.is_file():
        master_text = master_path.read_text(encoding="utf-8", errors="ignore")
        master_typo = parse_master_typography(master_text)
    kit_css = build_kit_css_skeleton(
        prefix,
        candidate=selected,
        designer=designer,
        master_typography=master_typo or None,
        master_text=master_text,
    )
    (root / KIT_SKELETON).write_text(kit_css, encoding="utf-8")

    impl_lines = [
        "# Implementation UI Input (skill.adapt)",
        "",
        f"Read `{master_rel}` before shared widgets.",
        f"Read `{stack_rel}` plus `stack-vue.md` / `stack-html-tailwind.md` (skill stacks).",
        f"Read `skill-adapt/{AMBIENT_CANVAS_BRIEF}` — implement `u-{{prefix}}-ambient`.",
        "Read `design-system/*/pages/<screen>.md` before implementing each route.",
        f"Read `skill-adapt/{CSS_MOTION_BRIEF}` for animation canon.",
        "Read `skill-adapt/design-tokens.css` — wire into Tailwind theme / `:root`.",
        f"Read `skill-adapt/{ICON_MANIFEST}` — import Phosphor Vue components listed there.",
        f"Optional kit classes: `skill-adapt/{KIT_SKELETON}` (`c-{prefix}-*` helpers).",
        "",
        "## designerDeckSelections (for 本包视觉锁.json)",
        json.dumps(designer, ensure_ascii=False, indent=2),
        "",
        "## ambientCanvas (for 本包视觉锁.json)",
        json.dumps(
            _ambient_canvas_lock_seed(candidate, designer),
            ensure_ascii=False,
            indent=2,
        ),
        "",
    ]
    (root / IMPL_UI_INPUT).write_text("\n".join(impl_lines), encoding="utf-8")
    return root / DESIGN_BRIEF


def load_selected_designer(workspace: Path) -> dict[str, str]:
    path = workspace / SKILL_ADAPT_DIR / SELECTED_DESIGNER
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    sel = data.get("designerDeckSelections")
    return sel if isinstance(sel, dict) else {}


def format_designer_lock_from_adapt(workspace: Path) -> str:
    path = workspace / SKILL_ADAPT_DIR / SELECTED_DESIGNER
    if not path.is_file():
        raise RuntimeError("缺少 skill-adapt/selected-designer.json — 请先运行 skill.adapt")
    designer = load_selected_designer(workspace)
    lines = [
        "[Designer Selection — from ui-ux-pro-max skill.adapt; copy to 本包视觉锁.json designerDeckSelections]",
    ]
    for key in (
        "colorTemperature",
        "shapeLanguage",
        "typographyPersonality",
        "navigationPattern",
        "heroVisualMotif",
        "interactionFlavor",
        "iconStyle",
    ):
        lines.append(f"- {key}: {designer.get(key, '')}")
    return "\n".join(lines)


def format_design_brief_block(workspace: Path) -> str:
    brief = workspace / SKILL_ADAPT_DIR / DESIGN_BRIEF
    master = workspace / "design-system"
    if not brief.is_file():
        raise RuntimeError("缺少 skill-adapt/design-brief.md — 请先运行 skill.adapt")
    text = brief.read_text(encoding="utf-8").strip()
    master_hint = ""
    matches = sorted(master.glob("*/MASTER.md"))
    if matches:
        rel = matches[0].relative_to(workspace).as_posix()
        master_hint = f"\nMASTER path: `{rel}`"
    ambient_hint = ""
    ambient_path = workspace / SKILL_ADAPT_DIR / AMBIENT_CANVAS_BRIEF
    if ambient_path.is_file():
        ambient_hint = f"\nAmbient canvas: `skill-adapt/{AMBIENT_CANVAS_BRIEF}`"
    enrich_hint = ""
    try:
        from batch.skill_enrich import format_enrich_summary_block

        name = workspace.name
        enrich_hint = format_enrich_summary_block(workspace, name)
        if enrich_hint:
            enrich_hint = "\n" + enrich_hint
    except Exception:
        pass
    pages_hint = ""
    try:
        from batch.skill_pages import format_pages_block

        pages_hint = format_pages_block(workspace, workspace.name)
        if pages_hint:
            pages_hint = "\n" + pages_hint
    except Exception:
        pass
    return (
        "[Design System — ui-ux-pro-max via skill.design + skill.adapt]\n"
        + text
        + master_hint
        + ambient_hint
        + enrich_hint
        + pages_hint
        + "\n\nUse skill-adapt/impl-ui-input.md during Programmer phase."
    )


def format_ambient_canvas_block(workspace: Path) -> str:
    from batch.ambient_canvas import format_ambient_canvas_prompt_block

    path = workspace / SKILL_ADAPT_DIR / AMBIENT_CANVAS_BRIEF
    if not path.is_file():
        raise RuntimeError("缺少 skill-adapt/ambient-canvas-brief.md — 请先运行 skill.adapt")
    rel = path.relative_to(workspace).as_posix()
    return format_ambient_canvas_prompt_block(rel)
