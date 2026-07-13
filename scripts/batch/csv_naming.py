"""Apply CSV naming obfuscation rules to workspace code combo JSON."""

from __future__ import annotations

import json
import os
import random
import re
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from batch.csv_tasks import CsvTaskRow, normalize_naming_obfuscation_rule
from batch.naming import build_rule_meta

RULE_DUAL_RANDOM_HEAD = "双随机首段策略"
RULE_CONSONANT_CORE = "辅音核心策略"
RULE_REVERSE_INITIALS = "倒序声母策略"
RULE_VOWEL_BRIDGE = "元音桥接策略"
RULE_BATCH_INITIAL_EMBED = "批次声母嵌入策略"
RULE_MIRROR_RANDOM = "双随机镜像策略"
RULE_SINGLE_INITIAL_TRIPLE = "单声母三随机策略"
RULE_CV_PSEUDOWORD = "元辅伪词策略"
RULE_APPNAME_SPLIT_INSERT = "应用名分段插入策略"
RULE_HASH_DOMAIN = "哈希域伪装策略"

_RULE_KEY_BY_LABEL: dict[str, str] = {
    RULE_DUAL_RANDOM_HEAD: "dual_random_head",
    RULE_CONSONANT_CORE: "consonant_core",
    RULE_REVERSE_INITIALS: "reverse_initials",
    RULE_VOWEL_BRIDGE: "vowel_bridge",
    RULE_BATCH_INITIAL_EMBED: "batch_initial_embed",
    RULE_MIRROR_RANDOM: "mirror_random",
    RULE_SINGLE_INITIAL_TRIPLE: "single_initial_triple",
    RULE_CV_PSEUDOWORD: "cv_pseudoword",
    RULE_APPNAME_SPLIT_INSERT: "appname_split_insert",
    RULE_HASH_DOMAIN: "hash_domain",
}

COOLDOWN_DAYS = int(os.environ.get("COOLDOWN_DAYS", "60"))
_MAX_ATTEMPTS = 400
_PREFIX_RE = re.compile(r"^[a-z]{4,6}$")

_VOWELS = "aeiou"
_CONSONANTS = "bcdfghjklmnpqrstvwxyz"


def _app_letters(name: str, count: int) -> str:
    letters = [c.lower() for c in name if c.isalpha()]
    while len(letters) < count:
        letters.append("x")
    return "".join(letters[:count])


def _consonants(name: str, count: int) -> str:
    found = [c.lower() for c in name if c.isalpha() and c.lower() in _CONSONANTS]
    while len(found) < count:
        found.append("x")
    return "".join(found[:count])


def _rand_vowels(rng: random.Random, n: int) -> str:
    return "".join(rng.choice(_VOWELS) for _ in range(n))


def _rand_consonants(rng: random.Random, n: int) -> str:
    return "".join(rng.choice(_CONSONANTS) for _ in range(n))


def _cv_word(rng: random.Random) -> str:
    return (
        _rand_consonants(rng, 1)
        + _rand_vowels(rng, 1)
        + _rand_consonants(rng, 1)
        + _rand_vowels(rng, 1)
        + _rand_consonants(rng, 1)
    )


def _batch_domain_2(batch_id: str) -> str:
    found = [c.lower() for c in batch_id if c.isalpha()]
    h = abs(hash(batch_id))
    pool = string.ascii_lowercase
    while len(found) < 2:
        found.append(pool[h % 26])
        h //= 26
    return found[0] + found[1]


def _rng(workspace: Path, app_name: str, attempt: int) -> random.Random:
    day = int(datetime.now().strftime("%Y%m%d"))
    seed = hash(str(workspace)) ^ hash(app_name) ^ attempt ^ day
    return random.Random(seed)


def _rand_letters(rng: random.Random, n: int) -> str:
    return "".join(rng.choice(string.ascii_lowercase) for _ in range(n))


def load_recent_dart_prefixes(registry_path: Path) -> set[str]:
    """Load dartCodePrefix values used within COOLDOWN_DAYS."""
    cutoff = (datetime.now() - timedelta(days=COOLDOWN_DAYS)).strftime("%Y-%m-%d")
    recent: set[str] = set()
    if not registry_path.is_file():
        return recent
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return recent
    for pkg in data.get("packages") or []:
        used_at = pkg.get("usedAt") or pkg.get("registeredAt") or ""
        if used_at < cutoff:
            continue
        cc = pkg.get("codeAntiCorrelation") or {}
        dp = cc.get("dartCodePrefix")
        if dp and isinstance(dp, str):
            recent.add(dp.lower().strip())
    return recent


def _valid_prefix(prefix: str, recent: set[str]) -> bool:
    p = prefix.lower().strip()
    if p in recent:
        return False
    return bool(_PREFIX_RE.match(p))


def _meta_v2(
    rule_key: str,
    package_seed: str,
    *,
    batch_id: str = "",
) -> dict[str, Any]:
    """v2 meta: seeds only — affix keys derived at transform time."""
    return build_rule_meta(rule_key, package_seed, batch_id=batch_id)


def _generate_dual_random_head(
    app_name: str,
    workspace: Path,
    attempt: int,
) -> tuple[str, dict[str, Any]]:
    rng = _rng(workspace, app_name, attempt)
    head = _rand_letters(rng, 2)
    app2 = _app_letters(app_name, 2)
    tail = _rand_letters(rng, 1)
    prefix = head + app2 + tail
    return prefix, _meta_v2("dual_random_head", prefix)


def _generate_consonant_core(
    app_name: str,
    workspace: Path,
    attempt: int,
) -> tuple[str, dict[str, Any]]:
    rng = _rng(workspace, app_name, attempt)
    core = _consonants(app_name, 3)
    rand = _rand_letters(rng, 2)
    prefix = core + rand
    return prefix, _meta_v2("consonant_core", prefix)


def _generate_reverse_initials(
    app_name: str,
    workspace: Path,
    attempt: int,
) -> tuple[str, dict[str, Any]]:
    rng = _rng(workspace, app_name, attempt)
    letters = _app_letters(app_name, 3)
    r0 = _rand_letters(rng, 1)
    r1 = _rand_letters(rng, 1)
    prefix = f"{letters[2]}{letters[1]}{r0}{letters[0]}{r1}"
    return prefix, _meta_v2("reverse_initials", prefix)


def _generate_vowel_bridge(
    app_name: str,
    workspace: Path,
    attempt: int,
) -> tuple[str, dict[str, Any]]:
    rng = _rng(workspace, app_name, attempt)
    letters = _app_letters(app_name, 3)
    v0 = _rand_vowels(rng, 1)
    v1 = _rand_vowels(rng, 1)
    prefix = f"{letters[0]}{v0}{letters[1]}{v1}{letters[2]}"
    return prefix, _meta_v2("vowel_bridge", prefix)


def _generate_batch_initial_embed(
    app_name: str,
    workspace: Path,
    batch_id: str,
    attempt: int,
) -> tuple[str, dict[str, Any]]:
    rng = _rng(workspace, app_name, attempt)
    batch2 = _batch_domain_2(batch_id or "batch")
    app2 = _app_letters(app_name, 2)
    rnd1 = _rand_letters(rng, 1)
    prefix = batch2 + app2 + rnd1
    return prefix, _meta_v2("batch_initial_embed", prefix, batch_id=batch_id or "")


def _generate_mirror_random(
    app_name: str,
    workspace: Path,
    attempt: int,
) -> tuple[str, dict[str, Any]]:
    rng = _rng(workspace, app_name, attempt)
    left = _rand_letters(rng, 2)
    pivot = _app_letters(app_name, 1)
    right = _rand_letters(rng, 2)
    prefix = left + pivot + right
    return prefix, _meta_v2("mirror_random", prefix)


def _generate_single_initial_triple(
    app_name: str,
    workspace: Path,
    attempt: int,
) -> tuple[str, dict[str, Any]]:
    rng = _rng(workspace, app_name, attempt)
    pivot = _app_letters(app_name, 1)
    rand = _rand_letters(rng, 3)
    prefix = pivot + rand
    return prefix, _meta_v2("single_initial_triple", prefix)


def _generate_cv_pseudoword(
    app_name: str,
    workspace: Path,
    attempt: int,
) -> tuple[str, dict[str, Any]]:
    rng = _rng(workspace, app_name, attempt)
    prefix = _cv_word(rng)
    return prefix, _meta_v2("cv_pseudoword", prefix)


def _generate_appname_split_insert(
    app_name: str,
    workspace: Path,
    attempt: int,
) -> tuple[str, dict[str, Any]]:
    rng = _rng(workspace, app_name, attempt)
    letters = _app_letters(app_name, 3)
    infix = _rand_letters(rng, 2)
    prefix = f"{letters[0]}{letters[1]}{infix}{letters[2]}"
    return prefix, _meta_v2("appname_split_insert", prefix)


def _generate_hash_domain(
    app_name: str,
    workspace: Path,
    batch_id: str,
    attempt: int,
) -> tuple[str, dict[str, Any]]:
    seed = abs(hash((app_name, batch_id, str(workspace), attempt)))
    letters: list[str] = []
    h = seed
    for _ in range(5):
        letters.append(string.ascii_lowercase[h % 26])
        h //= 26
    prefix = "".join(letters)
    return prefix, _meta_v2("hash_domain", prefix, batch_id=batch_id or "")


def generate_dart_prefix(
    rule_label: str,
    *,
    app_name: str,
    workspace: Path,
    batch_id: str = "",
    registry_path: Path | None = None,
) -> tuple[str, dict[str, Any]]:
    """Generate dartCodePrefix + namingRuleMeta per 命名混淆规则.md."""
    canonical = normalize_naming_obfuscation_rule(rule_label)
    if not canonical:
        raise ValueError(f"命名混淆规则无效: {rule_label!r}")

    recent = load_recent_dart_prefixes(registry_path or Path("/dev/null"))
    generators = {
        RULE_DUAL_RANDOM_HEAD: lambda a: _generate_dual_random_head(
            app_name, workspace, a
        ),
        RULE_CONSONANT_CORE: lambda a: _generate_consonant_core(
            app_name, workspace, a
        ),
        RULE_REVERSE_INITIALS: lambda a: _generate_reverse_initials(
            app_name, workspace, a
        ),
        RULE_VOWEL_BRIDGE: lambda a: _generate_vowel_bridge(app_name, workspace, a),
        RULE_BATCH_INITIAL_EMBED: lambda a: _generate_batch_initial_embed(
            app_name, workspace, batch_id, a
        ),
        RULE_MIRROR_RANDOM: lambda a: _generate_mirror_random(app_name, workspace, a),
        RULE_SINGLE_INITIAL_TRIPLE: lambda a: _generate_single_initial_triple(
            app_name, workspace, a
        ),
        RULE_CV_PSEUDOWORD: lambda a: _generate_cv_pseudoword(app_name, workspace, a),
        RULE_APPNAME_SPLIT_INSERT: lambda a: _generate_appname_split_insert(
            app_name, workspace, a
        ),
        RULE_HASH_DOMAIN: lambda a: _generate_hash_domain(
            app_name, workspace, batch_id, a
        ),
    }
    gen = generators[canonical]

    for attempt in range(_MAX_ATTEMPTS):
        prefix, meta = gen(attempt)
        if _valid_prefix(prefix, recent):
            meta["namingObfuscationRule"] = canonical
            return prefix, meta

    raise ValueError(
        f"无法为「{app_name}」分配唯一 dartCodePrefix（规则: {canonical}）"
    )


def apply_naming_rule_to_combo(
    workspace: Path,
    row: CsvTaskRow,
    data: dict[str, Any],
    *,
    registry_path: Path | None = None,
    batch_id: str = "",
) -> None:
    """Set namingObfuscationRule, dartCodePrefix, namingRuleMeta on combo dict."""
    from batch.dimension_lock import locked_code_prefix

    data["namingObfuscationRule"] = row.naming_obfuscation_rule
    canonical = normalize_naming_obfuscation_rule(row.naming_obfuscation_rule)

    existing = locked_code_prefix(workspace)
    if not existing:
        existing = str(data.get("dartCodePrefix") or "").strip()
    if existing and _PREFIX_RE.match(existing.lower()):
        meta = data.get("namingRuleMeta")
        if not isinstance(meta, dict):
            meta = {}
        else:
            meta = dict(meta)
        meta["packageSeed"] = existing
        if canonical:
            meta["namingObfuscationRule"] = canonical
        data["dartCodePrefix"] = existing
        data["namingRuleMeta"] = meta
        return

    prefix, meta = generate_dart_prefix(
        row.naming_obfuscation_rule,
        app_name=row.name,
        workspace=workspace,
        batch_id=batch_id,
        registry_path=registry_path,
    )
    data["dartCodePrefix"] = prefix
    data["namingRuleMeta"] = meta


def build_naming_rule_prompt_block(row: CsvTaskRow) -> str:
    """Build Agent instruction block for CSV naming obfuscation rule."""
    rule = row.naming_obfuscation_rule
    key = _RULE_KEY_BY_LABEL.get(rule, "")
    return (
        "\n[CSV Naming Obfuscation v2 — REQUIRED]\n"
        f"- namingObfuscationRule (from CSV): {rule}\n"
        f"- ruleKey: {key}\n"
        "- Read 命名混淆规则.md — dynamic key per identifier (no pre-baked affix).\n"
        "- dartCodePrefix / packageSeed in 本包代码组合.json is the package seed only.\n"
        "- Affix position: prefix | suffix | infix | mirror (see namingRuleMeta.affix).\n"
        "- Affix length varies within lengthRange; join style per entity "
        "(camel/pascal/snake/compact/dot/hyphen).\n"
        "- Use transform_identifier() / derive_key() for EVERY namable "
        "(folders, files, classes, methods, fields, params, locals).\n"
    )
