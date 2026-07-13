"""skill.enrich — multi-domain BM25 briefs from ui-ux-pro-max."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from batch.skill_icons import format_h5_icon_landing_block
from batch.skill_resolve import inject_uupm_scripts, integration_enabled
from batch.uupm_design_system import design_query_from_context, design_system_dir_for_app
from batch.workspace import dart_prefix

if TYPE_CHECKING:
    from batch.config import BatchConfig
    from batch.csv_tasks import CsvTaskRow

_CHART_KEYWORDS = re.compile(
    r"budget|analytics|chart|forecast|stat|dashboard|tracker|list|grid|data",
    re.I,
)

_PRE_DELIVERY = """## Pre-Delivery Checklist (ui-ux-pro-max)

- [ ] Contrast 4.5:1 minimum for body text
- [ ] Touch targets >= 44pt / 48dp
- [ ] prefers-reduced-motion respected
- [ ] No emojis as structural icons (inline SVG only)
- [ ] Focus states visible for keyboard navigation
- [ ] Test at 375px width + landscape
"""


def _format_search_md(domain: str, query: str, result: dict[str, Any], *, h5_prefix: str = "") -> str:
    lines = [
        f"# {domain.upper()} Brief (skill.enrich)",
        "",
        f"**Query:** {query}",
        f"**Source:** {result.get('file', '?')} | **Found:** {result.get('count', 0)}",
        "",
    ]
    for i, row in enumerate(result.get("results") or [], 1):
        lines.append(f"## {i}. {row.get('Category') or row.get('Issue') or row.get('Icon Name') or row.get('Data Type') or 'Result'}")
        for key, value in row.items():
            if not value:
                continue
            text = str(value)
            if len(text) > 400:
                text = text[:400] + "..."
            lines.append(f"- **{key}:** {text}")
        lines.append("")
    if domain == "icons" and h5_prefix:
        lines.append(format_h5_icon_landing_block(h5_prefix).rstrip())
        lines.append("")
    lines.append(_PRE_DELIVERY.strip())
    lines.append("")
    return "\n".join(lines)


def _search_domain(query: str, domain: str, max_results: int) -> dict[str, Any]:
    from core import search  # type: ignore[import-not-found]

    return search(query, domain, max_results)


def run_skill_enrich(
    *,
    cfg: BatchConfig,
    workspace: Path,
    row: CsvTaskRow,
) -> Path:
    """Generate ux/icons/web/chart briefs under design-system/{slug}/."""
    if not integration_enabled(cfg, "enrich_domains"):
        ds_dir = design_system_dir_for_app(workspace, row.name)
        ds_dir.mkdir(parents=True, exist_ok=True)
        return ds_dir

    ctx_path = workspace / "skill-input" / "context.json"
    anti_path = workspace / "skill-input" / "anti-collision-context.json"
    if not ctx_path.is_file():
        raise RuntimeError("skill.enrich 缺少 skill-input/context.json")
    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    anti = json.loads(anti_path.read_text(encoding="utf-8")) if anti_path.is_file() else {}
    query = design_query_from_context(ctx, anti, row=row)

    inject_uupm_scripts(cfg)
    ds_dir = design_system_dir_for_app(workspace, row.name)
    ds_dir.mkdir(parents=True, exist_ok=True)

    domains: list[tuple[str, str, int]] = [
        ("ux", "ux-checklist.md", 8),
        ("icons", "icon-brief.md", 6),
        ("web", "h5-interface-brief.md", 6),
    ]
    if _CHART_KEYWORDS.search(query):
        domains.append(("chart", "chart-brief.md", 4))

    prefix = dart_prefix(workspace)

    for domain, filename, max_results in domains:
        result = _search_domain(query, domain, max_results)
        (ds_dir / filename).write_text(
            _format_search_md(domain, query, result, h5_prefix=prefix if domain == "icons" else ""),
            encoding="utf-8",
        )

    meta_path = ds_dir / "enrich-meta.json"
    meta = {
        "query": query,
        "domains": [d[0] for d in domains],
        "files": [d[1] for d in domains],
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ds_dir


def enrich_file_paths(workspace: Path, app_name: str) -> dict[str, Path]:
    ds_dir = design_system_dir_for_app(workspace, app_name)
    mapping = {
        "ux": ds_dir / "ux-checklist.md",
        "icons": ds_dir / "icon-brief.md",
        "web": ds_dir / "h5-interface-brief.md",
        "chart": ds_dir / "chart-brief.md",
    }
    return {k: v for k, v in mapping.items() if v.is_file()}


def format_enrich_summary_block(workspace: Path, app_name: str) -> str:
    paths = enrich_file_paths(workspace, app_name)
    if not paths:
        return ""
    lines = ["[Skill Enrich — ui-ux-pro-max domain briefs]"]
    for key, path in paths.items():
        rel = path.relative_to(workspace).as_posix()
        lines.append(f"- {key}: `{rel}`")
    return "\n".join(lines)
