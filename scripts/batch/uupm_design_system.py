"""ui-ux-pro-max client — skill.design step (candidates, MASTER, stack, pages)."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from batch.design_diversity import (
    design_ledger_path,
    diversify_candidates,
    is_banned_saas_design,
    register_design_selection,
    theme_search_query_from_row,
)
from batch.candidate_similarity import (
    run_fallback_ladder,
    candidate_similarity,
    anti_style_search,
    load_registry_packages,
    extract_candidate_registry_entry,
    SimilarityResult,
    THRESHOLD_WARN,
    THRESHOLD_FAIL,
    MAX_RETRIES,
)
from batch.pack_type import is_h5_shell
from batch.skill_context import (
    h5_architecture_stack,
    native_stack_for_pack_type,
    stack_for_pack_type,
)
from batch.skill_resolve import inject_uupm_scripts, resolve_uupm_package_dir, resolve_skill_repo_root

if TYPE_CHECKING:
    from batch.config import BatchConfig
    from batch.csv_tasks import CsvTaskRow

UUPM_PACKAGE_SUFFIX = Path("src/ui-ux-pro-max")
UUPM_SCRIPTS_SUFFIX = UUPM_PACKAGE_SUFFIX / "scripts"
CURSOR_UUPM_SKILL_REL = Path(".cursor/skills/ui-ux-pro-max")
DESIGN_SYSTEM_DIRNAME = "design-system"
MASTER_FILENAME = "MASTER.md"
POINTER_FILENAME = "设计系统建议.md"
META_FILENAME = "META.json"
CANDIDATES_FILENAME = "candidates.json"


def _uupm_skill_repo_candidates(cfg: BatchConfig) -> list[Path]:
    """Ordered skill repo roots (BatchConfig → env → yaml → sibling repo)."""
    candidates: list[Path] = []

    # 1. BatchConfig field (loaded via from_env: CLI override > env > config.yaml)
    cfg_dir = (cfg.uupm_skill_dir or "").strip()
    if cfg_dir:
        candidates.append(Path(cfg_dir).expanduser())

    # 2. Environment variable (backward compat and direct shell usage)
    env = (os.environ.get("UUPM_SKILL_DIR") or "").strip()
    if env:
        candidates.append(Path(env).expanduser())

    # 3. Direct yaml read for callers that instantiate BatchConfig without from_env
    yaml_path = cfg.config_dir / "config.yaml"
    if yaml_path.is_file():
        try:
            import yaml

            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            uupm = data.get("uupm") if isinstance(data, dict) else None
            if isinstance(uupm, dict):
                raw = str(uupm.get("skill_dir") or "").strip()
                if raw:
                    candidates.append(Path(raw).expanduser())
        except Exception:
            pass

    # 4. Default sibling repo names
    for base in (cfg.project_dir.parent, cfg.project_dir.parent.parent):
        candidates.append(base / "ui-ux-pro-max-skill")

    seen: set[str] = set()
    ordered: list[Path] = []
    for root in candidates:
        key = str(root.resolve()) if root.exists() else str(root)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(root)
    return ordered


def _scripts_dir_from_root(root: Path) -> Path | None:
    nested = root / UUPM_SCRIPTS_SUFFIX
    if nested.is_dir() and (nested / "search.py").is_file():
        return nested
    if root.is_dir() and (root / "search.py").is_file():
        return root
    return None


def resolve_uupm_scripts_dir(cfg: BatchConfig) -> Path:
    """Locate ui-ux-pro-max ``scripts/`` (config → env → sibling repo)."""
    from batch.skill_resolve import resolve_uupm_scripts_dir as _resolve

    return _resolve(cfg)


def resolve_uupm_package_dir(cfg: BatchConfig) -> Path:
    from batch.skill_resolve import resolve_uupm_package_dir as _resolve

    return _resolve(cfg)


def resolve_uupm_skill_repo_root(cfg: BatchConfig) -> Path | None:
    return resolve_skill_repo_root(cfg)


def _inject_scripts(scripts_dir: Path) -> None:
    scripts = str(scripts_dir.resolve())
    if scripts not in sys.path:
        sys.path.insert(0, scripts)


def _keyword_dial(
    text: str,
    *,
    low_words: tuple[str, ...],
    high_words: tuple[str, ...],
    default: int = 5,
) -> int:
    blob = (text or "").lower()
    score = default
    for word in low_words:
        if word in blob:
            score -= 2
    for word in high_words:
        if word in blob:
            score += 2
    return max(1, min(10, score))


def designer_dials_from_row(row: CsvTaskRow) -> dict[str, int]:
    """Map CSV theme/product flow to uupm variance/motion/density (1-10)."""
    angle = (row.theme_angle or "").lower()
    flow = (row.product_flow or "").lower()
    full = f"{angle} {flow}".strip()

    variance = _keyword_dial(
        full,
        low_words=("minimal", "soft rounded", "pill", "squircle", "centered", "pastel", "organic"),
        high_words=(
            "asymmetric", "brutal", "bold", "architectural", "neon",
            "experimental", "sharp rectangular", "overlapping",
        ),
    )
    motion = _keyword_dial(
        flow,
        low_words=("subtle", "fade", "static", "minimal", "gentle"),
        high_words=("spring", "bounce", "parallax", "complex", "playful", "elastic", "stagger"),
    )
    density = _keyword_dial(
        full,
        low_words=("single focus", "hero-first", "minimal", "wizard", "one-screen"),
        high_words=("dashboard", "grid", "index grid", "dense", "hub", "multi-panel", "drill-down"),
    )
    return {"variance": variance, "motion": motion, "density": density}


def _dial_variants(base: dict[str, int]) -> list[tuple[str, dict[str, int]]]:
    v, m, d = base["variance"], base["motion"], base["density"]
    return [
        ("c1", {"variance": v, "motion": m, "density": d}),
        ("c2", {"variance": max(1, min(10, v + 2)), "motion": m, "density": d}),
        ("c3", {"variance": max(1, min(10, v - 2)), "motion": max(1, min(10, m + 1)), "density": max(1, min(10, d + 1))}),
    ]


def _prefer_non_saas_candidate(
    selected: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Thin gate: prefer a non-SaaS-branded candidate when available."""
    pool = list(candidates or [])
    if selected is not None:
        pool = [selected] + [c for c in pool if c is not selected]
    if not pool:
        raise RuntimeError("skill.design: no candidates to persist")
    for cand in pool:
        if isinstance(cand, dict) and not is_banned_saas_design(cand):
            if cand is not selected and selected is not None and is_banned_saas_design(selected):
                print(
                    f"[DESIGN] Avoiding SaaS-branded pick "
                    f"{(selected.get('style') or {}).get('name')!r} → "
                    f"{(cand.get('style') or {}).get('name')!r}"
                )
            return cand
    return pool[0]


def design_query_from_context(
    ctx: dict[str, Any],
    anti: dict[str, Any] | None = None,
    row: CsvTaskRow | None = None,
) -> str:
    """Short English BM25 query for ui-ux-pro-max (README-style keyword search).

    Anti-collision is handled by registry similarity + anti-collision-context.json,
    not by appending history blobs to the search query.
    """
    _ = anti
    if row is not None:
        return theme_search_query_from_row(row)

    product = ctx.get("product") or {}
    search_query = str(product.get("searchQuery") or "").strip()
    if search_query:
        return search_query

    app = ctx.get("app") or {}

    class _ProductRow:
        pass

    row_like = _ProductRow()
    row_like.name = str(app.get("name") or "").strip()
    row_like.track = str(product.get("track") or "").strip()
    row_like.audience = str(product.get("audience") or "").strip()
    row_like.core_scene = str(product.get("coreScene") or "").strip()
    row_like.local_feature = str(product.get("localFeature") or "").strip()
    return theme_search_query_from_row(row_like)


def master_path_for_app(workspace: Path, app_name: str) -> Path:
    slug = app_name.lower().replace(" ", "-")
    return workspace / DESIGN_SYSTEM_DIRNAME / slug / MASTER_FILENAME


def design_system_dir_for_app(workspace: Path, app_name: str) -> Path:
    slug = app_name.lower().replace(" ", "-")
    return workspace / DESIGN_SYSTEM_DIRNAME / slug


def find_design_system_master(workspace: Path, app_name: str = "") -> Path | None:
    if app_name.strip():
        direct = master_path_for_app(workspace, app_name.strip())
        if direct.is_file():
            return direct
    root = workspace / DESIGN_SYSTEM_DIRNAME
    if root.is_dir():
        matches = sorted(root.glob(f"*/{MASTER_FILENAME}"))
        if matches:
            return matches[0]
    return None


_MASTER_ROLE_MAP: dict[str, str] = {
    "primary": "primary",
    "on primary": "on_primary",
    "secondary": "secondary",
    "accent/cta": "accent",
    "accent": "accent",
    "cta": "accent",
    "background": "background",
    "foreground": "foreground",
    "muted": "muted",
    "border": "border",
    "destructive": "destructive",
    "ring": "ring",
}


def _normalize_master_role(raw: str) -> str | None:
    role = raw.strip().lower()
    if role in _MASTER_ROLE_MAP:
        return _MASTER_ROLE_MAP[role]
    for label, key in _MASTER_ROLE_MAP.items():
        if label in role:
            return key
    return None


def parse_master_palette(text: str) -> dict[str, str]:
    """Parse MASTER §Color Palette table → token keys (primary, accent, …)."""
    section_m = re.search(
        r"###\s*Color Palette([\s\S]*?)(?=###|\n---|\Z)",
        text,
        re.I,
    )
    if not section_m:
        return {}
    out: dict[str, str] = {}
    for row in re.finditer(
        r"\|\s*([^|]+?)\s*\|\s*`?(#[0-9A-Fa-f]{3,8})`?\s*\|",
        section_m.group(1),
    ):
        key = _normalize_master_role(row.group(1))
        if key:
            out[key] = row.group(2).upper()
    return out


def parse_master_typography(text: str) -> dict[str, str]:
    """Parse MASTER §Typography → heading/body/google_fonts_url."""
    out: dict[str, str] = {}
    hm = re.search(r"\*\*Heading Font:\*\*\s*(.+)", text)
    bm = re.search(r"\*\*Body Font:\*\*\s*(.+)", text)
    if hm:
        out["heading"] = hm.group(1).strip()
    if bm:
        out["body"] = bm.group(1).strip()
    for pattern in (
        r"@import\s+url\(['\"]?([^'\";\)]+)['\"]?\)",
        r"https://fonts\.googleapis\.com/css2[^\s\)'\"`]+",
    ):
        m = re.search(pattern, text)
        if m:
            url = m.group(1) if m.lastindex else m.group(0)
            out["google_fonts_url"] = url.strip()
            break
    return out


def parse_master_shadows(text: str) -> dict[str, str]:
    """Parse MASTER §Shadow Depths table."""
    section_m = re.search(
        r"###\s*Shadow Depths([\s\S]*?)(?=###|\n---|\Z)",
        text,
        re.I,
    )
    if not section_m:
        return {
            "shadow_sm": "0 1px 2px rgba(0,0,0,0.05)",
            "shadow_md": "0 4px 6px rgba(0,0,0,0.1)",
            "shadow_lg": "0 10px 15px rgba(0,0,0,0.1)",
        }
    out: dict[str, str] = {}
    for row in re.finditer(
        r"\|\s*`?(--shadow-\w+)`?\s*\|\s*`?([^|`]+)`?\s*\|",
        section_m.group(1),
    ):
        # --shadow-md → shadow_md (not __shadow_md)
        key = row.group(1).strip("`").removeprefix("--").replace("-", "_")
        out[key] = row.group(2).strip()
    return out


def parse_master_spacing(text: str) -> dict[str, str]:
    section_m = re.search(
        r"###\s*Spacing Variables([\s\S]*?)(?=###|\n---|\Z)",
        text,
        re.I,
    )
    if not section_m:
        return {"md": "16px", "lg": "24px", "sm": "8px"}
    out: dict[str, str] = {}
    for row in re.finditer(
        r"\|\s*`?(--space-\w+)`?\s*\|\s*`?(\d+px)",
        section_m.group(1),
    ):
        out[row.group(1).replace("--space-", "")] = row.group(2)
    return out


def parse_master_style_meta(text: str) -> dict[str, str]:
    """Parse MASTER Style Guidelines / Color Notes / Pattern Name for adapt overlays."""
    out: dict[str, str] = {}
    sm = re.search(r"\*\*Style:\*\*\s*(.+)", text)
    if sm:
        out["style_name"] = sm.group(1).strip()
    km = re.search(r"\*\*Keywords:\*\*\s*(.+)", text)
    if km:
        out["style_keywords"] = km.group(1).strip()
    pm = re.search(r"\*\*Pattern Name:\*\*\s*(.+)", text)
    if pm:
        out["pattern_name"] = pm.group(1).strip()
    cn = re.search(r"\*\*Color Notes:\*\*\s*(.+)", text)
    if cn:
        out["color_notes"] = cn.group(1).strip()
    mood = re.search(r"\*\*Mood:\*\*\s*(.+)", text)
    if mood:
        out["mood"] = mood.group(1).strip()
    ap = re.search(r"##\s*Anti-Patterns[\s\S]*?-\s*❌\s*(.+)", text)
    if ap:
        out["anti_patterns"] = ap.group(1).strip()
    return out


def load_master_design_tokens(workspace: Path, app_name: str = "") -> dict[str, Any]:
    """Return parsed MASTER palette + typography (skill.design visual truth)."""
    master = find_design_system_master(workspace, app_name)
    if not master or not master.is_file():
        return {}
    text = master.read_text(encoding="utf-8", errors="ignore")
    palette = parse_master_palette(text)
    typography = parse_master_typography(text)
    shadows = parse_master_shadows(text)
    spacing = parse_master_spacing(text)
    style_meta = parse_master_style_meta(text)
    if not palette and not typography:
        return {}
    return {
        "palette": palette,
        "typography": typography,
        "shadows": shadows,
        "spacing": spacing,
        "style_meta": style_meta,
        "path": str(master),
    }


def stack_guidelines_path(workspace: Path, app_name: str, stack: str) -> Path:
    slug = app_name.lower().replace(" ", "-")
    safe = stack.replace("/", "-")
    return workspace / DESIGN_SYSTEM_DIRNAME / slug / f"stack-{safe}.md"


def _format_stack_md(stack: str, query: str, results: list[dict[str, str]]) -> str:
    lines = [
        f"# Stack Guidelines — {stack}",
        "",
        f"Query: {query}",
        f"Source: ui-ux-pro-max `stacks/{stack}.csv`",
        "",
    ]
    for i, row in enumerate(results, 1):
        lines.append(f"## {i}. {row.get('Category', row.get('Guideline', 'Guideline'))}")
        for key, val in row.items():
            if val and key not in ("Category",):
                lines.append(f"- **{key}:** {val}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _patch_master_category(master_path: Path, category: str) -> None:
    """Replace uupm-generated Category line with product-grounded label."""
    text = master_path.read_text(encoding="utf-8")
    label = (category or "").strip()
    if not label:
        return
    if re.search(r"^\*\*Category:\*\*", text, flags=re.MULTILINE):
        text = re.sub(
            r"^\*\*Category:\*\*.*$",
            f"**Category:** {label}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        text = text.replace("# Design System MASTER", f"# Design System MASTER\n\n**Category:** {label}", 1)
    master_path.write_text(text, encoding="utf-8")


def run_skill_design(
    *,
    cfg: BatchConfig,
    workspace: Path,
    row: CsvTaskRow,
    pack_type: str,
) -> Path:
    """Generate uupm candidates, MASTER (provisional), and stack guidelines.
    
    Applies the 4-step fallback ladder to avoid registry saturation issues.
    """
    ctx_path = workspace / "skill-input" / "context.json"
    anti_path = workspace / "skill-input" / "anti-collision-context.json"
    if not ctx_path.is_file() or not anti_path.is_file():
        raise RuntimeError("skill.design 缺少 skill-input/ — 请先运行 prepare.context")

    ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
    anti = json.loads(anti_path.read_text(encoding="utf-8"))
    query = design_query_from_context(ctx, anti, row=row)
    stack = stack_for_pack_type(pack_type)
    base_dials = designer_dials_from_row(row)

    scripts_dir = resolve_uupm_scripts_dir(cfg)
    inject_uupm_scripts(cfg)
    from design_system import DesignSystemGenerator, persist_design_system  # type: ignore[import-not-found]
    from core import search_stack  # type: ignore[import-not-found]

    generator = DesignSystemGenerator()
    candidates_out: list[dict[str, Any]] = []

    for cid, dials in _dial_variants(base_dials):
        ds = generator.generate(
            query,
            row.name,
            variance=dials["variance"],
            motion=dials["motion"],
            density=dials["density"],
        )
        ds["id"] = cid
        candidates_out.append(ds)

    candidates_out = diversify_candidates(candidates_out, query=query)

    # ── Fallback Ladder ──────────────────────────────────────────────
    registry_path = cfg.contentpack_registry
    styles_csv_path = scripts_dir.parent / "data" / "styles.csv"

    def generator_fn(q, proj, variance, motion, density):
        return generator.generate(q, proj, variance=variance, motion=motion, density=density)

    selected_candidate, sim_result = run_fallback_ladder(
        candidates=candidates_out,
        registry_path=registry_path,
        base_query=query,
        base_dials=base_dials,
        styles_csv_path=styles_csv_path,
        generator_fn=generator_fn,
    )

    # Log similarity check results
    for log_msg in sim_result.log:
        print(f"[SIMILARITY] {log_msg}")

    if sim_result.status == "FAIL":
        registry_pkgs = load_registry_packages(registry_path)
        registry_entries = [extract_candidate_registry_entry(p) for p in registry_pkgs]
        anti_styles = anti_style_search(registry_entries, styles_csv_path, max_results=3)
        if anti_styles:
            print(
                f"[SIMILARITY] Falling back to anti-styles: "
                f"{[s.get('Style Category', '') for s in anti_styles]}"
            )
            for anti_style in anti_styles:
                style_name = str(anti_style.get("Style Category", "")).strip()
                keywords = str(anti_style.get("Keywords", "")).strip()
                if not style_name:
                    continue
                anti_query = f"{query} {style_name} {keywords} differentiated visual style"
                print(f"[SIMILARITY] Trying style override query: {anti_query[:120]}...")
                regenerated: list[dict[str, Any]] = []
                for cid, dials in _dial_variants(base_dials):
                    ds = generator.generate(
                        anti_query,
                        row.name,
                        variance=dials["variance"],
                        motion=dials["motion"],
                        density=dials["density"],
                    )
                    ds["id"] = cid
                    regenerated.append(ds)
                retry = run_fallback_ladder(
                    candidates=regenerated,
                    registry_path=registry_path,
                    base_query=anti_query,
                    base_dials=base_dials,
                    styles_csv_path=styles_csv_path,
                    generator_fn=generator_fn,
                )
                if retry.selected_candidate and retry.status in ("PASS", "WARN"):
                    selected_candidate = retry.selected_candidate
                    sim_result = retry
                    candidates_out = regenerated
                    break

        # If still failing, fall back to best available
        if selected_candidate is None:
            print("[SIMILARITY] WARNING: All fallback strategies failed. Using best available candidate.")
            selected_candidate = candidates_out[0]
            sim_result.status = "WARN"
            sim_result.similarity_score = candidate_similarity(selected_candidate, [])
    elif selected_candidate is None:
        # Retry succeeded but didn't return candidate yet
        selected_candidate = candidates_out[0]
        sim_result.status = "WARN"

    # ── Persist selected candidate ───────────────────────────────────
    ds_dir = design_system_dir_for_app(workspace, row.name)
    ds_dir.mkdir(parents=True, exist_ok=True)
    (ds_dir / CANDIDATES_FILENAME).write_text(
        json.dumps({"candidates": candidates_out}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    primary = _prefer_non_saas_candidate(selected_candidate, candidates_out)
    if is_banned_saas_design(primary):
        print(
            "[DESIGN] WARNING: selected candidate still looks SaaS-branded; "
            "persisting anyway — Agent must repair per H5壳ui-ux-pro-max使用规范.md"
        )
    persist_design_system(primary, None, str(workspace), query)

    # Prefer mobile-oriented stack guidelines for H5 (still html-tailwind / vue).
    stack_query = (
        f"{query} touch 44px mobile-first safe-area"
        if stack == "html-tailwind"
        else query
    )
    stack_result = search_stack(stack_query, stack, 8)
    stack_results = stack_result.get("results") or []
    stack_path = stack_guidelines_path(workspace, row.name, stack)
    stack_path.parent.mkdir(parents=True, exist_ok=True)
    stack_path.write_text(_format_stack_md(stack, stack_query, stack_results), encoding="utf-8")

    native_stack = native_stack_for_pack_type(pack_type)
    if native_stack and native_stack != stack:
        native_result = search_stack(query, native_stack, 6)
        native_results = native_result.get("results") or []
        native_path = stack_guidelines_path(workspace, row.name, native_stack)
        native_path.write_text(
            _format_stack_md(native_stack, query, native_results),
            encoding="utf-8",
        )

    if is_h5_shell(pack_type):
        # Architecture stack from skill (vue.csv) — no Tailwind→hand-CSS translation.
        vue_stack = h5_architecture_stack()
        if vue_stack != stack:
            vue_result = search_stack(query, vue_stack, 8)
            vue_path = stack_guidelines_path(workspace, row.name, vue_stack)
            vue_path.write_text(
                _format_stack_md(vue_stack, query, vue_result.get("results") or []),
                encoding="utf-8",
            )
        from batch.skill_stack_brief import write_h5_runtime_brief

        write_h5_runtime_brief(workspace, row.name)

    meta = {
        "source": "ui-ux-pro-max-skill",
        "app": row.name,
        "packType": pack_type,
        "stack": stack,
        "query": query,
        "dialsBase": base_dials,
        "candidateCount": len(candidates_out),
    }
    (ds_dir / META_FILENAME).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    master = master_path_for_app(workspace, row.name)
    if not master.is_file():
        raise RuntimeError(f"skill.design 未生成 MASTER.md: {master}")

    from batch.skill_product_bind import load_product_bind, master_category_label

    bind = {
        "app": {"name": row.name},
        "product": {
            "audience": row.audience or "",
            "coreScene": row.core_scene or "",
            "localFeature": row.local_feature or "",
            "themeCn": row.theme_cn or "",
        },
    }
    ctx_path = workspace / "skill-input" / "context.json"
    if ctx_path.is_file():
        try:
            bind = json.loads(ctx_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    _patch_master_category(master, master_category_label(bind))

    pointer = workspace / POINTER_FILENAME
    rel = master.relative_to(workspace)
    slug = row.name.lower().replace(" ", "-")
    pages_glob = f"design-system/{slug}/pages/*.md"
    pointer.write_text(
        "\n".join(
            [
                "# 设计系统建议",
                "",
                "由流水线 `skill.design` + `skill.enrich` + `skill.adapt` + `skill.pages` 调用 **ui-ux-pro-max** 生成。",
                "",
                f"- MASTER: `{rel.as_posix()}`",
                f"- Style stack: `design-system/{slug}/stack-html-tailwind.md`",
                f"- Architecture stack: `design-system/{slug}/stack-vue.md`",
                f"- H5 runtime (deploy only): `design-system/{slug}/h5-runtime.md`",
                f"- Enrich: `design-system/{slug}/ux-checklist.md` · `icon-brief.md` · `typography-brief.md`",
                f"- Pages: `{pages_glob}`",
                f"- Candidates: `design-system/{slug}/candidates.json`",
                f"- Adapt: `skill-adapt/design-brief.md` · `design-tokens.css` · `icon-manifest.json`",
                "",
                "Cursor skills: `.cursor/skills/ui-ux-pro-max` — H5 统一用 skill 栈（Vue + Tailwind + Google Fonts + Phosphor）。",
                "",
                "Agent Plan 读 skill-adapt/design-brief.md + MASTER + pages；Implementer 读 stack-vue + stack-html-tailwind + icon-brief。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return master


def run_skill_adapt_step(*, workspace: Path, row: CsvTaskRow) -> Path:
    """Write skill-adapt/ from skill.design MASTER — no second visual pick / re-persist."""
    from batch.skill_adapt import candidate_aligned_to_master, write_skill_adapt_outputs

    ds_dir = design_system_dir_for_app(workspace, row.name)
    cand_path = ds_dir / CANDIDATES_FILENAME
    ctx_path = workspace / "skill-input" / "context.json"
    if not cand_path.is_file():
        raise RuntimeError("skill.adapt 缺少 candidates.json — 请先运行 skill.design")

    master = master_path_for_app(workspace, row.name)
    if not master.is_file():
        raise RuntimeError("skill.adapt 缺少 MASTER.md — 请先运行 skill.design")

    data = json.loads(cand_path.read_text(encoding="utf-8"))
    candidates = data.get("candidates") or []
    ctx = json.loads(ctx_path.read_text(encoding="utf-8")) if ctx_path.is_file() else {}
    seeds = (ctx.get("designerSeeds") or {}) if isinstance(ctx, dict) else {}

    from batch.config import BatchConfig

    cfg = BatchConfig.from_env()

    # Visual truth = MASTER factory. Do NOT re-pick (was overwriting brief/token with a
    # different candidate while persist_design_system skipped existing MASTER).
    master_text = master.read_text(encoding="utf-8", errors="ignore")
    selected, rationale = candidate_aligned_to_master(candidates, master_text)

    from batch.skill_product_bind import load_product_bind, master_category_label

    bind = load_product_bind(workspace)
    _patch_master_category(master, master_category_label(bind))

    from batch.skill_context import update_context_designer_seeds
    from batch.skill_adapt import designer_selections_from_candidate

    designer = designer_selections_from_candidate(
        selected, seeds, product_bind=bind, project_dir=cfg.project_dir
    )
    update_context_designer_seeds(workspace, designer)

    try:
        register_design_selection(
            design_ledger_path(cfg.project_dir),
            app=row.name,
            batch_id=str((ctx.get("constraints") or {}).get("batchId") or cfg.batch_id or ""),
            candidate=selected,
            workspace=workspace,
        )
    except Exception:
        pass

    stack_path = None
    meta_path = ds_dir / META_FILENAME
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        stack = meta.get("stack") or "flutter"
        stack_path = stack_guidelines_path(workspace, row.name, str(stack))

    return write_skill_adapt_outputs(
        workspace,
        candidate=selected,
        seeds=seeds,
        selection_rationale=rationale,
        master_path=master,
        stack_path=stack_path,
        project_dir=cfg.project_dir,
    )


# Legacy aliases used by tests / gates
generate_and_persist_design_system = run_skill_design
