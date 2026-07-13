"""skill.pages — canonical + spec-driven page overrides."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from batch.pack_type import is_h5_shell
from batch.skill_resolve import inject_uupm_scripts, integration_enabled
from batch.uupm_design_system import (
    design_query_from_context,
    design_system_dir_for_app,
    master_path_for_app,
)

if TYPE_CHECKING:
    from batch.config import BatchConfig
    from batch.csv_tasks import CsvTaskRow

CANONICAL_H5_PAGES: tuple[str, ...] = (
    "splash",
    "welcome",
    "hub",
    "list",
    "detail",
    "store",
    "export",
    "plaza",
    "settings",
)

_SCREEN_SLUG_RE = re.compile(
    r"(?:^|\n)\s*(?:[-*]|\d+\.)\s*\**([A-Za-z][\w\s/-]{1,40})\**",
    re.M,
)


def _slugify_page(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "screen"


def _load_selected_candidate(workspace: Path, app_name: str = "") -> dict[str, Any]:
    path = workspace / "skill-adapt" / "selected-candidate.json"
    if not path.is_file():
        raise RuntimeError("skill.pages 缺少 skill-adapt/selected-candidate.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    cand_id = data.get("candidateId") or "c1"
    for cand_file in workspace.glob("design-system/*/candidates.json"):
        try:
            blob = json.loads(cand_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for cand in blob.get("candidates") or []:
            if cand.get("id") == cand_id:
                out = dict(cand)
                out["project_name"] = app_name or workspace.name
                return out
    ds = data.get("designSystem") or {}
    if not ds:
        raise RuntimeError("skill.pages: selected-candidate.json 无 designSystem")
    return {"id": cand_id, **ds, "project_name": app_name or workspace.name}


def _base_query(workspace: Path, row: CsvTaskRow) -> str:
    ctx_path = workspace / "skill-input" / "context.json"
    anti_path = workspace / "skill-input" / "anti-collision-context.json"
    ctx = json.loads(ctx_path.read_text(encoding="utf-8")) if ctx_path.is_file() else {}
    anti = json.loads(anti_path.read_text(encoding="utf-8")) if anti_path.is_file() else {}
    return design_query_from_context(ctx, anti, row=row)


def _persist_pages(
    cfg: BatchConfig,
    candidate: dict[str, Any],
    workspace: Path,
    *,
    pages: list[str],
    base_query: str,
) -> list[Path]:
    inject_uupm_scripts(cfg)
    from design_system import persist_design_system  # type: ignore[import-not-found]

    created: list[Path] = []
    persist_design_system(candidate, None, str(workspace), base_query)
    for page in pages:
        page_query = f"{base_query} {page} screen"
        result = persist_design_system(candidate, page, str(workspace), page_query)
        for raw in result.get("created_files") or []:
            created.append(Path(raw))
    return created


def run_skill_pages(
    *,
    cfg: BatchConfig,
    workspace: Path,
    row: CsvTaskRow,
    pack_type: str,
) -> Path:
    """Generate design-system/{slug}/pages/*.md from selected candidate."""
    ds_dir = design_system_dir_for_app(workspace, row.name)
    if not integration_enabled(cfg, "page_overrides"):
        return ds_dir

    inject_uupm_scripts(cfg)
    candidate = _load_selected_candidate(workspace, row.name)
    candidate["project_name"] = row.name
    base_query = _base_query(workspace, row)

    pages = list(CANONICAL_H5_PAGES) if is_h5_shell(pack_type) else ["welcome", "home", "store", "export"]
    _persist_pages(cfg, candidate, workspace, pages=pages, base_query=base_query)

    master = master_path_for_app(workspace, row.name)
    if not master.is_file():
        raise RuntimeError(f"skill.pages 未生成 MASTER.md: {master}")
    return ds_dir / "pages"


def _extract_screen_slugs(spec_text: str) -> list[str]:
    slugs: list[str] = []
    in_inventory = False
    for line in spec_text.splitlines():
        if re.search(r"screen\s+inventory", line, re.I):
            in_inventory = True
            continue
        if in_inventory and line.strip().startswith("#"):
            if "screen" not in line.lower():
                in_inventory = False
            continue
        if not in_inventory:
            continue
        m = _SCREEN_SLUG_RE.search(line)
        if m:
            slug = _slugify_page(m.group(1))
            if slug not in slugs and slug not in ("screen", "inventory"):
                slugs.append(slug)
    return slugs


def sync_pages_from_spec(
    *,
    cfg: BatchConfig,
    workspace: Path,
    row: CsvTaskRow,
    pack_type: str,
) -> list[str]:
    """After plan.gate — add page overrides for screens in 功能文档.md."""
    if not integration_enabled(cfg, "page_overrides"):
        return []
    spec = workspace / "功能文档.md"
    if not spec.is_file():
        return []
    slugs = _extract_screen_slugs(spec.read_text(encoding="utf-8", errors="replace"))
    if not slugs:
        return []

    pages_dir = design_system_dir_for_app(workspace, row.name) / "pages"
    existing = {p.stem for p in pages_dir.glob("*.md")} if pages_dir.is_dir() else set()
    missing = [s for s in slugs if s not in existing]
    if not missing:
        return []

    inject_uupm_scripts(cfg)
    candidate = _load_selected_candidate(workspace, row.name)
    candidate["project_name"] = row.name
    base_query = _base_query(workspace, row)
    _persist_pages(cfg, candidate, workspace, pages=missing, base_query=base_query)
    return [f"page override: {s}" for s in missing]


def format_pages_block(workspace: Path, app_name: str) -> str:
    pages_dir = design_system_dir_for_app(workspace, app_name) / "pages"
    if not pages_dir.is_dir():
        return ""
    files = sorted(pages_dir.glob("*.md"))
    if not files:
        return ""
    lines = ["[Page Overrides — design-system/pages/]"]
    for path in files:
        lines.append(f"- `{path.relative_to(workspace).as_posix()}`")
    return "\n".join(lines)
