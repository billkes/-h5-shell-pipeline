"""Validate app names and product codes for prep-phase name pools."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from batch.prod_a_registry import ProdARegistry, subtitle_pair_from_full
from batch.task_schema import diversity_cap

MAIN_NAME_LEN = 6
# 副标题 Word1（A 面）候选池 — 与 name_generator 共用
SUBTITLE_A_FACE_WORDS = (
    "Calm",
    "Glow",
    "Soft",
    "Bright",
    "Mellow",
    "Pure",
    "Neat",
    "Warm",
    "Crisp",
    "Fine",
)
BANNED_SUBTITLE_WORDS = frozenset(
    {
        "dating",
        "matchmaker",
        "flirt",
        "meet",
        "hot",
    }
)

_FULL_NAME_RE = re.compile(
    r"^[A-Z][a-zA-Z]{4,5} - [A-Z][a-zA-Z]+ & [A-Z][a-zA-Z]+$",
)
_PRODUCT_CODE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^00[A-Z][a-zA-Z]{3}$"), "00 + 4位主题单词"),
    (re.compile(r"^00[A-Z][a-zA-Z]{4}$"), "00 + 5位主题单词"),
    (re.compile(r"^00[A-Z][a-zA-Z]{5}$"), "00 + 6位主题单词"),
    (re.compile(r"^[A-Z][a-zA-Z]{3}00$"), "4位主题单词+00"),
    (re.compile(r"^[A-Z][a-zA-Z]{4}00$"), "5位主题单词+00"),
    (re.compile(r"^[A-Z][a-zA-Z]{5}00$"), "6位主题单词+00"),
    (re.compile(r"^[A-Z][a-zA-Z]{6}00$"), "7位主题单词+00"),
)
_ALLOWED_PRODUCT_CODE_FORMATS = "、".join(label for _, label in _PRODUCT_CODE_PATTERNS)
_CONSONANT_RUN_RE = re.compile(r"[^aeiouAEIOU]{3,}")
_ROUND_VOWEL_RE = re.compile(r"(oo|yy|uu|ii)", re.IGNORECASE)
_ROUND_SYLLABLE_RE = re.compile(r"(oio|ioi|goi|joi|roi)", re.IGNORECASE)
_ENGLISH_WORDLIKE = frozenset(
    {
        "apple",
        "table",
        "water",
        "light",
        "house",
        "music",
        "photo",
        "video",
        "track",
        "store",
        "cloud",
        "dream",
        "happy",
        "world",
        "green",
        "black",
        "white",
        "small",
        "large",
        "quick",
        "smart",
        "clean",
        "fresh",
        "sweet",
        "brave",
        "calm",
        "glow",
        "soft",
        "bright",
        "neat",
        "warm",
        "crisp",
        "fine",
        "hold",
        "drift",
        "bloom",
        "span",
        "flow",
        "echo",
        "lane",
        "pair",
        "form",
        "hue",
        "pace",
        "style",
        "batch",
        "sweet",
        "glow",
        "ritual",
        "season",
        "script",
        "rhythm",
        "shade",
        "space",
        "order",
        "stride",
        "stroke",
        "dance",
        "polish",
        "closet",
        "idolry",
        "ovenry",
        "dermal",
        "capsul",
    }
)


@dataclass(frozen=True)
class NameCandidate:
    name: str
    full_name: str
    product_code: str


@dataclass(frozen=True)
class Denylist:
    app_names: frozenset[str]
    full_names: frozenset[str]
    main_names: frozenset[str]
    product_codes: frozenset[str]
    subtitle_pairs: frozenset[tuple[str, str]]


def build_denylist(
    registry: ProdARegistry,
    *,
    batch_app_names: frozenset[str] | None = None,
    batch_full_names: frozenset[str] | None = None,
    batch_codes: frozenset[str] | None = None,
    batch_subtitle_pairs: frozenset[tuple[str, str]] | None = None,
) -> Denylist:
    pairs: set[tuple[str, str]] = set(batch_subtitle_pairs or ())
    for entry in registry.entries:
        if entry.full_name:
            pair = subtitle_pair_from_full(entry.full_name)
            if pair:
                pairs.add(pair)
    mains: set[str] = set(registry.main_names)
    for full in batch_full_names or ():
        if " - " in full:
            mains.add(full.split(" - ", 1)[0].strip())
    return Denylist(
        app_names=frozenset(registry.app_names | (batch_app_names or frozenset())),
        full_names=frozenset(registry.full_names | (batch_full_names or frozenset())),
        main_names=frozenset(mains),
        product_codes=frozenset(registry.product_codes | (batch_codes or frozenset())),
        subtitle_pairs=frozenset(pairs),
    )


def main_name_from_full(full_name: str) -> str:
    text = (full_name or "").strip()
    if " - " in text:
        return text.split(" - ", 1)[0].strip()
    return text


def validate_main_name(name: str) -> list[str]:
    issues: list[str] = []
    raw = (name or "").strip()
    if len(raw) != MAIN_NAME_LEN:
        issues.append(f"主名字须 {MAIN_NAME_LEN} 个字母，当前 {len(raw)!r}")
    if not raw.isalpha():
        issues.append("主名字只能含字母")
    if raw and not raw[0].isupper():
        issues.append("主名字首字母须大写")
    lower = raw.lower()
    if lower in _ENGLISH_WORDLIKE:
        issues.append(f"主名字 {raw!r} 像真实英语单词")
    if _CONSONANT_RUN_RE.search(raw):
        issues.append(f"主名字 {raw!r} 含连续 3+ 辅音")
    if not (_ROUND_VOWEL_RE.search(raw) or _ROUND_SYLLABLE_RE.search(raw)):
        issues.append(f"主名字 {raw!r} 缺少圆润音韵（oo/yy/uu/ii 或 oio/ioi/goi/joi/roi）")
    return issues


def validate_full_name(full_name: str) -> list[str]:
    issues: list[str] = []
    text = (full_name or "").strip()
    if not _FULL_NAME_RE.match(text):
        issues.append(f"全称格式须为 Main - Word1 & Word2: {text!r}")
        return issues
    pair = subtitle_pair_from_full(text)
    if not pair:
        issues.append(f"无法解析副标题: {text!r}")
        return issues
    for word in pair:
        if word.lower() in BANNED_SUBTITLE_WORDS:
            issues.append(f"副标题含禁词: {word!r}")
    return issues


def validate_product_code(code: str) -> list[str]:
    issues: list[str] = []
    text = (code or "").strip()
    if not text:
        issues.append("商品Code 为空")
        return issues
    if not any(pattern.match(text) for pattern, _ in _PRODUCT_CODE_PATTERNS):
        issues.append(
            f"商品Code 须为以下格式之一（{_ALLOWED_PRODUCT_CODE_FORMATS}）: {text!r}"
        )
    if not text.replace("00", "").isalpha():
        issues.append(f"商品Code 只能含字母与 00: {text!r}")
    return issues


def validate_candidate(
    candidate: NameCandidate,
    deny: Denylist,
) -> list[str]:
    issues: list[str] = []
    issues.extend(validate_main_name(candidate.name))
    issues.extend(validate_full_name(candidate.full_name))
    issues.extend(validate_product_code(candidate.product_code))

    main = main_name_from_full(candidate.full_name)
    if main != candidate.name:
        issues.append(f"全称主名 {main!r} 与 应用主名称 {candidate.name!r} 不一致")

    if candidate.name in deny.app_names:
        issues.append(f"应用主名称 {candidate.name!r} 已在产A总库")
    if main.lower() in {m.lower() for m in deny.main_names}:
        issues.append(f"主名字 {main!r} 已在产A总库")
    if candidate.full_name in deny.full_names:
        issues.append(f"全称 {candidate.full_name!r} 已在产A总库")
    if candidate.product_code in deny.product_codes:
        issues.append(f"商品Code {candidate.product_code!r} 已在产A总库")

    pair = subtitle_pair_from_full(candidate.full_name)
    if pair and pair in deny.subtitle_pairs:
        issues.append(f"副标题组合 {pair!r} 已在产A总库")

    return issues


def subtitle_a_face(full_name: str) -> str | None:
    """全称 `Main - A & B` 的 A 面词（Word1）。"""
    pair = subtitle_pair_from_full(full_name)
    return pair[0] if pair else None


def a_face_counts_from_full_names(full_names: list[str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for full in full_names:
        word = subtitle_a_face(full)
        if word:
            counts[word] += 1
    return counts


def a_face_batch_limit(batch_size: int) -> int:
    """批内同一 A 面词最大出现次数（与四维 diversity_cap 同公式）。"""
    if batch_size <= 0:
        return 0
    return diversity_cap(batch_size, len(SUBTITLE_A_FACE_WORDS))


def audit_subtitle_a_face_diversity(
    full_names: list[str],
    *,
    label: str = "批次",
) -> list[str]:
    """批内副标题 A 面词（Calm/Glow/…）不得扎堆。"""
    names = [f.strip() for f in full_names if (f or "").strip()]
    n = len(names)
    if n == 0:
        return []
    limit = a_face_batch_limit(n)
    counts = a_face_counts_from_full_names(names)
    violations: list[str] = []
    for word, cnt in sorted(counts.items()):
        if cnt > limit:
            violations.append(
                f"{label}副标题 A 面词「{word}」{cnt} 次 > 上限 {limit}（共 {n} 包）"
            )
    return violations


def pick_diverse_candidate_index(
    candidates: list[NameCandidate],
    deny: Denylist,
    a_face_counts: Counter[str],
    *,
    limit: int,
    start: int = 0,
) -> int:
    """从候选池选首个通过校验且未超 A 面词上限的下标。"""
    for i in range(max(0, start), len(candidates)):
        cand = candidates[i]
        issues = validate_candidate(cand, deny)
        if issues:
            continue
        a_word = subtitle_a_face(cand.full_name)
        if a_word and a_face_counts.get(a_word, 0) >= limit:
            continue
        return i
    raise RuntimeError(
        f"候选池 {start}-{len(candidates) - 1} 内无满足 A 面词上限 {limit} 的合法候选"
    )
