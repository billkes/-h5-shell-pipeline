"""Generate 10 name candidates per theme (Agent or deterministic fallback)."""

from __future__ import annotations

import json
import os
import random
import re
from pathlib import Path
from typing import Any

from batch.config import BatchConfig
from batch.cursor_runner import run_agent
from batch.name_rules import (
    Denylist,
    NameCandidate,
    SUBTITLE_A_FACE_WORDS,
    a_face_batch_limit,
    a_face_counts_from_full_names,
    build_denylist,
    pick_diverse_candidate_index,
    subtitle_a_face,
    validate_candidate,
)
from batch.name_pool import POOL_SIZE
from batch.prod_a_registry import load_prod_a_registry, subtitle_pair_from_full

_A_FACE = SUBTITLE_A_FACE_WORDS
_B_FACE = ("Hold", "Drift", "Bloom", "Span", "Flow", "Echo", "Lane", "Pair", "Form", "Hue")
_MAIN_SUFFIXES = ("ioo", "oyy", "aoo", "eoo", "uoo", "ioy", "aoy", "eoy", "ooi", "oyi")
_MAIN_PREFIXES = ("Y", "L", "R", "T", "M", "N", "P", "S", "V", "W")


def _theme_seed(theme_code: str) -> random.Random:
    seed = sum(ord(c) for c in theme_code) + 20260702
    return random.Random(seed)


def _code_from_theme(theme: dict[str, str], rng: random.Random, index: int) -> str:
    local = (theme.get("local_feature") or theme.get("track") or "Pack")[:5]
    word = "".join(ch for ch in local if ch.isalpha()) or "Pack"
    word = word[:1].upper() + word[1:4].lower()
    if len(word) < 4:
        word = (word + "Pack")[:4]
    if index % 2 == 0:
        return f"{word}00"
    return f"00{word}"


def _product_flow_from_theme(
    theme: dict[str, str],
    *,
    topology_id: str = "",
    project_dir: Path | None = None,
) -> str:
    from batch.interaction_topology import generate_product_flow_for_topology

    audience = theme.get("audience") or "users"
    scene = theme.get("core_scene") or "daily tasks"
    feature = theme.get("local_feature") or "journal"
    return generate_product_flow_for_topology(
        audience=audience,
        scene=scene,
        feature=feature,
        topology_id=topology_id or "T6_checklist_session",
        project_dir=project_dir,
    )


def deterministic_candidates(
    theme: dict[str, str],
    *,
    theme_code: str,
    deny: Denylist,
) -> tuple[list[NameCandidate], str]:
    """Rule-based fallback for tests / offline."""
    product_flow = _product_flow_from_theme(theme)
    rng = _theme_seed(theme_code)
    templates: list[tuple[str, str, str, str]] = [
        ("Yogioo", "Calm", "Hold", "Yogi00"),
        ("Loomio", "Soft", "Span", "Loom00"),
        ("Rilooi", "Glow", "Flow", "Rilo00"),
        ("Treioo", "Pure", "Echo", "Trei00"),
        ("Moiioo", "Warm", "Lane", "Moii00"),
        ("Noiooy", "Neat", "Pair", "Noio00"),
        ("Paiioo", "Crisp", "Form", "Paii00"),
        ("Sooioy", "Mellow", "Hue", "Sooi00"),
        ("Voiioo", "Bright", "Drift", "Voii00"),
        ("Woiioo", "Fine", "Bloom", "Woii00"),
    ]
    rng.shuffle(templates)
    out: list[NameCandidate] = []
    for main, a_word, b_word, code in templates:
        if len(out) >= POOL_SIZE:
            break
        full = f"{main} - {a_word} & {b_word}"
        cand = NameCandidate(name=main, full_name=full, product_code=code)
        issues = validate_candidate(cand, deny)
        if issues:
            continue
        if any(c.name == cand.name for c in out):
            continue
        out.append(cand)
    if len(out) < POOL_SIZE:
        raise RuntimeError(f"确定性生成未能产出 {POOL_SIZE} 个合法候选")
    return out[:POOL_SIZE], product_flow


def build_agent_prompt(
    *,
    theme_code: str,
    theme: dict[str, str],
    deny: Denylist,
    output_path: Path,
    project_dir: Path,
) -> str:
    template_path = project_dir / "prompts" / "prep" / "name_candidates.txt"
    if template_path.is_file():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = _DEFAULT_PROMPT
    blacklist_sample = sorted(deny.app_names)[:40]
    return template.format(
        theme_code=theme_code,
        theme_cn=theme.get("theme_cn", ""),
        track=theme.get("track", ""),
        audience=theme.get("audience", ""),
        core_scene=theme.get("core_scene", ""),
        local_feature=theme.get("local_feature", ""),
        pack_type=theme.get("pack_type", "tool_flutter"),
        blacklist_apps=", ".join(blacklist_sample),
        blacklist_count=len(deny.app_names),
        output_path=output_path,
        pool_size=POOL_SIZE,
    )


_DEFAULT_PROMPT = """你是 iOS 马甲包 ASO 命名专家。基于主题上下文生成 {pool_size} 组候选。

主题编号: {theme_code}
中文主题: {theme_cn}
赛道: {track}
目标人群: {audience}
核心场景: {core_scene}
本地功能: {local_feature}

规则（必须遵守）:
1. 应用主名称 = 6 个字母的人造词，2-3 音节，含 oo/yy/uu/ii 或 oio/ioi/goi/joi/roi 圆润音韵，禁止真实英语单词
2. 全称格式: `Main - Word1 & Word2`（Word1 抽象情绪词，Word2 双关动作词；禁 Dating/Matchmaker/Flirt/Meet/Hot）
3. 首个商品Code: 真实英文主题词首字母大写 + 00，须从以下格式之一选取（主题词 4–7 位字母，禁止 3 位及以下）:
   - 00 + 4/5/6 位主题单词（如 00Cast、00Draft）
   - 4/5/6/7 位主题单词 + 00（如 Glam00、Mockup00）
4. 产A 总库已有 {blacklist_count} 个应用主名称，禁止重复主名/全称/副标题组合/商品Code（样例: {blacklist_apps}）
5. 同一 JSON 内 10 组互不重复
6. 10 组候选的 Word1（A 面词）须覆盖多种情绪词，禁止 10 组全部以 Calm/Soft/Warm 等同词开头

另外生成一条英文 productFlow（一条字符串，描述 Browse/save/log/export 工具流，与主题场景相关）。

将结果写入 JSON 文件（仅此文件，不要改其它文件）:
{output_path}

格式:
{{
  "product_flow": "...",
  "candidates": [
    {{"name": "...", "full_name": "...", "product_code": "..."}},
    ...
  ]
}}
"""


def _parse_candidates_list(raw_list: Any) -> list[NameCandidate]:
    if not isinstance(raw_list, list):
        raise ValueError("candidates 必须是 array")
    candidates: list[NameCandidate] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        candidates.append(
            NameCandidate(
                name=str(item.get("name") or "").strip(),
                full_name=str(item.get("full_name") or "").strip(),
                product_code=str(item.get("product_code") or "").strip(),
            )
        )
    return candidates


def _parse_agent_output(path: Path) -> tuple[list[NameCandidate], str]:
    if not path.is_file():
        raise FileNotFoundError(f"Agent 未写出候选文件: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    product_flow = str(data.get("product_flow") or "").strip()
    return _parse_candidates_list(data.get("candidates") or []), product_flow


def _parse_batch_agent_output(path: Path) -> dict[str, tuple[list[NameCandidate], str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Agent 未写出批量候选文件: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    themes_raw = data.get("themes")
    if not isinstance(themes_raw, dict):
        raise ValueError("批量 JSON 缺少 themes 对象")
    out: dict[str, tuple[list[NameCandidate], str]] = {}
    for code, block in themes_raw.items():
        if not isinstance(block, dict):
            raise ValueError(f"主题 {code!r} 块无效")
        product_flow = str(block.get("product_flow") or "").strip()
        candidates = _parse_candidates_list(block.get("candidates") or [])
        out[str(code).strip()] = candidates, product_flow
    return out


def _format_themes_block(themes: list[tuple[str, dict[str, str]]]) -> str:
    lines: list[str] = []
    for code, theme in themes:
        lines.append(f"- 编号: {code}")
        lines.append(f"  中文主题: {theme.get('theme_cn', '')}")
        lines.append(f"  赛道: {theme.get('track', '')}")
        lines.append(f"  目标人群: {theme.get('audience', '')}")
        lines.append(f"  核心场景: {theme.get('core_scene', '')}")
        lines.append(f"  本地功能: {theme.get('local_feature', '')}")
        lines.append("")
    return "\n".join(lines).rstrip()


def build_batch_agent_prompt(
    *,
    themes: list[tuple[str, dict[str, str]]],
    deny: Denylist,
    output_path: Path,
    project_dir: Path,
) -> str:
    template_path = project_dir / "prompts" / "prep" / "name_candidates_batch.txt"
    if template_path.is_file():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = _DEFAULT_BATCH_PROMPT
    blacklist_sample = sorted(deny.app_names)[:40]
    example_code = themes[0][0] if themes else "A00001"
    return template.format(
        theme_count=len(themes),
        pool_size=POOL_SIZE,
        blacklist_apps=", ".join(blacklist_sample),
        blacklist_count=len(deny.app_names),
        themes_block=_format_themes_block(themes),
        output_path=output_path,
        example_theme_code=example_code,
    )


_DEFAULT_BATCH_PROMPT = """你是 iOS 马甲包 ASO 命名专家。为 {theme_count} 个主题各生成 {pool_size} 组候选。

产A 总库 {blacklist_count} 条，禁止重复（样例: {blacklist_apps}）。
批次内各主题首选候选之间也不得重复。
系统会从各主题 10 组候选中自动选取 A 面词（Word1）不扎堆的首选；每个主题的 10 组候选 Word1 须多样化，禁止多主题首选全用 Calm/Soft/Warm 等同词。

{themes_block}

写入: {output_path}
格式: {{"themes": {{"{example_theme_code}": {{"product_flow": "...", "candidates": [...]}}}}}}
"""


def _prep_path(cfg: BatchConfig, theme_code: str) -> Path:
    return cfg.project_dir / "output" / "_prep" / f"{theme_code}-names.json"


def _write_prep_file(
    path: Path,
    *,
    product_flow: str,
    candidates: list[NameCandidate],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "product_flow": product_flow,
        "candidates": [
            {
                "name": c.name,
                "full_name": c.full_name,
                "product_code": c.product_code,
            }
            for c in candidates
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _try_load_prep(
    path: Path,
    theme: dict[str, str],
    deny: Denylist,
) -> tuple[list[NameCandidate], str] | None:
    if not path.is_file():
        return None
    try:
        candidates, product_flow = _parse_agent_output(path)
        if not product_flow:
            product_flow = _product_flow_from_theme(theme)
        return _validate_pool(candidates, product_flow, deny)
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _validate_pool(
    candidates: list[NameCandidate],
    product_flow: str,
    deny: Denylist,
) -> tuple[list[NameCandidate], str]:
    if not product_flow:
        raise ValueError("product_flow 不能为空")
    if len(candidates) != POOL_SIZE:
        raise ValueError(f"需要 {POOL_SIZE} 个候选，Agent 返回 {len(candidates)}")
    seen: set[str] = set()
    for cand in candidates:
        if cand.name in seen:
            raise ValueError(f"批内重复主名: {cand.name!r}")
        seen.add(cand.name)
        issues = validate_candidate(cand, deny)
        if issues:
            raise ValueError(f"{cand.name}: " + "; ".join(issues))
    return candidates, product_flow


def generate_candidates(
    theme_code: str,
    theme: dict[str, str],
    *,
    cfg: BatchConfig,
    batch_names: frozenset[str] | None = None,
    batch_full_names: frozenset[str] | None = None,
    batch_codes: frozenset[str] | None = None,
    use_agent: bool | None = None,
    registry: Any | None = None,
) -> tuple[list[NameCandidate], str]:
    reg = registry if registry is not None else load_prod_a_registry(cfg.project_dir)
    deny = build_denylist(
        reg,
        batch_app_names=batch_names,
        batch_full_names=batch_full_names,
        batch_codes=batch_codes,
    )
    if use_agent is None:
        use_agent = os.environ.get("CIB_DETERMINISTIC_NAMES", "").lower() not in (
            "1",
            "true",
            "yes",
        )
    out_path = _prep_path(cfg, theme_code)
    cached = _try_load_prep(out_path, theme, deny)
    if cached is not None:
        return cached

    if not use_agent:
        candidates, product_flow = deterministic_candidates(
            theme, theme_code=theme_code, deny=deny
        )
        _write_prep_file(out_path, product_flow=product_flow, candidates=candidates)
        return candidates, product_flow

    prompt = build_agent_prompt(
        theme_code=theme_code,
        theme=theme,
        deny=deny,
        output_path=out_path,
        project_dir=cfg.project_dir,
    )
    ok = run_agent(cfg, cfg.project_dir, prompt)
    if not ok:
        raise RuntimeError(f"Agent 生成 {theme_code} 候选名失败")
    candidates, product_flow = _parse_agent_output(out_path)
    if not product_flow:
        product_flow = _product_flow_from_theme(theme)
    validated = _validate_pool(candidates, product_flow, deny)
    _write_prep_file(out_path, product_flow=validated[1], candidates=validated[0])
    return validated


def generate_candidates_batch(
    themes: list[tuple[str, dict[str, str]]],
    *,
    cfg: BatchConfig,
    batch_names: frozenset[str] | None = None,
    batch_full_names: frozenset[str] | None = None,
    batch_codes: frozenset[str] | None = None,
    use_agent: bool | None = None,
    registry: Any | None = None,
) -> dict[str, tuple[list[NameCandidate], str]]:
    """Generate name pools for multiple themes in one Agent call when possible."""
    if not themes:
        return {}

    reg = registry if registry is not None else load_prod_a_registry(cfg.project_dir)
    if use_agent is None:
        use_agent = os.environ.get("CIB_DETERMINISTIC_NAMES", "").lower() not in (
            "1",
            "true",
            "yes",
        )

    names = set(batch_names or ())
    fulls = set(batch_full_names or ())
    codes = set(batch_codes or ())
    a_face_counts = a_face_counts_from_full_names(list(fulls))
    results: dict[str, tuple[list[NameCandidate], str]] = {}
    pending: list[tuple[str, dict[str, str]]] = []
    batch_n = len(names) + len(themes)
    a_limit = a_face_batch_limit(batch_n) if batch_n else 1

    for theme_code, theme in themes:
        deny = build_denylist(
            reg,
            batch_app_names=frozenset(names),
            batch_full_names=frozenset(fulls),
            batch_codes=frozenset(codes),
        )
        prep = _prep_path(cfg, theme_code)
        cached = _try_load_prep(prep, theme, deny)
        if cached is not None:
            results[theme_code] = cached
            deny_pick = build_denylist(
                reg,
                batch_app_names=frozenset(names),
                batch_full_names=frozenset(fulls),
                batch_codes=frozenset(codes),
            )
            idx = pick_diverse_candidate_index(
                cached[0], deny_pick, a_face_counts, limit=a_limit, start=0
            )
            active = cached[0][idx]
            names.add(active.name)
            fulls.add(active.full_name)
            codes.add(active.product_code)
            a_word = subtitle_a_face(active.full_name)
            if a_word:
                a_face_counts[a_word] += 1
            continue
        pending.append((theme_code, theme))

    if not pending:
        return results

    if not use_agent:
        for theme_code, theme in pending:
            deny = build_denylist(
                reg,
                batch_app_names=frozenset(names),
                batch_full_names=frozenset(fulls),
                batch_codes=frozenset(codes),
            )
            candidates, product_flow = deterministic_candidates(
                theme, theme_code=theme_code, deny=deny
            )
            prep = _prep_path(cfg, theme_code)
            _write_prep_file(prep, product_flow=product_flow, candidates=candidates)
            results[theme_code] = candidates, product_flow
            idx = pick_diverse_candidate_index(
                candidates, deny, a_face_counts, limit=a_limit, start=0
            )
            active = candidates[idx]
            names.add(active.name)
            fulls.add(active.full_name)
            codes.add(active.product_code)
            a_word = subtitle_a_face(active.full_name)
            if a_word:
                a_face_counts[a_word] += 1
        return results

    out_dir = cfg.project_dir / "output" / "_prep"
    out_dir.mkdir(parents=True, exist_ok=True)
    batch_path = out_dir / "batch-names.json"
    deny = build_denylist(
        reg,
        batch_app_names=frozenset(names),
        batch_full_names=frozenset(fulls),
        batch_codes=frozenset(codes),
    )
    prompt = build_batch_agent_prompt(
        themes=pending,
        deny=deny,
        output_path=batch_path,
        project_dir=cfg.project_dir,
    )
    ok = run_agent(cfg, cfg.project_dir, prompt)
    if not ok:
        raise RuntimeError("Agent 批量生成候选名失败")

    raw = _parse_batch_agent_output(batch_path)
    missing = [code for code, _ in pending if code not in raw]
    if missing:
        raise ValueError(f"批量 JSON 缺少主题: {', '.join(missing)}")

    for theme_code, theme in pending:
        deny = build_denylist(
            reg,
            batch_app_names=frozenset(names),
            batch_full_names=frozenset(fulls),
            batch_codes=frozenset(codes),
        )
        candidates, product_flow = raw[theme_code]
        if not product_flow:
            product_flow = _product_flow_from_theme(theme)
        validated = _validate_pool(candidates, product_flow, deny)
        prep = _prep_path(cfg, theme_code)
        _write_prep_file(prep, product_flow=validated[1], candidates=validated[0])
        results[theme_code] = validated
        idx = pick_diverse_candidate_index(
            validated[0], deny, a_face_counts, limit=a_limit, start=0
        )
        active = validated[0][idx]
        names.add(active.name)
        fulls.add(active.full_name)
        codes.add(active.product_code)
        a_word = subtitle_a_face(active.full_name)
        if a_word:
            a_face_counts[a_word] += 1

    return results


def extract_json_from_text(text: str) -> Any:
    """Best-effort JSON parse for tests."""
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group(0))
    raise ValueError("未找到 JSON")
