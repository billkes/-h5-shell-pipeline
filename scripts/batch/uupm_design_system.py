"""ui-ux-pro-max client — skill.design step (candidates, MASTER, stack, pages)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from batch.skill_context import avoid_query_suffix, stack_for_pack_type
from batch.candidate_similarity import (
    run_fallback_ladder,
    candidate_similarity,
    anti_style_search,
    SimilarityResult,
    THRESHOLD_WARN,
    THRESHOLD_FAIL,
    MAX_RETRIES,
)

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
    for root in _uupm_skill_repo_candidates(cfg):
        scripts = _scripts_dir_from_root(root)
        if scripts is not None:
            return scripts

    raise RuntimeError(
        "找不到 ui-ux-pro-max-skill：请设置 config.yaml → uupm.skill_dir "
        "或环境变量 UUPM_SKILL_DIR（指向 ui-ux-pro-max-skill 仓库根目录）"
    )


def resolve_uupm_package_dir(cfg: BatchConfig) -> Path:
    """Locate ui-ux-pro-max package root (contains ``scripts/`` + ``data/``)."""
    scripts = resolve_uupm_scripts_dir(cfg)
    if scripts.name == "scripts" and scripts.parent.is_dir():
        return scripts.parent
    return scripts


def resolve_uupm_skill_repo_root(cfg: BatchConfig) -> Path | None:
    """Best-effort skill git repo root (for bundled SKILL.md)."""
    pkg = resolve_uupm_package_dir(cfg)
    if pkg.name == "ui-ux-pro-max" and pkg.parent.name == "src":
        return pkg.parent.parent
    for root in _uupm_skill_repo_candidates(cfg):
        if _scripts_dir_from_root(root) is not None:
            return root
    return None


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


def design_query_from_context(ctx: dict[str, Any], anti: dict[str, Any]) -> str:
    app = ctx.get("app") or {}
    product = ctx.get("product") or {}
    parts = [
        app.get("name"),
        app.get("description"),
        product.get("themeAngle"),
        product.get("mainFeature"),
    ]
    base = " ".join(str(p).strip() for p in parts if p and str(p).strip())
    return base + avoid_query_suffix(anti)


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
    query = design_query_from_context(ctx, anti)
    # Extract base query (without avoid suffix) for fallback ladder
    base_query = query.replace(avoid_query_suffix(anti), "").strip()
    stack = stack_for_pack_type(pack_type)
    base_dials = designer_dials_from_row(row)

    scripts_dir = resolve_uupm_scripts_dir(cfg)
    _inject_scripts(scripts_dir)
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

    # ── Fallback Ladder ──────────────────────────────────────────────
    registry_path = cfg.contentpack_registry
    styles_csv_path = scripts_dir.parent / "data" / "styles.csv"

    def generator_fn(q, proj, variance, motion, density):
        return generator.generate(q, proj, variance=variance, motion=motion, density=density)

    selected_candidate, sim_result = run_fallback_ladder(
        candidates=candidates_out,
        registry_path=registry_path,
        base_query=base_query,
        base_dials=base_dials,
        styles_csv_path=styles_csv_path,
        generator_fn=generator_fn,
    )

    # Log similarity check results
    for log_msg in sim_result.log:
        print(f"[SIMILARITY] {log_msg}")

    if sim_result.status == "FAIL":
        # Anti-style search result — try to force a different style
        anti_styles = anti_style_search(
            [candidate_similarity.__globals__.get("registry_entries", [])],
            styles_csv_path,
            max_results=3,
        )
        if anti_styles:
            print(f"[SIMILARITY] Falling back to anti-styles: {[s.get('Style Category', '') for s in anti_styles]}")
            # Regenerate with anti-style priority
            for anti_style in anti_styles:
                style_name = anti_style.get("Style Category", "")
                if style_name:
                    print(f"[SIMILARITY] Trying style override: {style_name}")
                    # TODO: Implement style_priority injection into generator.generate()
                    # For now, use the first candidate as-is with a warning
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

    primary = selected_candidate or candidates_out[0]
    persist_design_system(primary, None, str(workspace), query)

    stack_result = search_stack(query, stack, 8)
    stack_results = stack_result.get("results") or []
    stack_path = stack_guidelines_path(workspace, row.name, stack)
    stack_path.parent.mkdir(parents=True, exist_ok=True)
    stack_path.write_text(_format_stack_md(stack, query, stack_results), encoding="utf-8")

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

    pointer = workspace / POINTER_FILENAME
    rel = master.relative_to(workspace)
    slug = row.name.lower().replace(" ", "-")
    pointer.write_text(
        "\n".join(
            [
                "# 设计系统建议",
                "",
                "由流水线 `skill.design` + `skill.adapt` 调用 **ui-ux-pro-max** 生成。",
                "",
                f"- MASTER: `{rel.as_posix()}`",
                f"- Stack: `design-system/{slug}/stack-{stack}.md`",
                f"- Candidates: `design-system/{slug}/candidates.json`",
                f"- Adapt brief: `skill-adapt/design-brief.md`",
                "",
                "Agent Plan 读 skill-adapt/design-brief.md + MASTER；Programmer 读 stack。",
                "页面级 override（design-system/pages/）不再预生成，由 build.agent 按功能文档定义。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return master


def run_skill_adapt_step(*, workspace: Path, row: CsvTaskRow) -> Path:
    """Pick candidate + write skill-adapt/ artifacts; re-persist selected MASTER."""
    from batch.skill_adapt import pick_candidate, write_skill_adapt_outputs

    ds_dir = design_system_dir_for_app(workspace, row.name)
    cand_path = ds_dir / CANDIDATES_FILENAME
    anti_path = workspace / "skill-input" / "anti-collision-context.json"
    ctx_path = workspace / "skill-input" / "context.json"
    if not cand_path.is_file():
        raise RuntimeError("skill.adapt 缺少 candidates.json — 请先运行 skill.design")
    if not anti_path.is_file():
        raise RuntimeError("skill.adapt 缺少 anti-collision-context.json")

    data = json.loads(cand_path.read_text(encoding="utf-8"))
    candidates = data.get("candidates") or []
    anti = json.loads(anti_path.read_text(encoding="utf-8"))
    ctx = json.loads(ctx_path.read_text(encoding="utf-8")) if ctx_path.is_file() else {}
    seeds = (ctx.get("designerSeeds") or {}) if isinstance(ctx, dict) else {}

    selected, rationale = pick_candidate(candidates, anti)

    scripts_dir = None
    try:
        from batch.config import BatchConfig

        cfg = BatchConfig.from_env()
        scripts_dir = resolve_uupm_scripts_dir(cfg)
        _inject_scripts(scripts_dir)
        from design_system import persist_design_system  # type: ignore[import-not-found]

        persist_design_system(selected, None, str(workspace), design_query_from_context(ctx, anti))
    except Exception:
        pass

    stack_path = None
    meta_path = ds_dir / META_FILENAME
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        stack = meta.get("stack") or "flutter"
        stack_path = stack_guidelines_path(workspace, row.name, str(stack))

    master = master_path_for_app(workspace, row.name)
    return write_skill_adapt_outputs(
        workspace,
        candidate=selected,
        seeds=seeds,
        selection_rationale=rationale,
        master_path=master,
        stack_path=stack_path,
    )


# Legacy aliases used by tests / gates
generate_and_persist_design_system = run_skill_design
