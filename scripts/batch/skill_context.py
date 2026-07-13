"""Build skill-input context for ui-ux-pro-max (facts + anti-collision, no design lock)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from batch.design_diversity import (
    design_ledger_path,
    enrich_anti_collision_with_visuals,
    theme_search_query_from_row,
)
from batch.pack_type import (
    H5_FLUTTER_SHELL,
    H5_OC_SHELL,
    H5_SHELL,
    H5_SWIFT_SHELL,
    h5_shell_runtime,
    is_flutter_runtime,
    is_h5_shell,
)
from batch.registry import format_already_used_block
from batch.spec_business_depth import resolve_business_depth_tier

if TYPE_CHECKING:
    from batch.config import BatchConfig
    from batch.csv_tasks import CsvTaskRow

SKILL_INPUT_DIR = "skill-input"
CONTEXT_FILE = "context.json"
ANTI_COLLISION_FILE = "anti-collision-context.json"
CONSTRAINTS_FILE = "constraints.md"


def stack_for_pack_type(pack_type: str) -> str:
    """Primary UI stack for design-system generation (H5 site uses html-tailwind)."""
    if is_h5_shell(pack_type):
        return "html-tailwind"
    if is_flutter_runtime(pack_type):
        return "flutter"
    return "html-tailwind"


def native_stack_for_pack_type(pack_type: str) -> str | None:
    """Optional native shell stack brief (Swift/Flutter)."""
    text = (pack_type or "").strip()
    if text == H5_SWIFT_SHELL:
        return "swiftui"
    if text in (H5_SHELL, H5_FLUTTER_SHELL):
        return "flutter"
    return None


_DESIGNER_SEED_POOL: tuple[dict[str, str], ...] = (
    {
        "colorTemperature": "warm approachable pastels",
        "shapeLanguage": "soft rounded cards",
        "typographyPersonality": "friendly humanist sans",
        "navigationPattern": "bottom tab hub",
        "heroVisualMotif": "layered ambient mesh",
        "interactionFlavor": "subtle fade transitions",
        "iconStyle": "outlined 2px stroke SVG",
    },
    {
        "colorTemperature": "cool professional blue-gray",
        "shapeLanguage": "sharp rectangular panels",
        "typographyPersonality": "geometric display + neutral body",
        "navigationPattern": "index grid home",
        "heroVisualMotif": "data band grid",
        "interactionFlavor": "standard 200ms ease",
        "iconStyle": "sharp outlined SVG",
    },
    {
        "colorTemperature": "vibrant accent on neutral base",
        "shapeLanguage": "pill chips and squircles",
        "typographyPersonality": "rounded playful pairing",
        "navigationPattern": "hero-first drill-down",
        "heroVisualMotif": "organic blob parallax",
        "interactionFlavor": "spring-like micro-motion",
        "iconStyle": "rounded outlined SVG",
    },
)


def designer_seeds_from_row(row: CsvTaskRow) -> dict[str, str]:
    """Stable designer seed phrases from CSV row (pre skill.adapt)."""
    blob = " ".join(
        filter(
            None,
            [
                row.name,
                row.theme_angle,
                row.track,
                row.audience,
                row.core_scene,
                row.local_feature,
                row.product_flow,
            ],
        )
    )
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(_DESIGNER_SEED_POOL)
    return dict(_DESIGNER_SEED_POOL[idx])


def update_context_designer_seeds(workspace: Path, designer: dict[str, str]) -> None:
    """After skill.adapt — persist resolved designerDeckSelections into context.json."""
    ctx_path = workspace / SKILL_INPUT_DIR / CONTEXT_FILE
    if not ctx_path.is_file():
        return
    try:
        ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    ctx["designerSeeds"] = designer
    ctx_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _same_batch_summaries(
    cfg: BatchConfig,
    row: CsvTaskRow,
    *,
    batch_id: str,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for name, other in (cfg.task_csv_by_name or {}).items():
        if name == row.name or not isinstance(other, type(row)):
            continue
        out.append(
            {
                "name": name,
                "themeAngle": str(getattr(other, "theme_angle", "") or ""),
            }
        )
    _ = batch_id
    return out


def _registry_avoid_phrases(registry_path: Path, limit: int = 40) -> list[str]:
    if not registry_path.is_file():
        return []
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        packages = data.get("packages") or []
    except (json.JSONDecodeError, OSError):
        return []
    phrases: list[str] = []
    for pkg in packages[-limit:]:
        theme = str(pkg.get("themeAngle") or pkg.get("description") or "").strip()
        main = str(pkg.get("mainFeature") or "").strip()
        tabs = " / ".join(
            str(pkg.get(k) or "")
            for k in ("tab1Name", "tab2Name", "tab3Name")
            if pkg.get(k)
        )
        bits = [b for b in (theme, main, tabs) if b]
        if bits:
            phrases.append(" | ".join(bits))
    return phrases


def build_context_payload(
    *,
    cfg: BatchConfig,
    row: CsvTaskRow,
    desc: str,
    pack_type: str,
    batch_id: str = "",
) -> dict[str, Any]:
    _ = cfg
    seeds = designer_seeds_from_row(row)
    depth_tier = resolve_business_depth_tier(
        core_scene=row.core_scene or "",
        local_feature=row.local_feature or "",
        product_flow=row.product_flow or "",
        theme_angle=row.theme_angle or "",
    )
    return {
        "app": {
            "name": row.name,
            "description": desc,
            "fullName": row.full_name or "",
            "packType": pack_type,
            "runtime": h5_shell_runtime(pack_type) if is_h5_shell(pack_type) else "flutter",
            "stack": stack_for_pack_type(pack_type),
        },
        "designerSeeds": seeds,
        "product": {
            "themeAngle": row.theme_angle or "",
            "track": row.track or "",
            "audience": row.audience or "",
            "coreScene": row.core_scene or "",
            "localFeature": row.local_feature or "",
            "themeCn": row.theme_cn or "",
            "searchQuery": theme_search_query_from_row(row),
        },
        "constraints": {
            "offlineOnly": True,
            "noLogin": True,
            "noFeed": pack_type == "tool_flutter",
            "iapRequired": True,
            "businessDepthTier": depth_tier if is_h5_shell(pack_type) else "",
            "batchId": batch_id,
        },
    }


def build_anti_collision_payload(
    *,
    cfg: BatchConfig,
    row: CsvTaskRow,
    batch_id: str = "",
) -> dict[str, Any]:
    same_batch = _same_batch_summaries(cfg, row, batch_id=batch_id)
    historical = _registry_avoid_phrases(cfg.contentpack_registry)
    anti = {
        "sameBatchUsed": same_batch,
        "historicalAvoid": historical,
        "seedHints": [],
        "mustDiffer": [
            "themeAngle",
            "visualFingerprint",
            "colorMood",
            "navigationPattern",
        ],
        "registryBlock": format_already_used_block(cfg.contentpack_registry),
    }
    return enrich_anti_collision_with_visuals(
        anti,
        ledger_path=design_ledger_path(cfg.project_dir),
        app_name=row.name,
        batch_id=batch_id,
        output_dir=cfg.project_dir / "output",
    )


def _constraints_markdown(pack_type: str) -> str:
    lines = [
        "# Batch Hard Constraints (non-negotiable)",
        "",
        "- Fully offline — no login, cloud sync, or external API.",
        "- Respect `.cursor/rules/*.mdc` iron rules.",
    ]
    if pack_type == "tool_flutter":
        lines.append("- Tool app: exactly 3 tabs, no Feed / community / publish stream.")
    if is_h5_shell(pack_type):
        lines.append("- H5 shell: vault + Bridge contract; legal kit + deflavor rules apply.")
        lines.append(
            "- 功能文档.md MUST meet 《H5壳功能文档深度标准.md》 (businessDepthTier in context.json)."
        )
    lines.extend(
        [
            "",
            "Design decisions come from ui-ux-pro-max outputs in `design-system/` — do not invent parallel UI canon.",
            "",
        ]
    )
    return "\n".join(lines)


def write_skill_input(
    workspace: Path,
    *,
    cfg: BatchConfig,
    row: CsvTaskRow,
    desc: str,
    pack_type: str,
    batch_id: str = "",
) -> Path:
    """Write ``skill-input/`` files; return context.json path."""
    root = workspace / SKILL_INPUT_DIR
    root.mkdir(parents=True, exist_ok=True)

    ctx = build_context_payload(
        cfg=cfg,
        row=row,
        desc=desc,
        pack_type=pack_type,
        batch_id=batch_id,
    )
    anti = build_anti_collision_payload(cfg=cfg, row=row, batch_id=batch_id)

    ctx_path = root / CONTEXT_FILE
    ctx_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / ANTI_COLLISION_FILE).write_text(
        json.dumps(anti, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / CONSTRAINTS_FILE).write_text(
        _constraints_markdown(pack_type),
        encoding="utf-8",
    )
    return ctx_path


def avoid_query_suffix(anti: dict[str, Any]) -> str:
    """Append avoid phrases to uupm search query."""
    parts: list[str] = []
    for item in anti.get("sameBatchUsed") or []:
        if isinstance(item, dict):
            theme = str(item.get("themeAngle") or "").strip()
            if theme:
                parts.append(theme)
    for phrase in (anti.get("historicalAvoid") or [])[:12]:
        parts.append(str(phrase))
    if not parts:
        return ""
    joined = "; ".join(p.strip() for p in parts if p.strip())
    return (
        f" Avoid duplicating sibling visual identity (palette, fonts, layout pattern). "
        f"Must differ in theme and navigation. Context: {joined}."
    )
