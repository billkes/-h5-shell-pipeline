"""skill.pages — canonical + spec-driven page overrides."""

from __future__ import annotations

import json
import re
from datetime import datetime
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

H5_PAGE_QUERY_HINTS: dict[str, str] = {
    "splash": "splash launch loading brand intro animation",
    "welcome": "welcome onboarding legal consent first-run gate",
    "hub": "home dashboard hub navigation tab root category chips browse",
    "list": "list catalog filter search results browse items records",
    "detail": "detail record item view edit notes attachments photos",
    "store": "in-app purchase store consumable credits paywall ribbon",
    "export": "export share card summary weekly report decision",
    "plaza": "bridge plaza internal QA hidden diagnostics",
    "settings": "settings profile preferences privacy terms clear data",
}

H5_PAGE_TYPE_LABELS: dict[str, str] = {
    "splash": "Splash / Launch",
    "welcome": "Onboarding / Welcome Gate",
    "hub": "Hub / Home Dashboard",
    "list": "List / Catalog",
    "detail": "Detail / Record View",
    "store": "IAP Store / Paywall",
    "export": "Export / Share Preview",
    "plaza": "Bridge Plaza (hidden QA)",
    "settings": "Settings / Profile",
}

# Per-page H5 shell semantics — each override must differ from MASTER and from siblings.
H5_PAGE_SPECS: dict[str, dict[str, Any]] = {
    "splash": {
        "layout": {
            "Max Width": "Full viewport (no horizontal scroll)",
            "Layout": "Single centered column; no Tab bar",
            "Sections": "1. Ambient brand wash, 2. Logo/mark, 3. App name + subtitle",
        },
        "spacing": {"Content Density": "Minimal — logo zone only, no cards"},
        "typography": {"Scale": "Display title only; body hidden until handoff"},
        "colors": {"Strategy": "Background + primary accent wash; no CTA buttons"},
        "components": [
            "Required: dual `requestAnimationFrame` then `bridge.call('shellReady')`",
            "Avoid: Tab bar, IAP ribbon, scrollable lists",
            "Avoid: Welcome gate controls on splash route",
        ],
        "unique_components": ["shell/splash_veil handoff", "ambient canvas wash (hub lane hidden)"],
        "recommendations": [
            "Motion: short logo fade/scale; respect `prefers-reduced-motion`",
            "Bridge: first paint must complete before `shellReady`",
            "Navigation: auto-route to welcome or hub after veil dismiss",
        ],
    },
    "welcome": {
        "layout": {
            "Max Width": "480px centered card on full-bleed wash",
            "Layout": "Single column consent gate; no Tab bar",
            "Sections": "1. Value prop hero, 2. Privacy/User links, 3. Continue CTA, 4. Optional demo import",
        },
        "spacing": {"Content Density": "Low — one decision per screen"},
        "typography": {"Scale": "H1 value prop + body legal copy"},
        "colors": {"Strategy": "Primary CTA on muted card; links use accent"},
        "components": [
            "Required: persist first-run flag in local storage",
            "Avoid: Tab bar before Continue",
            "Avoid: Paywall or store entry on welcome",
        ],
        "unique_components": ["welcome gate card", "legal link row", "optional mock import chip"],
        "recommendations": [
            "Show once per install unless data cleared",
            "Continue routes to hub tab root",
            "Listing URLs must match in-app Privacy/User pages",
        ],
    },
    "hub": {
        "layout": {
            "Max Width": "100% with safe-area padding",
            "Layout": "Tab root — category chips + KPI strip + module cards",
            "Sections": "1. Greeting/header, 2. Category chips, 3. Quick actions, 4. Recent items teaser",
        },
        "spacing": {"Content Density": "Medium — scan-friendly chip grid"},
        "typography": {"Scale": "H2 section titles + chip labels"},
        "colors": {"Strategy": "Chips use secondary; cards on background; CTA accent for primary action"},
        "components": [
            "Required: bottom Tab bar visible (≥3 tabs)",
            "Required: chip tap → list route with filter context",
            "Avoid: Bridge plaza entry on hub",
        ],
        "unique_components": ["category chip rail", "KPI/stat strip", "recent items carousel"],
        "recommendations": [
            "Anchor navigation for the product's core scene",
            "Empty hub must still show chips + CTA to add first item",
            "Use MASTER pattern sections for hero/features rhythm",
        ],
    },
    "list": {
        "layout": {
            "Max Width": "100%",
            "Layout": "Filter bar + scrollable card/list column",
            "Sections": "1. Search/filter bar, 2. Sort control, 3. Item cards, 4. FAB or footer add",
        },
        "spacing": {"Content Density": "High — compact rows with 44px tap targets"},
        "typography": {"Scale": "Body primary for titles; muted meta line"},
        "colors": {"Strategy": "Cards on muted surface; active filter chip = primary"},
        "components": [
            "Required: empty state with CTA back to hub",
            "Required: row tap → detail route",
            "Avoid: Paywall blocking list browse",
        ],
        "unique_components": ["filter chip bar", "sort dropdown", "swipe or overflow actions (optional)"],
        "recommendations": [
            "Support tag/date filters from product flow",
            "Skeleton rows while IndexedDB loads",
            "Pull-to-refresh optional; offline-only",
        ],
    },
    "detail": {
        "layout": {
            "Max Width": "720px centered column inside Tab stack",
            "Layout": "Header + editable fields + attachment gallery",
            "Sections": "1. Title/status, 2. Core fields, 3. Notes, 4. Photo attachments, 5. Save/delete",
        },
        "spacing": {"Content Density": "Medium — form field rhythm from MASTER spacing tokens"},
        "typography": {"Scale": "H2 record title + body fields"},
        "colors": {"Strategy": "Destructive for delete; primary for save"},
        "components": [
            "Required: back navigation to list preserving filter",
            "Required: attachment picker via Bridge when photos enabled",
            "Avoid: Full-screen paywall overlay on detail",
        ],
        "unique_components": ["inline field editors", "attachment thumbnail grid", "status badge"],
        "recommendations": [
            "Autosave or explicit Save with toast feedback",
            "Validate required fields before leave",
            "Deep link: `#/detail/:id`",
        ],
    },
    "store": {
        "layout": {
            "Max Width": "560px centered paywall column",
            "Layout": "Credit balance header + product cards + legal footnote",
            "Sections": "1. Balance ribbon, 2. Consumable packs, 3. Purchase CTA per SKU, 4. Terms",
        },
        "spacing": {"Content Density": "Medium — one SKU per card"},
        "typography": {"Scale": "Price emphasis on SKU title"},
        "colors": {"Strategy": "Accent CTA per MASTER; muted legal text"},
        "components": [
            "Required: consumable IAP only (no subscription copy)",
            "Required: Bridge purchase flow + ledger update",
            "Avoid: Restore purchases button (consumable policy)",
        ],
        "unique_components": ["balance ribbon", "SKU cards", "purchase pending state"],
        "recommendations": [
            "Entry from soft paywall gate or Settings",
            "Show post-purchase balance immediately",
            "Receipt-free local ledger acceptable for demo",
        ],
    },
    "export": {
        "layout": {
            "Max Width": "640px share-card preview",
            "Layout": "Preview canvas + export actions row",
            "Sections": "1. Summary card preview, 2. Date range chip, 3. Share/save actions, 4. Confirmation toast",
        },
        "spacing": {"Content Density": "Low — focus on single summary artifact"},
        "typography": {"Scale": "Card title + stat numerals"},
        "colors": {"Strategy": "Card uses elevated surface; actions on accent"},
        "components": [
            "Required: weekly/date-range selector",
            "Required: Bridge share or download when available",
            "Avoid: Empty export without user data",
        ],
        "unique_components": ["summary card renderer", "range chip", "share action bar"],
        "recommendations": [
            "Gate export when list is empty — offer CTA to add items",
            "PNG/PDF/blob per Bridge capability",
            "Route: `#/export` or modal from hub",
        ],
    },
    "plaza": {
        "layout": {
            "Max Width": "100% diagnostic grid",
            "Layout": "Button matrix + result log (non-Tab)",
            "Sections": "1. Capability header, 2. Bridge action buttons, 3. Result/toast area, 4. Back to Settings",
        },
        "spacing": {"Content Density": "High — dense QA button grid"},
        "typography": {"Scale": "Mono-friendly labels for Bridge actions"},
        "colors": {"Strategy": "Neutral diagnostic chrome; status colors for pass/fail"},
        "components": [
            "If Screen Inventory lists `#/plaza`: route required — never in Tab bar",
            "If declared: entry via Settings long-press version 3s only",
            "Avoid: Visible plaza CTA on hub/home in production build",
        ],
        "unique_components": ["shell/bridge_plaza", "shell/bridge_toast", "shell/permission_gate"],
        "recommendations": [
            "Render buttons from `bridgeCapabilities` subset",
            "Strip `plaza-dev-entrance` before App Store build",
            "Browser dev may error — expected without native Bridge",
        ],
    },
    "settings": {
        "layout": {
            "Max Width": "100% form list",
            "Layout": "Grouped settings sections + version footer",
            "Sections": "1. Preferences toggles, 2. Data (clear/demo), 3. Legal links, 4. Version (hidden plaza entry)",
        },
        "spacing": {"Content Density": "Medium — standard iOS-like settings rows"},
        "typography": {"Scale": "Row title + chevron/meta"},
        "colors": {"Strategy": "Grouped cards on muted; destructive on clear-data"},
        "components": [
            "Required: in-app Privacy + User agreement links",
            "Required: version row long-press 3s → `#/plaza`",
            "Avoid: Login/account section (offline-only)",
        ],
        "unique_components": ["settings row groups", "clear data confirm modal", "version long-press handler"],
        "recommendations": [
            "Clear data returns to welcome gate",
            "Optional demo import chip for review path",
            "Tab: usually 4th tab or overflow",
        ],
    },
}

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


def _page_query(base_query: str, page: str) -> str:
    hint = H5_PAGE_QUERY_HINTS.get(page, page)
    return f"{base_query} {hint} screen"


def _product_context_block(ctx: dict[str, Any], row: CsvTaskRow) -> str:
    product = ctx.get("product") or {}
    constraints = ctx.get("constraints") or {}
    lines = [
        "## Product Context (skill.pages)",
        "",
        f"- **Audience:** {product.get('audience') or row.audience or '—'}",
        f"- **Core scene:** {product.get('coreScene') or row.core_scene or '—'}",
        f"- **Local feature:** {product.get('localFeature') or row.local_feature or '—'}",
        f"- **Product flow:** {row.product_flow or '—'}",
    ]
    topo = constraints.get("interactionTopologyLabel") or constraints.get("interactionTopology")
    if topo:
        lines.append(f"- **Interaction topology:** {topo}")
    lines.append("")
    return "\n".join(lines)


def _pattern_context_lines(
    candidate: dict[str, Any],
    ctx: dict[str, Any],
    *,
    project_dir: Path | None = None,
) -> list[str]:
    from batch.skill_product_bind import load_product_bind, navigation_pattern_canon

    pattern = candidate.get("pattern") or {}
    style = candidate.get("style") or {}
    bind = ctx if (ctx.get("product") or ctx.get("constraints")) else load_product_bind(Path("."))
    pdir = project_dir or Path(".")
    lines: list[str] = []
    nav = navigation_pattern_canon(
        bind,
        project_dir=pdir,
        fallback=str((bind.get("designerSeeds") or {}).get("navigationPattern") or ""),
    )
    if nav:
        lines.append(f"- **Navigation pattern:** {nav}")
        lines.append("- **IA source:** productFlow + interaction topology (not uupm page pattern name)")
    if pattern.get("name"):
        lines.append(f"- **Visual tone (uupm):** {pattern['name']}")
    if pattern.get("sections"):
        lines.append(f"- **Visual sections reference:** {pattern['sections']}")
    if style.get("name"):
        lines.append(f"- **Shape language:** {style['name']}")
    if style.get("effects"):
        lines.append(f"- **Motion/effects:** {style['effects']}")
    return lines


def _format_h5_page_override_md(
    page: str,
    candidate: dict[str, Any],
    ctx: dict[str, Any],
    row: CsvTaskRow,
) -> str:
    """Write H5 canonical page overrides locally — do not delegate to uupm generic landing search."""
    spec = H5_PAGE_SPECS[page]
    project = candidate.get("project_name") or row.name
    page_title = page.replace("-", " ").replace("_", " ").title()
    page_type = H5_PAGE_TYPE_LABELS.get(page, page_title)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"# {page_title} Page Overrides",
        "",
        f"> **PROJECT:** {project}",
        f"> **Generated:** {timestamp}",
        f"> **Page Type:** {page_type}",
        "",
        "> ⚠️ **IMPORTANT:** Rules in this file **override** the Master file (`design-system/MASTER.md`).",
        "> Only deviations from the Master are documented here. For all other rules, refer to the Master.",
        "",
        "---",
        "",
        _product_context_block(ctx, row).rstrip(),
        "",
        "---",
        "",
        "## Page-Specific Rules",
        "",
    ]

    pattern_lines = _pattern_context_lines(candidate, ctx)
    if pattern_lines:
        lines.append("### Design System Anchors")
        lines.append("")
        lines.extend(pattern_lines)
        lines.append("")

    for section_key, heading in (
        ("layout", "Layout Overrides"),
        ("spacing", "Spacing Overrides"),
        ("typography", "Typography Overrides"),
        ("colors", "Color Overrides"),
    ):
        lines.append(f"### {heading}")
        lines.append("")
        block = spec.get(section_key) or {}
        if block:
            for key, value in block.items():
                lines.append(f"- **{key}:** {value}")
        else:
            lines.append(f"- No overrides — use Master {section_key}")
        lines.append("")

    lines.append("### Component Overrides")
    lines.append("")
    for comp in spec.get("components") or []:
        lines.append(f"- {comp}")
    lines.append("")

    lines.extend(["---", "", "## Page-Specific Components", ""])
    for comp in spec.get("unique_components") or []:
        lines.append(f"- {comp}")
    if not spec.get("unique_components"):
        lines.append("- No unique components for this page")
    lines.append("")

    lines.extend(["---", "", "## Recommendations", ""])
    for rec in spec.get("recommendations") or []:
        lines.append(f"- {rec}")
    lines.append("")

    return "\n".join(lines)


def _write_h5_page_file(
    pages_dir: Path,
    *,
    page: str,
    candidate: dict[str, Any],
    ctx: dict[str, Any],
    row: CsvTaskRow,
) -> Path:
    pages_dir.mkdir(parents=True, exist_ok=True)
    path = pages_dir / f"{page}.md"
    path.write_text(
        _format_h5_page_override_md(page, candidate, ctx, row),
        encoding="utf-8",
    )
    return path


def _persist_pages(
    cfg: BatchConfig,
    candidate: dict[str, Any],
    workspace: Path,
    *,
    pages: list[str],
    base_query: str,
    ctx: dict[str, Any],
    row: CsvTaskRow,
    h5_canonical: bool = False,
) -> list[Path]:
    inject_uupm_scripts(cfg)
    from design_system import persist_design_system  # type: ignore[import-not-found]

    created: list[Path] = []
    # H5 canonical pages are written locally; do not re-persist MASTER (skill.adapt owns it).
    if not h5_canonical:
        persist_design_system(candidate, None, str(workspace), base_query)
    pages_dir = design_system_dir_for_app(workspace, row.name) / "pages"
    for page in pages:
        if h5_canonical and page in H5_PAGE_SPECS:
            created.append(
                _write_h5_page_file(
                    pages_dir,
                    page=page,
                    candidate=candidate,
                    ctx=ctx,
                    row=row,
                )
            )
            continue
        page_query = _page_query(base_query, page)
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
    ctx_path = workspace / "skill-input" / "context.json"
    ctx = json.loads(ctx_path.read_text(encoding="utf-8")) if ctx_path.is_file() else {}
    base_query = _base_query(workspace, row)

    pages = list(CANONICAL_H5_PAGES) if is_h5_shell(pack_type) else ["welcome", "home", "store", "export"]
    _persist_pages(
        cfg,
        candidate,
        workspace,
        pages=pages,
        base_query=base_query,
        ctx=ctx,
        row=row,
        h5_canonical=is_h5_shell(pack_type),
    )

    master = master_path_for_app(workspace, row.name)
    if not master.is_file():
        raise RuntimeError(f"skill.pages 未生成 MASTER.md: {master}")
    if is_h5_shell(pack_type):
        from batch.skill_product_bind import load_product_bind, master_category_label
        from batch.uupm_design_system import _patch_master_category

        _patch_master_category(master, master_category_label(load_product_bind(workspace)))
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
    ctx_path = workspace / "skill-input" / "context.json"
    ctx = json.loads(ctx_path.read_text(encoding="utf-8")) if ctx_path.is_file() else {}
    base_query = _base_query(workspace, row)
    _persist_pages(
        cfg,
        candidate,
        workspace,
        pages=missing,
        base_query=base_query,
        ctx=ctx,
        row=row,
    )
    return [f"page override: {s}" for s in missing]


def format_pages_block(workspace: Path, app_name: str) -> str:
    from batch.h5_page_scaffold import format_page_scaffold_prompt_block

    pages_dir = design_system_dir_for_app(workspace, app_name) / "pages"
    scaffold_block = format_page_scaffold_prompt_block(workspace, app_name)
    if not pages_dir.is_dir():
        return scaffold_block
    files = sorted(pages_dir.glob("*.md"))
    if not files:
        return scaffold_block
    lines = ["[Page Overrides — design-system/pages/]"]
    for path in files:
        lines.append(f"- `{path.relative_to(workspace).as_posix()}`")
    if scaffold_block:
        lines.append("")
        lines.append(scaffold_block)
    return "\n".join(lines)
