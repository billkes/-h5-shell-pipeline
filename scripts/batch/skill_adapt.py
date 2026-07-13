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
ICON_SPRITE_MANIFEST = "icon-sprite-manifest.json"


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


def pick_candidate(
    candidates: list[dict[str, Any]],
    anti: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    if not candidates:
        raise RuntimeError("skill.adapt: candidates.json 为空")

    from batch.design_diversity import fingerprint_batch_collision, visual_fingerprint

    sibling_fps = _sibling_visual_fingerprints(anti)
    scored: list[tuple[float, dict[str, Any]]] = []
    for cand in candidates:
        score = collision_score(cand, anti)
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
        f"Selected lowest collision score {best_score:.3f} among {len(candidates)} candidate(s)."
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


def designer_selections_from_candidate(
    candidate: dict[str, Any],
    seeds: dict[str, str],
) -> dict[str, str]:
    """Map uupm candidate + CSV seeds → designerDeckSelections."""
    style = candidate.get("style") or {}
    colors = candidate.get("colors") or {}
    typo = candidate.get("typography") or {}
    pattern = candidate.get("pattern") or {}
    dials = candidate.get("dials") or {}

    color_temp = colors.get("notes") or colors.get("primary") or seeds.get("colorTemperature") or ""
    shape = style.get("name") or style.get("keywords") or seeds.get("shapeLanguage") or ""
    typography = typo.get("heading") or typo.get("mood") or seeds.get("typographyPersonality") or ""
    navigation = pattern.get("name") or seeds.get("navigationPattern") or ""
    hero = style.get("best_for") or seeds.get("heroVisualMotif") or ""
    motion_label = dials.get("motion_label") or seeds.get("interactionFlavor") or ""
    icon = seeds.get("iconStyle") or "outlined inline SVG sprite (unified H5 kit)"

    return {
        "colorTemperature": str(color_temp)[:120],
        "shapeLanguage": str(shape)[:120],
        "typographyPersonality": str(typography)[:120],
        "navigationPattern": str(navigation)[:120],
        "heroVisualMotif": str(hero)[:120],
        "interactionFlavor": str(motion_label)[:120],
        "iconStyle": str(icon)[:120],
    }


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
    from batch.skill_icons import (
        CANONICAL_ICON_SLUGS,
        FORBIDDEN_ICON_LIBRARIES,
        h5_symbol_id,
        parse_icon_names_from_brief,
    )
    from batch.workspace import dart_prefix

    prefix = dart_prefix(workspace)
    symbols: list[dict[str, str]] = []
    icon_brief = None
    for path in workspace.glob("design-system/*/icon-brief.md"):
        icon_brief = path
        break
    if icon_brief and icon_brief.is_file():
        text = icon_brief.read_text(encoding="utf-8", errors="replace")
        for slug in parse_icon_names_from_brief(text):
            symbols.append(
                {
                    "slug": slug,
                    "symbolId": h5_symbol_id(prefix, slug),
                    "source": "uupm-icons",
                }
            )
    seen = {s["slug"] for s in symbols}
    for slug in CANONICAL_ICON_SLUGS:
        if slug not in seen:
            symbols.append(
                {
                    "slug": slug,
                    "symbolId": h5_symbol_id(prefix, slug),
                    "source": "canonical",
                }
            )
            seen.add(slug)
    symbols = symbols[:20]
    return {
        "prefix": prefix,
        "delivery": "inline-svg-sprite",
        "strokeWidth": "2",
        "viewBox": "0 0 24 24",
        "style": "outlined inline SVG sprite (unified H5 kit — no per-pack icon libraries)",
        "forbiddenLibraries": list(FORBIDDEN_ICON_LIBRARIES),
        "symbols": symbols,
        # Legacy field for design_diversity ledger readers.
        "icons": [{"name": s["slug"], "source": s["source"]} for s in symbols],
    }


def format_css_motion_block(workspace: Path) -> str:
    path = workspace / SKILL_ADAPT_DIR / CSS_MOTION_BRIEF
    if not path.is_file():
        return ""
    rel = path.relative_to(workspace).as_posix()
    return f"[CSS Motion — read `{rel}` for H5 animation canon]"


def format_icon_manifest_block(workspace: Path) -> str:
    from batch.workspace import dart_prefix

    path = workspace / SKILL_ADAPT_DIR / ICON_SPRITE_MANIFEST
    if not path.is_file():
        return ""
    rel = path.relative_to(workspace).as_posix()
    return f"[Icon Sprite Manifest — read `{rel}`; embed `{dart_prefix(workspace)}-mark-*` symbol IDs in entry.htm — NO icon font libraries]"


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
) -> str:
    style = candidate.get("style") or {}
    colors = candidate.get("colors") or {}
    typo = candidate.get("typography") or {}
    lines = [
        "# Design Brief (skill.adapt)",
        "",
        f"**Selection:** {selection_rationale}",
        "",
        "## Primary Sources",
        f"- `{master_rel}` — full design system (ui-ux-pro-max MASTER)",
        f"- `{stack_rel}` — stack implementation guidelines",
        "- `design-system/*/pages/*.md` — per-screen overrides (override MASTER)",
        "- `design-system/*/ux-checklist.md` — UX/a11y acceptance checklist",
        "- `design-system/*/h5-interface-brief.md` — H5 monolith Do/Don't",
        "",
        "## Visual Identity (from selected candidate)",
        f"- **Style:** {style.get('name', '?')} — {style.get('keywords', '')}",
        f"- **Colors:** primary `{colors.get('primary', '?')}`, background `{colors.get('background', '?')}`",
        f"- **Typography:** {typo.get('heading', '?')} / {typo.get('body', '?')} ({typo.get('mood', '')})",
        f"- **Pattern:** {(candidate.get('pattern') or {}).get('name', '?')}",
        "",
        "## Ambient Canvas",
        "Expand `skill-adapt/ambient-canvas-brief.md` into 视觉蓝图.md **§Ambient Canvas Canon**.",
        "Bind layers to heroVisualMotif + key_effects — **no flat SaaS gray wash only**.",
        "",
        "## Anti-Patterns (hard avoid in 视觉蓝图.md)",
        str(candidate.get("anti_patterns") or "(see MASTER §Anti-Patterns)"),
        "",
        "## Agent Rule",
        "Do NOT invent generic UI/UX rules. Expand MASTER into 视觉蓝图.md / 本包视觉锁.json; cite MASTER sections.",
        "",
    ]
    return "\n".join(lines)


def write_skill_adapt_outputs(
    workspace: Path,
    *,
    candidate: dict[str, Any],
    seeds: dict[str, str],
    selection_rationale: str,
    master_path: Path,
    stack_path: Path | None,
) -> Path:
    root = workspace / SKILL_ADAPT_DIR
    root.mkdir(parents=True, exist_ok=True)

    designer = designer_selections_from_candidate(candidate, seeds)
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
    )
    (root / DESIGN_BRIEF).write_text(brief, encoding="utf-8")

    from batch.ambient_canvas import build_ambient_canvas_brief

    ambient = build_ambient_canvas_brief(candidate, designer=designer)
    (root / AMBIENT_CANVAS_BRIEF).write_text(ambient, encoding="utf-8")

    from batch.skill_resolve import integration_enabled
    from batch.config import BatchConfig

    cfg = BatchConfig.from_env()
    if integration_enabled(cfg, "motion_css"):
        (root / CSS_MOTION_BRIEF).write_text(_build_css_motion_brief(candidate), encoding="utf-8")

    if integration_enabled(cfg, "icon_brief"):
        manifest = _build_icon_sprite_manifest(workspace, candidate, designer)
        (root / ICON_SPRITE_MANIFEST).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    impl_lines = [
        "# Implementation UI Input (skill.adapt)",
        "",
        f"Read `{master_rel}` before shared widgets.",
        f"Read `{stack_rel}` for stack-specific rules.",
        f"Read `skill-adapt/{AMBIENT_CANVAS_BRIEF}` — implement `u-{{prefix}}-ambient` in entry.htm.",
        "Read `design-system/*/pages/<screen>.md` before implementing each route.",
        "Read `skill-adapt/css-motion-brief.md` for animation canon.",
        "Read `skill-adapt/design-tokens.css` for :root variables.",
        "Read `skill-adapt/icon-sprite-manifest.json` — embed listed `symbolId` values as inline SVG sprites.",
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
