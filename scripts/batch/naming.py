"""Per-name functional naming generator.

Every namable (folder/file/class/method/field/param/local) is transformed
independently by a pure function:

    transform_identifier(
        rule_key=...,
        meta=...,             # namingRuleMeta from 本包维度锁.json
        entity=...,           # "folder" | "file" | "class" | "method" | ...
        semantic=...,         # e.g. "feed_coordinator" or "FeedCoordinator"
        salt=...,             # optional disambiguator
    ) -> name

The function is deterministic given (rule_key, meta, entity, semantic, salt),
so the scaffold step and Agent self-check produce the exact same name.

Each rule chooses where to splice its signature token (e.g.
``variableMiddleInsert``, ``embedSegment``, ``classSuffix``) onto the
semantic chunks of the requested entity; **no rule simply concatenates a
global prefix**. The package-level ``dartCodePrefix`` is treated as a
package seed that anchors LIB root names only.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
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

_PATTERN_PASCAL_SPLIT = re.compile(r"(?<!^)(?=[A-Z])")
_PATTERN_NON_ALNUM = re.compile(r"[^a-zA-Z0-9]+")
_PATTERN_SNAKE = re.compile(r"[_\s]+")


def _normalize_chunks(semantic: str) -> list[str]:
    """Return lowercase semantic chunks split on case + underscore boundaries."""
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


def _stable_token(seed: tuple[str, ...], alphabet: str, n: int) -> str:
    joined = "\x1f".join(seed).encode("utf-8")
    digest = hashlib.sha256(joined).digest()
    return "".join(alphabet[b % len(alphabet)] for b in digest[:n])


@dataclass(frozen=True)
class NamingMeta:
    """Subset of ``namingRuleMeta`` needed by ``transform_identifier``."""

    rule_key: str
    insert_token: str = ""
    class_suffix: str = ""
    left_random: str = ""
    right_random: str = ""
    infix: str = ""
    batch_domain2: str = ""
    pseudoword: str = ""
    opaque: str = ""
    app_initials2: str = ""
    pivot_initial: str = ""


def _resolve_insert(meta: NamingMeta, entity: Entity, semantic: str) -> str:
    """Return the per-rule token spliced into the identifier."""
    rk = meta.rule_key
    if rk == "single_initial_triple":
        return meta.insert_token or "xxx"
    if rk == "vowel_bridge":
        return meta.insert_token or "ae"
    if rk == "appname_split_insert":
        return meta.infix or "xx"
    if rk == "batch_initial_embed":
        return meta.batch_domain2 or "xx"
    if rk == "reverse_initials":
        return ""
    if rk in {"mirror_random"}:
        return ""
    if rk in {"dual_random_head", "consonant_core"}:
        return ""
    if rk in {"cv_pseudoword", "hash_domain"}:
        return _stable_token((rk, semantic), "abcdefghijklmnopqrstuvwxyz", 3)
    return ""


def _splice_pascal(chunks: list[str], insert: str) -> str:
    if not insert:
        return _pascal(chunks)
    if len(chunks) <= 1:
        return _pascal(chunks) + insert.capitalize()
    head = _pascal(chunks[:1])
    tail = _pascal(chunks[1:])
    return f"{head}{insert.lower()}{tail}"


def _splice_camel(chunks: list[str], insert: str) -> str:
    if not insert:
        return _camel(chunks)
    if len(chunks) <= 1:
        return (chunks[0] if chunks else "") + insert.lower()
    head = chunks[0]
    tail = _pascal(chunks[1:])
    return f"{head}{insert.lower()}{tail}"


def _splice_snake(chunks: list[str], insert: str) -> str:
    if not insert:
        return _snake(chunks)
    if len(chunks) <= 1:
        return _snake(chunks) + "_" + insert.lower()
    head = chunks[0]
    tail = "_".join(chunks[1:])
    return f"{head}_{insert.lower()}_{tail}"


def _mirror_wrap(name: str, meta: NamingMeta, snake: bool) -> str:
    left = meta.left_random
    right = meta.right_random
    if not left and not right:
        return name
    if snake:
        parts = [p for p in (left, name, right) if p]
        return "_".join(parts)
    capped = name[:1].upper() + name[1:] if name else name
    return f"{left}{capped}{right}".rstrip()


def _suffix_class(name: str, meta: NamingMeta) -> str:
    if meta.rule_key == "reverse_initials" and meta.class_suffix:
        return f"{name}{meta.class_suffix.capitalize()}"
    return name


def transform_identifier(
    *,
    rule_key: str,
    meta: NamingMeta,
    entity: Entity,
    semantic: str,
    salt: str = "",
) -> str:
    """Independently apply the rule to one identifier and return its final name.

    Per the doc: this is the only entry the scaffold/Agent should use; there
    is no global ``{prefix}_{semantic}`` shortcut.
    """
    chunks = _normalize_chunks(semantic)
    if salt:
        salted = _stable_token((rule_key, salt), "abcdefghijklmnopqrstuvwxyz", 2)
        chunks.append(salted)
    if not chunks:
        chunks = ["anon"]

    bound = NamingMeta(
        rule_key=rule_key,
        insert_token=meta.insert_token,
        class_suffix=meta.class_suffix,
        left_random=meta.left_random,
        right_random=meta.right_random,
        infix=meta.infix,
        batch_domain2=meta.batch_domain2,
        pseudoword=meta.pseudoword,
        opaque=meta.opaque,
        app_initials2=meta.app_initials2,
        pivot_initial=meta.pivot_initial,
    )
    insert = _resolve_insert(bound, entity, semantic)

    if entity in {"class", "record"}:
        name = _splice_pascal(chunks, insert)
        return _suffix_class(name, bound)

    if entity in {"method", "field", "param", "local"}:
        return _splice_camel(chunks, insert)

    if entity == "enum_value":
        return _splice_camel(chunks, insert)

    if entity == "file":
        snake = _splice_snake(chunks, insert)
        if rule_key == "mirror_random":
            snake = _mirror_wrap(snake, bound, snake=True)
        return snake

    if entity == "folder":
        snake = _splice_snake(chunks, insert)
        if rule_key == "mirror_random":
            snake = _mirror_wrap(snake, bound, snake=True)
        return snake

    return _splice_camel(chunks, insert)


def meta_from_lock(naming_rule_meta: dict[str, object] | None) -> NamingMeta:
    """Build NamingMeta from ``本包维度锁.json -> namingObfuscationRule.namingRuleMeta``."""
    nm = naming_rule_meta or {}

    def s(key: str) -> str:
        val = nm.get(key)
        return str(val).strip().lower() if isinstance(val, str) else ""

    return NamingMeta(
        rule_key=s("ruleKey"),
        insert_token=s("variableMiddleInsert") or s("embedSegment") or s("randomTail"),
        class_suffix=s("classSuffix"),
        left_random=s("leftRandom"),
        right_random=s("rightRandom"),
        infix=s("infix"),
        batch_domain2=s("batchDomain2"),
        pseudoword=s("pseudoword"),
        opaque=s("opaque"),
        app_initials2=s("appInitials2"),
        pivot_initial=s("pivotInitial"),
    )


def transform_block_for_prompt(meta: NamingMeta) -> str:
    """Render a compact Prompt block that explains the transform contract."""
    return (
        "\n[Naming Transform — APPLY PER IDENTIFIER]\n"
        f"- ruleKey: {meta.rule_key}\n"
        f"- insertToken: {meta.insert_token!r}\n"
        f"- classSuffix: {meta.class_suffix!r}\n"
        f"- leftRandom: {meta.left_random!r}\n"
        f"- rightRandom: {meta.right_random!r}\n"
        f"- infix: {meta.infix!r}\n"
        f"- batchDomain2: {meta.batch_domain2!r}\n"
        "- Apply transform_identifier() independently to EVERY namable (folder, file,\n"
        "  class, method, field, param, local) under `lib/` **and** under `assets/`.\n"
        "  Do NOT concatenate a global prefix.\n"
        "- Reuse the package-wide tokens above on every name; the semantic chunks\n"
        "  differ per identifier — that is what produces the differentiation.\n"
        "- See 命名混淆规则.md → 'Per-name independent generation'.\n"
    )
