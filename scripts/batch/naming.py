"""Per-name dynamic naming generator (v2).

Every namable is transformed independently:

    transform_identifier(
        rule_key=...,
        meta=...,             # seeds only — no pre-baked affix keys
        entity=...,
        semantic=...,
        salt=...,
    ) -> str

Affix keys are derived at transform time via ``derive_key()`` (length within a
rule-specific range). Join style (camel / pascal / snake / compact / dot /
hyphen) is chosen per entity.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Literal

Entity = Literal[
    "folder",
    "file",
    "class",
    "record",
    "method",
    "field",
    "param",
    "local",
    "enum_value",
]

AffixKind = Literal["prefix", "suffix", "infix", "mirror"]
JoinStyle = Literal["camel", "pascal", "snake", "compact", "dot", "hyphen"]

_PATTERN_PASCAL_SPLIT = re.compile(r"(?<!^)(?=[A-Z])")
_PATTERN_NON_ALNUM = re.compile(r"[^a-zA-Z0-9]+")
_PATTERN_SNAKE = re.compile(r"[_\s]+")

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"

_DEFAULT_JOIN_BY_ENTITY: dict[str, JoinStyle] = {
    "class": "pascal",
    "record": "pascal",
    "method": "camel",
    "field": "camel",
    "param": "camel",
    "local": "camel",
    "enum_value": "camel",
    "file": "snake",
    "folder": "snake",
}

# Featured four + full CSV rule set profiles.
RULE_PROFILES: dict[str, dict[str, object]] = {
    "consonant_core": {
        "affix": "prefix",
        "length_range": (2, 4),
        "join_styles": dict(_DEFAULT_JOIN_BY_ENTITY),
    },
    "reverse_initials": {
        "affix": "suffix",
        "length_range": (2, 3),
        "join_styles": dict(_DEFAULT_JOIN_BY_ENTITY),
    },
    "single_initial_triple": {
        "affix": "infix",
        "length_range": (2, 5),
        "join_styles": dict(_DEFAULT_JOIN_BY_ENTITY),
    },
    "mirror_random": {
        "affix": "mirror",
        "length_range": (2, 3),
        "mirror_length_range": (2, 3),
        "join_styles": {
            **_DEFAULT_JOIN_BY_ENTITY,
            "file": "snake",
            "folder": "snake",
            "local": "compact",
            "field": "compact",
            "method": "compact",
            "param": "compact",
        },
    },
    "dual_random_head": {
        "affix": "prefix",
        "length_range": (2, 4),
        "join_styles": dict(_DEFAULT_JOIN_BY_ENTITY),
    },
    "vowel_bridge": {
        "affix": "infix",
        "length_range": (2, 3),
        "alphabet": "aeiou",
        "join_styles": dict(_DEFAULT_JOIN_BY_ENTITY),
    },
    "batch_initial_embed": {
        "affix": "infix",
        "length_range": (2, 4),
        "join_styles": dict(_DEFAULT_JOIN_BY_ENTITY),
    },
    "cv_pseudoword": {
        "affix": "prefix",
        "length_range": (3, 5),
        "join_styles": dict(_DEFAULT_JOIN_BY_ENTITY),
    },
    "appname_split_insert": {
        "affix": "infix",
        "length_range": (2, 4),
        "join_styles": dict(_DEFAULT_JOIN_BY_ENTITY),
    },
    "hash_domain": {
        "affix": "prefix",
        "length_range": (3, 5),
        "join_styles": dict(_DEFAULT_JOIN_BY_ENTITY),
    },
}

FEATURED_RULE_KEYS: tuple[str, ...] = (
    "consonant_core",
    "reverse_initials",
    "single_initial_triple",
    "mirror_random",
)


def _normalize_chunks(semantic: str) -> list[str]:
    cleaned = semantic.strip()
    if not cleaned:
        return []
    parts: list[str] = []
    for piece in _PATTERN_SNAKE.split(cleaned):
        if not piece:
            continue
        for chunk in _PATTERN_PASCAL_SPLIT.split(piece):
            chunk = _PATTERN_NON_ALNUM.sub("", chunk).lower()
            if chunk:
                parts.append(chunk)
    return parts


def _pascal(chunks: list[str]) -> str:
    return "".join(c[:1].upper() + c[1:] for c in chunks if c)


def _camel(chunks: list[str]) -> str:
    if not chunks:
        return ""
    return chunks[0] + _pascal(chunks[1:])


def _snake(chunks: list[str]) -> str:
    return "_".join(chunks)


def derive_key(
    *,
    rule_key: str,
    package_seed: str,
    entity: Entity,
    semantic: str,
    role: str,
    length_range: tuple[int, int],
    salt: str = "",
    extra: str = "",
    alphabet: str = _ALPHABET,
) -> str:
    """Deterministic affix key; length varies within ``length_range``."""
    min_len, max_len = length_range
    joined = "\x1f".join(
        (rule_key, package_seed, entity, semantic, role, salt, extra)
    ).encode("utf-8")
    digest = hashlib.sha256(joined).digest()
    span = max_len - min_len + 1
    length = min_len + (digest[0] % span)
    return "".join(alphabet[digest[i + 1] % len(alphabet)] for i in range(length))


def build_rule_meta(
    rule_key: str,
    package_seed: str,
    *,
    batch_id: str = "",
) -> dict[str, object]:
    """Build v2 namingRuleMeta (seeds only, no affix keys)."""
    profile = RULE_PROFILES.get(rule_key, RULE_PROFILES["consonant_core"])
    meta: dict[str, object] = {
        "ruleKey": rule_key,
        "packageSeed": package_seed,
        "affix": profile["affix"],
        "lengthRange": list(profile["length_range"]),
        "joinStyles": dict(profile.get("join_styles") or {}),
    }
    if profile.get("mirror_length_range"):
        meta["mirrorLengthRange"] = list(profile["mirror_length_range"])
    if batch_id:
        meta["batchId"] = batch_id
    if profile.get("alphabet"):
        meta["alphabet"] = profile["alphabet"]
    return meta


@dataclass(frozen=True)
class NamingMeta:
    """Seeds for ``transform_identifier`` — no pre-baked affix tokens."""

    rule_key: str
    package_seed: str = ""
    affix: AffixKind = "infix"
    length_range: tuple[int, int] = (2, 4)
    mirror_length_range: tuple[int, int] = (2, 3)
    join_styles: dict[str, str] = field(default_factory=dict)
    batch_id: str = ""
    alphabet: str = _ALPHABET


def _profile_for(rule_key: str) -> dict[str, object]:
    return RULE_PROFILES.get(rule_key, RULE_PROFILES["consonant_core"])


def _resolve_join_style(entity: Entity, meta: NamingMeta) -> JoinStyle:
    styles = meta.join_styles or {}
    if entity in styles:
        return styles[entity]  # type: ignore[return-value]
    profile = _profile_for(meta.rule_key)
    profile_styles = profile.get("join_styles") or {}
    if entity in profile_styles:
        return profile_styles[entity]  # type: ignore[return-value]
    return _DEFAULT_JOIN_BY_ENTITY.get(entity, "camel")  # type: ignore[return-value]


def _format_base(chunks: list[str], join_style: JoinStyle) -> str:
    if join_style == "pascal":
        return _pascal(chunks)
    if join_style == "camel":
        return _camel(chunks)
    if join_style == "snake":
        return _snake(chunks)
    if join_style == "compact":
        return "".join(chunks)
    if join_style == "dot":
        return ".".join(chunks)
    if join_style == "hyphen":
        return "-".join(chunks)
    return _camel(chunks)


def _join_affix(
    parts: list[str],
    join_style: JoinStyle,
) -> str:
    filtered = [p for p in parts if p]
    if not filtered:
        return ""
    if join_style == "pascal":
        return "".join(p[:1].upper() + p[1:] for p in filtered)
    if join_style == "camel":
        head = filtered[0]
        tail = "".join(p[:1].upper() + p[1:] for p in filtered[1:])
        return head + tail
    if join_style == "snake":
        return "_".join(filtered)
    if join_style == "compact":
        return "".join(filtered)
    if join_style == "dot":
        return ".".join(filtered)
    if join_style == "hyphen":
        return "-".join(filtered)
    return "".join(filtered)


def _apply_prefix(
    chunks: list[str],
    key: str,
    join_style: JoinStyle,
) -> str:
    base = _format_base(chunks, join_style)
    if join_style == "pascal":
        return key[:1].upper() + key[1:] + base
    if join_style in {"camel", "compact"}:
        return key.lower() + base
    return _join_affix([key.lower(), base], join_style)


def _apply_suffix(
    chunks: list[str],
    key: str,
    join_style: JoinStyle,
) -> str:
    base = _format_base(chunks, join_style)
    if join_style == "pascal":
        return base + key[:1].upper() + key[1:]
    if join_style in {"camel", "compact"}:
        return base + key.lower()
    return _join_affix([base, key.lower()], join_style)


def _apply_infix(
    chunks: list[str],
    key: str,
    join_style: JoinStyle,
) -> str:
    if not chunks:
        chunks = ["anon"]
    if len(chunks) <= 1:
        word = chunks[0]
        if join_style == "pascal":
            return _pascal([word]) + key[:1].upper() + key[1:]
        if join_style in {"camel", "compact"}:
            return word + key.lower()
        return _join_affix([word, key.lower()], join_style)

    head, *tail = chunks
    if join_style == "pascal":
        return _pascal([head]) + key.lower() + _pascal(tail)
    if join_style == "camel":
        return head + key.lower() + _pascal(tail)
    if join_style == "compact":
        return head + key.lower() + "".join(tail)
    if join_style == "snake":
        return _join_affix([head, key.lower(), _snake(tail)], "snake")
    if join_style == "dot":
        return _join_affix([head, key.lower(), ".".join(tail)], "dot")
    if join_style == "hyphen":
        return _join_affix([head, key.lower(), "-".join(tail)], "hyphen")
    return head + key.lower() + _pascal(tail)


def _apply_mirror(
    chunks: list[str],
    left: str,
    right: str,
    join_style: JoinStyle,
) -> str:
    base = _format_base(chunks, join_style)
    if join_style in {"snake", "dot", "hyphen"}:
        return _join_affix([left.lower(), base, right.lower()], join_style)
    if join_style == "pascal":
        mid = base[:1].upper() + base[1:] if base else ""
        return left.lower() + mid + right.lower()
    return left.lower() + base + right.lower()


def transform_identifier(
    *,
    rule_key: str,
    meta: NamingMeta,
    entity: Entity,
    semantic: str,
    salt: str = "",
) -> str:
    """Apply dynamic affix naming to one identifier."""
    profile = _profile_for(rule_key)
    affix: AffixKind = meta.affix or profile["affix"]  # type: ignore[assignment]
    length_range = meta.length_range or profile["length_range"]  # type: ignore[assignment]
    join_style = _resolve_join_style(entity, meta)
    alphabet = meta.alphabet or str(profile.get("alphabet") or _ALPHABET)

    chunks = _normalize_chunks(semantic)
    if salt:
        chunks = chunks + [
            derive_key(
                rule_key=rule_key,
                package_seed=meta.package_seed,
                entity=entity,
                semantic=semantic,
                role="salt",
                length_range=(2, 2),
                salt=salt,
            )
        ]
    if not chunks:
        chunks = ["anon"]

    extra = meta.batch_id if rule_key in {"batch_initial_embed", "hash_domain"} else ""

    if affix == "prefix":
        key = derive_key(
            rule_key=rule_key,
            package_seed=meta.package_seed,
            entity=entity,
            semantic=semantic,
            role="pre",
            length_range=length_range,
            salt=salt,
            extra=extra,
            alphabet=alphabet,
        )
        return _apply_prefix(chunks, key, join_style)

    if affix == "suffix":
        key = derive_key(
            rule_key=rule_key,
            package_seed=meta.package_seed,
            entity=entity,
            semantic=semantic,
            role="suf",
            length_range=length_range,
            salt=salt,
            extra=extra,
            alphabet=alphabet,
        )
        return _apply_suffix(chunks, key, join_style)

    if affix == "infix":
        key = derive_key(
            rule_key=rule_key,
            package_seed=meta.package_seed,
            entity=entity,
            semantic=semantic,
            role="mid",
            length_range=length_range,
            salt=salt,
            extra=extra,
            alphabet=alphabet,
        )
        return _apply_infix(chunks, key, join_style)

    if affix == "mirror":
        mirror_range = meta.mirror_length_range or profile.get(
            "mirror_length_range", (2, 3)
        )
        left = derive_key(
            rule_key=rule_key,
            package_seed=meta.package_seed,
            entity=entity,
            semantic=semantic,
            role="L",
            length_range=mirror_range,  # type: ignore[arg-type]
            salt=salt,
            extra=extra,
            alphabet=alphabet,
        )
        right = derive_key(
            rule_key=rule_key,
            package_seed=meta.package_seed,
            entity=entity,
            semantic=semantic,
            role="R",
            length_range=mirror_range,  # type: ignore[arg-type]
            salt=salt,
            extra=extra,
            alphabet=alphabet,
        )
        return _apply_mirror(chunks, left, right, join_style)

    key = derive_key(
        rule_key=rule_key,
        package_seed=meta.package_seed,
        entity=entity,
        semantic=semantic,
        role="mid",
        length_range=length_range,
        salt=salt,
        extra=extra,
        alphabet=alphabet,
    )
    return _apply_infix(chunks, key, join_style)


def meta_from_lock(naming_rule_meta: dict[str, object] | None) -> NamingMeta:
    """Build NamingMeta from ``本包维度锁.json -> namingRuleMeta`` (v2 or legacy)."""
    nm = naming_rule_meta or {}

    def s(key: str) -> str:
        val = nm.get(key)
        return str(val).strip().lower() if isinstance(val, str) else ""

    def parse_range(key: str, default: tuple[int, int]) -> tuple[int, int]:
        raw = nm.get(key)
        if isinstance(raw, (list, tuple)) and len(raw) == 2:
            try:
                return int(raw[0]), int(raw[1])
            except (TypeError, ValueError):
                pass
        return default

    rule_key = s("ruleKey")
    profile = _profile_for(rule_key)
    package_seed = s("packageSeed") or s("dartCodePrefix")
    join_raw = nm.get("joinStyles")
    join_styles: dict[str, str] = {}
    if isinstance(join_raw, dict):
        join_styles = {str(k): str(v) for k, v in join_raw.items()}

    affix_raw = nm.get("affix") or profile.get("affix") or "infix"
    alphabet_raw = nm.get("alphabet")
    alphabet = (
        str(alphabet_raw)
        if isinstance(alphabet_raw, str) and alphabet_raw
        else str(profile.get("alphabet") or _ALPHABET)
    )

    return NamingMeta(
        rule_key=rule_key,
        package_seed=package_seed,
        affix=affix_raw,  # type: ignore[arg-type]
        length_range=parse_range(
            "lengthRange", profile["length_range"]  # type: ignore[arg-type]
        ),
        mirror_length_range=parse_range(
            "mirrorLengthRange",
            profile.get("mirror_length_range", (2, 3)),  # type: ignore[arg-type]
        ),
        join_styles=join_styles,
        batch_id=s("batchId") or s("batch_id"),
        alphabet=alphabet,
    )


def transform_block_for_prompt(meta: NamingMeta) -> str:
    """Render a compact Prompt block for dynamic naming v2."""
    profile = _profile_for(meta.rule_key)
    affix = meta.affix or profile.get("affix", "infix")
    length_range = meta.length_range or profile.get("length_range", (2, 4))
    return (
        "\n[Naming Transform v2 — DYNAMIC KEY PER IDENTIFIER]\n"
        f"- ruleKey: {meta.rule_key}\n"
        f"- packageSeed: {meta.package_seed!r}\n"
        f"- affix: {affix} (prefix | suffix | infix | mirror)\n"
        f"- lengthRange: {list(length_range)}\n"
        f"- joinStyles: {meta.join_styles or profile.get('join_styles', {})}\n"
        "- Affix keys are NOT stored in meta; call derive_key() / "
        "transform_identifier() per namable.\n"
        "- Key length varies within lengthRange (hash-derived, not fixed 3).\n"
        "- Join style per entity: camel / pascal / snake / compact / dot / hyphen.\n"
        "- Apply to EVERY namable under `lib/` and `assets/` (see 命名混淆规则.md).\n"
    )
