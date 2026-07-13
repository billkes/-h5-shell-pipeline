"""Pick available themes → generate 10-name pools → write task.csv rows."""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path
from typing import Any

from batch.config import BatchConfig
from batch.csv_tasks import load_task_csv_raw, write_task_csv_rows
from batch.feishu_config import load_feishu_config
from batch.feishu_theme_sync import fetch_available_theme_index
from batch.name_generator import generate_candidates, generate_candidates_batch
from batch.name_pool import (
    load_pools,
    new_pool,
    save_pools,
    sidecar_path,
)
from batch.name_rules import (
    Denylist,
    NameCandidate,
    a_face_batch_limit,
    a_face_counts_from_full_names,
    build_denylist,
    pick_diverse_candidate_index,
    subtitle_a_face,
)
from batch.prod_a_registry import load_prod_a_registry, subtitle_pair_from_full
from batch.task_schema import (
    COL_AUDIENCE,
    COL_CORE_SCENE,
    COL_FIRST_PRODUCT_CODE,
    COL_FULL_NAME,
    COL_GIT_URL,
    COL_LOCAL_FEATURE,
    COL_NAME,
    COL_PACK_TYPE,
    COL_PRODUCT_FLOW,
    COL_THEME_CN,
    COL_THEME_CODE,
    COL_TRACK,
    STANDARD_COLUMNS,
)


def _theme_columns(theme: dict[str, str]) -> dict[str, str]:
    return {
        COL_THEME_CODE: theme.get("theme_code", ""),
        COL_THEME_CN: theme.get("theme_cn", ""),
        COL_TRACK: theme.get("track", ""),
        COL_AUDIENCE: theme.get("audience", ""),
        COL_CORE_SCENE: theme.get("core_scene", ""),
        COL_LOCAL_FEATURE: theme.get("local_feature", ""),
        COL_PACK_TYPE: theme.get("pack_type", "tool_flutter"),
    }


def _batch_deny_sets(rows: list[dict[str, str]]) -> tuple[frozenset[str], frozenset[str], frozenset[str], frozenset[tuple[str, str]]]:
    names: set[str] = set()
    fulls: set[str] = set()
    codes: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for row in rows:
        n = (row.get(COL_NAME) or "").strip()
        if n:
            names.add(n)
        f = (row.get(COL_FULL_NAME) or "").strip()
        if f:
            fulls.add(f)
            pair = subtitle_pair_from_full(f)
            if pair:
                pairs.add(pair)
        c = (row.get(COL_FIRST_PRODUCT_CODE) or "").strip()
        if c:
            codes.add(c)
    return frozenset(names), frozenset(fulls), frozenset(codes), frozenset(pairs)


def _batch_a_face_state(rows: list[dict[str, str]]) -> tuple[Counter[str], int]:
    fulls = [(r.get(COL_FULL_NAME) or "").strip() for r in rows if (r.get(COL_FULL_NAME) or "").strip()]
    return a_face_counts_from_full_names(fulls), a_face_batch_limit(len(rows))


def _sync_git_url_on_rename(row: dict[str, str], old_name: str, new_name: str) -> None:
    """Keep 仓库地址 aligned when 应用主名称 changes after rename-row."""
    url = (row.get(COL_GIT_URL) or "").strip()
    if not url or not old_name or not new_name or old_name == new_name:
        return
    if old_name in url:
        row[COL_GIT_URL] = url.replace(old_name, new_name, 1)


def _deny_for_pick(
    registry: Any,
    rows: list[dict[str, str]],
    *,
    exclude_theme_code: str = "",
) -> Denylist:
    names: set[str] = set()
    fulls: set[str] = set()
    codes: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for row in rows:
        if exclude_theme_code and (row.get(COL_THEME_CODE) or "").strip() == exclude_theme_code:
            continue
        n = (row.get(COL_NAME) or "").strip()
        if n:
            names.add(n)
        f = (row.get(COL_FULL_NAME) or "").strip()
        if f:
            fulls.add(f)
            pair = subtitle_pair_from_full(f)
            if pair:
                pairs.add(pair)
        c = (row.get(COL_FIRST_PRODUCT_CODE) or "").strip()
        if c:
            codes.add(c)
    return build_denylist(
        registry,
        batch_app_names=frozenset(names),
        batch_full_names=frozenset(fulls),
        batch_codes=frozenset(codes),
        batch_subtitle_pairs=frozenset(pairs),
    )


def _row_from_candidate(
    cand: NameCandidate,
    theme: dict[str, str],
    *,
    product_flow: str,
) -> dict[str, str]:
    row = {c: "" for c in STANDARD_COLUMNS}
    row[COL_NAME] = cand.name
    row[COL_FULL_NAME] = cand.full_name
    row[COL_FIRST_PRODUCT_CODE] = cand.product_code
    row[COL_PRODUCT_FLOW] = product_flow
    row[COL_GIT_URL] = ""
    row.update(_theme_columns(theme))
    return row


def pick_themes_to_csv(
    csv_path: Path,
    theme_codes: list[str],
    *,
    cfg: BatchConfig,
    feishu_config: Path | None = None,
    force: bool = False,
    use_agent: bool | None = None,
) -> list[str]:
    """Append one task.csv row per theme_code; return app names written."""
    config = load_feishu_config(feishu_config)
    available = fetch_available_theme_index(config)
    meta, rows, fieldnames = load_task_csv_raw(csv_path)
    pools = load_pools(csv_path)
    batch_names, batch_fulls, batch_codes, _ = _batch_deny_sets(rows)

    existing_codes = {
        (r.get(COL_THEME_CODE) or "").strip()
        for r in rows
        if (r.get(COL_THEME_CODE) or "").strip()
    }

    written: list[str] = []
    pending: list[tuple[str, dict[str, str]]] = []

    for code in theme_codes:
        code = code.strip()
        if not code:
            continue
        if code in existing_codes and not force:
            raise ValueError(f"task.csv 已有主题编号 {code}，使用 --force 覆盖")
        theme = available.get(code)
        if not theme:
            raise ValueError(
                f"主题 {code} 不在可用池（使用人+使用状态须均为空）"
            )
        theme_with_code = dict(theme)
        theme_with_code["theme_code"] = code
        pending.append((code, theme_with_code))

    if not pending:
        return written

    registry = load_prod_a_registry(cfg.project_dir)
    use_batch_agent = (
        use_agent is not False
        and len(pending) > 1
        and os.environ.get("CIB_DETERMINISTIC_NAMES", "").lower()
        not in ("1", "true", "yes")
    )

    if use_batch_agent:
        generated = generate_candidates_batch(
            pending,
            cfg=cfg,
            batch_names=batch_names,
            batch_full_names=batch_fulls,
            batch_codes=batch_codes,
            use_agent=use_agent,
            registry=registry,
        )
    else:
        generated = {}
        batch_n = len(rows) + len(pending)
        a_limit = a_face_batch_limit(batch_n)
        a_counts = a_face_counts_from_full_names(
            [(r.get(COL_FULL_NAME) or "").strip() for r in rows]
        )
        for code, theme_with_code in pending:
            generated[code] = generate_candidates(
                code,
                theme_with_code,
                cfg=cfg,
                batch_names=batch_names,
                batch_full_names=batch_fulls,
                batch_codes=batch_codes,
                use_agent=use_agent,
                registry=registry,
            )
            candidates, _ = generated[code]
            deny = _deny_for_pick(registry, rows)
            idx = pick_diverse_candidate_index(
                candidates, deny, a_counts, limit=a_limit, start=0
            )
            cand = candidates[idx]
            batch_names = frozenset(batch_names | {cand.name})
            batch_fulls = frozenset(batch_fulls | {cand.full_name})
            batch_codes = frozenset(batch_codes | {cand.product_code})
            a_word = subtitle_a_face(cand.full_name)
            if a_word:
                a_counts[a_word] += 1

    batch_size = len(rows) + len(pending)
    a_limit = a_face_batch_limit(batch_size)
    a_counts = a_face_counts_from_full_names(
        [(r.get(COL_FULL_NAME) or "").strip() for r in rows]
    )

    for code, theme_with_code in pending:
        theme = available.get(code) or theme_with_code
        candidates, product_flow = generated[code]
        pool = new_pool(
            code,
            context={
                "theme_cn": theme.get("theme_cn", ""),
                "track": theme.get("track", ""),
                "audience": theme.get("audience", ""),
                "core_scene": theme.get("core_scene", ""),
                "local_feature": theme.get("local_feature", ""),
            },
            candidates=candidates,
            product_flow=product_flow,
        )
        pools[code] = pool
        deny = _deny_for_pick(registry, rows)
        cand = pool.select_diverse(deny, a_counts, limit=a_limit, start=0)
        new_row = _row_from_candidate(cand, theme_with_code, product_flow=product_flow)

        if force and code in existing_codes:
            rows = [
                new_row if (r.get(COL_THEME_CODE) or "").strip() == code else r
                for r in rows
            ]
        else:
            rows.append(new_row)

        a_word = subtitle_a_face(cand.full_name)
        if a_word:
            a_counts[a_word] += 1
        batch_names = frozenset(batch_names | {cand.name})
        batch_fulls = frozenset(batch_fulls | {cand.full_name})
        batch_codes = frozenset(batch_codes | {cand.product_code})
        existing_codes.add(code)
        written.append(cand.name)

    write_task_csv_rows(csv_path, meta, rows, fieldnames)
    save_pools(csv_path, pools)
    return written


def rename_row_in_csv(
    csv_path: Path,
    *,
    row_number: int | None = None,
    app_name: str | None = None,
) -> NameCandidate:
    """Advance name pool cursor; update 应用主名称/全称/首个商品Code only."""
    meta, rows, fieldnames = load_task_csv_raw(csv_path)
    if row_number is not None:
        if not 1 <= row_number <= len(rows):
            raise ValueError(f"行号 {row_number} 超出范围（1-{len(rows)}）")
        idx = row_number - 1
    else:
        idx = None
        key = (app_name or "").strip()
        for i, row in enumerate(rows):
            if (row.get(COL_NAME) or "").strip() == key:
                idx = i
                break
        if idx is None:
            raise ValueError(f"未找到应用: {app_name!r}")

    row = rows[idx]
    theme_code = (row.get(COL_THEME_CODE) or "").strip()
    if not theme_code:
        raise ValueError(f"第 {idx + 1} 行缺少主题编号，无法换名")

    pools = load_pools(csv_path)
    pool = pools.get(theme_code)
    if pool is None:
        raise ValueError(
            f"未找到主题 {theme_code} 的候选池（先运行 task pick-theme）"
        )

    registry = load_prod_a_registry(Path(csv_path).resolve().parent)
    batch_size = len(rows)
    a_limit = a_face_batch_limit(batch_size)
    a_counts, _ = _batch_a_face_state(rows)
    old_a = subtitle_a_face((row.get(COL_FULL_NAME) or "").strip())
    if old_a and a_counts.get(old_a, 0) > 0:
        a_counts[old_a] -= 1
    deny = _deny_for_pick(registry, rows, exclude_theme_code=theme_code)
    cand = pool.select_diverse(
        deny,
        a_counts,
        limit=a_limit,
        start=pool.cursor + 1,
    )
    old_name = (row.get(COL_NAME) or "").strip()
    row[COL_NAME] = cand.name
    row[COL_FULL_NAME] = cand.full_name
    row[COL_FIRST_PRODUCT_CODE] = cand.product_code
    _sync_git_url_on_rename(row, old_name, cand.name)

    write_task_csv_rows(csv_path, meta, rows, fieldnames)
    save_pools(csv_path, pools)
    return cand


def format_pick_report(
    names: list[str],
    *,
    csv_path: Path,
    theme_codes: list[str],
) -> str:
    lines = [
        f">>> pick-theme 完成: {len(names)} 行 → {csv_path}",
        f"    sidecar: {sidecar_path(csv_path)}",
    ]
    for code, name in zip(theme_codes, names):
        lines.append(f"    {code} → {name}（A 面词去重后首选，仓库地址留空）")
    lines.append("    审核拒绝: python3 -m batch task rename-row --row N")
    return "\n".join(lines)
