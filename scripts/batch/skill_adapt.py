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


def collision_score(candidate: dict[str, Any], anti: dict[str, Any]) -> float:
    """Lower is better. Jaccard-like overlap vs avoid contexts."""
    cand_tokens = _tokenize(_candidate_blob(candidate))
    if not cand_tokens:
        return 1.0
    total = 0.0
    count = 0
    for _label, avoid_tokens in _avoid_blob(anti):
        if not avoid_tokens:
            continue
        inter = len(cand_tokens & avoid_tokens)
        union = len(cand_tokens | avoid_tokens)
        total += inter / union if union else 0.0
        count += 1
    return total / count if count else 0.0


def pick_candidate(
    candidates: list[dict[str, Any]],
    anti: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    if not candidates:
        raise RuntimeError("skill.adapt: candidates.json 为空")
    scored = [(collision_score(c, anti), c) for c in candidates]
    scored.sort(key=lambda x: x[0])
    best_score, best = scored[0]
    rationale = (
        f"Selected lowest collision score {best_score:.3f} among {len(candidates)} candidate(s)."
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
    icon = seeds.get("iconStyle") or "uupm-aligned icon set"

    return {
        "colorTemperature": str(color_temp)[:120],
        "shapeLanguage": str(shape)[:120],
        "typographyPersonality": str(typography)[:120],
        "navigationPattern": str(navigation)[:120],
        "heroVisualMotif": str(hero)[:120],
        "interactionFlavor": str(motion_label)[:120],
        "iconStyle": str(icon)[:120],
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
        "",
        "## Visual Identity (from selected candidate)",
        f"- **Style:** {style.get('name', '?')} — {style.get('keywords', '')}",
        f"- **Colors:** primary `{colors.get('primary', '?')}`, background `{colors.get('background', '?')}`",
        f"- **Typography:** {typo.get('heading', '?')} / {typo.get('body', '?')} ({typo.get('mood', '')})",
        f"- **Pattern:** {(candidate.get('pattern') or {}).get('name', '?')}",
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

    impl_lines = [
        "# Implementation UI Input (skill.adapt)",
        "",
        f"Read `{master_rel}` before shared widgets.",
        f"Read `{stack_rel}` for stack-specific rules.",
        "Screen layout comes from 功能文档.md / 视觉蓝图.md — not pre-baked page overrides.",
        "",
        "## designerDeckSelections (for 本包视觉锁.json)",
        json.dumps(designer, ensure_ascii=False, indent=2),
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
    return (
        "[Design System — ui-ux-pro-max via skill.design + skill.adapt]\n"
        + text
        + master_hint
        + "\n\nUse skill-adapt/impl-ui-input.md during Programmer phase."
    )
