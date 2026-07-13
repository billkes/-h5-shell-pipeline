"""Ambient canvas brief — theme-specific page backgrounds for H5 shell packs."""

from __future__ import annotations

import re
from typing import Any

AMBIENT_CANVAS_BRIEF = "ambient-canvas-brief.md"


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    raw = (hex_color or "#000000").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(c * 2 for c in raw)
    if len(raw) != 6:
        return f"rgba(0,0,0,{alpha})"
    r, g, b = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _motif_key(candidate: dict[str, Any]) -> str:
    style = candidate.get("style") or {}
    pattern = candidate.get("pattern") or {}
    blob = " ".join(
        [
            str(style.get("name") or ""),
            str(style.get("keywords") or ""),
            str(style.get("effects") or ""),
            str(style.get("best_for") or ""),
            str(pattern.get("name") or ""),
            str(pattern.get("color_strategy") or ""),
        ]
    )
    n = _norm(blob)
    if "horizontal scroll" in n or "journey" in n or "chapter" in n:
        return "horizontal_journey"
    if (
        "predictive" in n
        or "forecast" in n
        or "analytics" in n
        or "confidence" in n
        or "anomaly" in n
    ):
        return "predictive_analytics"
    if "parallax" in n or "storytelling" in n:
        return "parallax_story"
    if "inclusive" in n or "accessible" in n or "wcag" in n:
        return "inclusive_wash"
    if "gaming" in n or "cyber" in n or "hud" in n or "sci-fi" in n:
        return "hud_grid"
    return "mesh_gradient"


def motif_key_from_candidate(candidate: dict[str, Any]) -> str:
    """Public alias for skill.product_bind fallback."""
    return _motif_key(candidate)


_MOTIF_PRESETS: dict[str, dict[str, str]] = {
    "reminder_ring": {
        "title": "Reminder Ring Orbit",
        "motif": "Concentric due-date rings + soft amber pulse on cream base",
        "layers": "cream base | orbit rings (SVG) | due-node accents | subtle grid",
        "scene_hint": "list/hub: rings visible; detail: single ring focus; export: calm wash",
        "motion": "orbit drift 24s; due pulse 3s (respect reduced-motion)",
    },
    "wizard_pipeline": {
        "title": "Wizard Step Lane",
        "motif": "Horizontal step lane + progress wash for multi-step flows",
        "layers": "institutional base | step lane stripes | progress gradient bar",
        "scene_hint": "wizard steps: lane active; teleprompter: minimal wash",
        "motion": "lane progress fill on step change; no infinite decorative loops",
    },
    "checklist_session": {
        "title": "Checklist Session Grid",
        "motif": "Check row grid + completion tick accents",
        "layers": "muted base | row grid | completion highlight band",
        "scene_hint": "list/checklist routes show grid; splash/welcome: base only",
        "motion": "tick fade 400ms on complete",
    },
    "dashboard_kpi": {
        "title": "KPI Tile Wash",
        "motif": "Metric tile glow + calm dashboard mesh",
        "layers": "mesh base | tile grid | accent KPI glow",
        "scene_hint": "hub/dashboard intensified; detail/list subdued",
        "motion": "KPI count-up on mount only",
    },
    "capture_first": {
        "title": "Capture Spotlight",
        "motif": "Camera-ready spotlight ellipse + archive lane",
        "layers": "neutral base | spotlight | lane stripe",
        "scene_hint": "capture routes: spotlight; archive list: lane only",
        "motion": "spotlight breathe 12s",
    },
    "predictive_analytics": {
        "title": "Analytics Grid + Confidence Bands",
        "motif": "Forecast line, confidence interval wash, anomaly pulse nodes",
        "layers": "base wash | metric grid (28px) | SVG confidence band | soft primary blob",
        "scene_hint": "list/detail: grid fades toward bottom; hero: stronger band curve",
        "motion": "band fade-in 1.2s; optional anomaly pulse @ 4s (respect reduced-motion)",
    },
    "horizontal_journey": {
        "title": "Chapter Journey Lane",
        "motif": "Vertical chapter color wash + horizontal lane stripes for scroll journey",
        "layers": "chapter gradient stack | lane stripes (repeating-linear) | spotlight ellipse",
        "scene_hint": "hub/list: lane visible; welcome/splash: wash only, hide lane",
        "motion": "lane drift 22s ease-in-out; spotlight breathe 10s",
    },
    "inclusive_wash": {
        "title": "Accessible Depth Wash",
        "motif": "High-contrast-safe radial washes + 4px focus ring echo (decorative)",
        "layers": "tri-mesh radial | subtle dot grid | decorative focus rings (aria-hidden)",
        "scene_hint": "all routes share wash; rings strongest on welcome + form routes",
        "motion": "slow mesh drift 18s; disable ring animation when prefers-reduced-motion",
    },
    "hud_grid": {
        "title": "HUD Grid + Scan Accent",
        "motif": "Tech grid, ambient rings, optional scan line on data-heavy routes",
        "layers": "mesh | square grid | concentric rings | scan line (detail/export only)",
        "scene_hint": "per-route `data-{prefix}-scene` shifts ambient-a/b/c tokens",
        "motion": "ring breathe 8s; scan sweep 6s on detail/export scenes only",
    },
    "parallax_story": {
        "title": "Layered Story Depth",
        "motif": "Offset mesh blobs + soft horizon band for narrative scroll",
        "layers": "deep base | 2 parallax blobs (unrelated scroll speeds) | horizon band",
        "scene_hint": "hero/splash: full parallax; list: static wash only",
        "motion": "blob parallax via transform on scroll (CSS vars), not layout thrash",
    },
    "mesh_gradient": {
        "title": "Tri-Mesh Ambient",
        "motif": "Three radial gradients derived from primary/secondary/accent",
        "layers": "solid base | mesh overlay | optional 32px grid at 4% opacity",
        "scene_hint": "default for all routes; intensify mesh on hero routes",
        "motion": "mesh drift 18s ease-in-out infinite",
    },
}


def ambient_canvas_tokens(primary: str, secondary: str, accent: str) -> dict[str, str]:
    """CSS custom properties for ambient layers (reference — prefix at implement time)."""
    return {
        "ambient-a": _hex_to_rgba(primary, 0.22),
        "ambient-b": _hex_to_rgba(secondary or primary, 0.14),
        "ambient-c": _hex_to_rgba(accent or primary, 0.10),
        "ambient-ring": _hex_to_rgba(primary, 0.28),
        "ambient-grid": _hex_to_rgba(primary, 0.05),
        "ambient-scan": _hex_to_rgba(accent or primary, 0.35),
    }


def build_ambient_canvas_brief(
    candidate: dict[str, Any],
    *,
    designer: dict[str, str] | None = None,
    product_bind: dict[str, Any] | None = None,
    project_dir: Path | None = None,
) -> str:
    """Markdown brief for PM 视觉蓝图 §Ambient Canvas and H5 implementer."""
    from batch.skill_product_bind import ambient_motif_key, hero_visual_motif, navigation_pattern_canon

    style = candidate.get("style") or {}
    colors = candidate.get("colors") or {}
    pattern = candidate.get("pattern") or {}
    designer = designer or {}
    bind = product_bind or {}

    primary = str(colors.get("primary") or "#2563EB")
    secondary = str(colors.get("secondary") or primary)
    accent = str(colors.get("accent") or colors.get("cta") or primary)
    bg = str(colors.get("background") or "#F8FAFC")

    motif_key = ambient_motif_key(bind, candidate) if bind else _motif_key(candidate)
    preset = _MOTIF_PRESETS.get(motif_key) or _MOTIF_PRESETS["mesh_gradient"]
    tokens = ambient_canvas_tokens(primary, secondary, accent)

    hero = hero_visual_motif(bind) if bind else (designer.get("heroVisualMotif") or preset["motif"])
    nav = (
        navigation_pattern_canon(bind, project_dir=project_dir, fallback=str(pattern.get("name") or ""))
        if bind and project_dir
        else (designer.get("navigationPattern") or pattern.get("name") or "")
    )
    effects = str(style.get("effects") or candidate.get("key_effects") or "")

    lines = [
        "# Ambient Canvas Brief (skill.adapt)",
        "",
        "Use this as the **primary source** for `视觉蓝图.md` §Ambient Canvas Canon and H5 `entry.htm` background.",
        "",
        "## Identity Anchors",
        f"- **Style:** {style.get('name', '?')}",
        f"- **Pattern / navigation:** {nav}",
        f"- **heroVisualMotif:** {hero}",
        f"- **key_effects:** {effects or '(see style.effects)'}",
        "",
        "## Motif Preset",
        f"- **Key:** `{motif_key}`",
        f"- **Title:** {preset['title']}",
        f"- **Visual motif:** {preset['motif']}",
        f"- **Layer stack:** {preset['layers']}",
        f"- **Per-route behavior:** {preset['scene_hint']}",
        f"- **Motion:** {preset['motion']}",
        "",
        "## Token Seeds (map to `--{{prefix}}-ambient-*` in entry.htm)",
        f"- Page base: `{bg}`",
    ]
    for key, val in tokens.items():
        lines.append(f"- `--{{prefix}}-{key}`: `{val}`")
    lines += [
        "",
        "## DOM Contract (H5 implementer — MANDATORY)",
        "- Fixed full-viewport layer **behind** scroll content: `div.u-{prefix}-ambient` (`aria-hidden=\"true\"`, `pointer-events:none`, `z-index:0`).",
        "- Children: `__base` (solid `--bg`) → `__mesh` (radial stack) → `__grid` (optional) → motif-specific SVG/div (bands/lane/rings).",
        "- Main app shell: `position:relative; z-index:1` — cards use **semi-opaque** surfaces (`rgba`/`color-mix`) so canvas bleeds through.",
        "- Route scenes: `document.documentElement.setAttribute('data-{prefix}-scene', '<scene>')` on navigation.",
        "- Scene table in 视觉蓝图 must list ≥4 routes (splash, welcome, tab roots, detail/export).",
        "",
        "## Anti-Pattern (hard avoid)",
        "- Flat single `--bg` only with opaque white cards covering 100% viewport.",
        "- Generic SaaS gray gradient unrelated to heroVisualMotif.",
        "- Canvas above interactive content or capturing pointer events.",
        "",
        "## Reference",
        "- Factory pattern: `data/static/templates/oc_shell/.../{{PREFIX}}_entry.htm` (`u-{{PREFIX}}-ambient`, `data-{{PREFIX}}-scene`).",
        "",
    ]
    return "\n".join(lines)


def format_ambient_canvas_prompt_block(workspace_brief_rel: str = "skill-adapt/ambient-canvas-brief.md") -> str:
    return (
        "[Ambient Canvas — MANDATORY for 视觉蓝图.md + H5 entry.htm]\n"
        f"- Read `{workspace_brief_rel}` **before** writing 视觉蓝图.md.\n"
        "- 视觉蓝图.md MUST include **§Ambient Canvas Canon** (see plan template): scene table, layer stack, "
        "CSS token table, motif implementation notes tied to heroVisualMotif / key_effects / navigationPattern.\n"
        "- 本包视觉锁.json MUST include `ambientCanvas` object (scenes + token keys).\n"
        "- H5 implementer MUST ship `u-{prefix}-ambient` in entry.htm per brief — not a post-hoc CSS tweak."
    )
