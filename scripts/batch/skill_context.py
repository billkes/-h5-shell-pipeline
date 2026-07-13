"""Build skill-input context for ui-ux-pro-max (facts + anti-collision, no design lock)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from batch.design_diversity import (
    design_ledger_path,
    enrich_anti_collision_with_visuals,
    theme_search_query_from_row,
)
from batch.pack_type import h5_shell_runtime, is_flutter_runtime, is_h5_shell
from batch.registry import format_already_used_block

if TYPE_CHECKING:
    from batch.config import BatchConfig
    from batch.csv_tasks import CsvTaskRow

SKILL_INPUT_DIR = "skill-input"
CONTEXT_FILE = "context.json"
ANTI_COLLISION_FILE = "anti-collision-context.json"
CONSTRAINTS_FILE = "constraints.md"


def stack_for_pack_type(pack_type: str) -> str:
    if is_h5_shell(pack_type):
        return "html-tailwind"
    if is_flutter_runtime(pack_type):
        return "flutter"
    return "flutter"


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
    return {
        "app": {
            "name": row.name,
            "description": desc,
            "fullName": row.full_name or "",
            "packType": pack_type,
            "runtime": h5_shell_runtime(pack_type) if is_h5_shell(pack_type) else "flutter",
            "stack": stack_for_pack_type(pack_type),
        },
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
