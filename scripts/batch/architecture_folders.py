"""Generate obfuscated architecture layer folder names (naming rule > semantic roles)."""

from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Any

from batch.scaffold_templates import (
    PATTERN_ROLE_DIRS,
    PATTERN_ROLE_STUBS,
    prefix_pascal,
)

# Folder / stub suffixes must not leak MVC/VIPER semantics or generic lib names.
_FORBIDDEN_SUFFIX_RE = re.compile(
    r"(^|_)(models?|views?|controllers?|presenters?|viewmodels?|"
    r"interactors?|entities|routers?|screens?|widgets?|services?|pages?|"
    r"utils|common|components|helpers|data|base|core|skin|open_flow)($|_)"
)

_SEMANTIC_DIR_RE_TEMPLATE = (
    r"^{prefix}_(models|views|controllers|presenters|viewmodels|"
    r"interactors|entities|routers)$"
)

_THEME_A = (
    "open",
    "http",
    "lane",
    "vault",
    "mesh",
    "dock",
    "ring",
    "pulse",
    "flux",
    "arc",
    "nova",
    "byte",
    "glyph",
    "mint",
    "sage",
    "ember",
    "drift",
    "prism",
    "quill",
    "spark",
)
_THEME_B = (
    "strip",
    "lane",
    "vault",
    "core",
    "mesh",
    "dock",
    "ring",
    "pulse",
    "flow",
    "gate",
    "hub",
    "nest",
    "path",
    "wave",
    "zone",
    "link",
    "node",
    "port",
    "slot",
    "unit",
)


def _rng(
    workspace: Path,
    app_name: str,
    prefix: str,
    pattern_key: str,
    naming_rule: str,
) -> random.Random:
    seed = (
        hash(str(workspace))
        ^ hash(app_name)
        ^ hash(prefix)
        ^ hash(pattern_key)
        ^ hash(naming_rule)
    )
    return random.Random(seed & 0xFFFFFFFF)


def _suffix_allowed(suffix: str) -> bool:
    s = suffix.lower().strip()
    if not s or len(s) < 3:
        return False
    if not re.fullmatch(r"[a-z][a-z0-9_]*", s):
        return False
    return _FORBIDDEN_SUFFIX_RE.search(s) is None


def _unique_theme_suffix(rng: random.Random, used: set[str]) -> str:
    for _ in range(200):
        a = rng.choice(_THEME_A)
        b = rng.choice(_THEME_B)
        if a == b:
            suffix = f"{a}_{rng.choice(_THEME_B)}"
        else:
            suffix = f"{a}_{b}"
        if suffix in used:
            suffix = f"{a}_{b}_{rng.randint(2, 99)}"
        if _suffix_allowed(suffix) and suffix not in used:
            used.add(suffix)
            return suffix
    tail = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(4))
    suffix = f"lane_{tail}"
    used.add(suffix)
    return suffix


def generate_architecture_folders(
    *,
    prefix: str,
    pattern_key: str,
    workspace: Path,
    app_name: str,
    naming_rule_label: str,
) -> dict[str, dict[str, str]]:
    """Map architecture role keys to obfuscated folder + stub basenames."""
    roles = PATTERN_ROLE_DIRS.get(pattern_key, ())
    if not roles:
        return {}

    rng = _rng(workspace, app_name, prefix, pattern_key, naming_rule_label)
    used_suffixes: set[str] = set()
    out: dict[str, dict[str, str]] = {}

    for role in roles:
        folder_suffix = _unique_theme_suffix(rng, used_suffixes)
        folder_basename = f"{prefix}_{folder_suffix}"
        stub_tail = _unique_theme_suffix(rng, used_suffixes)
        stub_basename = f"{prefix}_{stub_tail}_anchor"
        class_suffix = PATTERN_ROLE_STUBS.get(pattern_key, {}).get(role, "Layer")
        out[role] = {
            "role": role,
            "folderSuffix": folder_suffix,
            "folderBasename": folder_basename,
            "stubBasename": stub_basename,
            "stubClassSuffix": class_suffix,
        }
    return out


def architecture_folders_from_lock(lock: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Normalized architectureFolders map from lock or combo."""
    raw = lock.get("architectureFolders")
    if isinstance(raw, dict) and raw:
        out: dict[str, dict[str, str]] = {}
        for role, entry in raw.items():
            if isinstance(entry, str):
                prefix = str(
                    (lock.get("namingObfuscationRule") or {}).get("dartCodePrefix") or ""
                ).strip()
                out[str(role)] = {
                    "role": str(role),
                    "folderSuffix": entry,
                    "folderBasename": f"{prefix}_{entry}" if prefix else entry,
                    "stubBasename": "",
                    "stubClassSuffix": PATTERN_ROLE_STUBS.get(
                        _pattern_key_from_lock(lock), {}
                    ).get(str(role), "Layer"),
                }
            elif isinstance(entry, dict):
                out[str(role)] = {k: str(v) for k, v in entry.items()}
        return out
    return {}


def _pattern_key_from_lock(lock: dict[str, Any]) -> str:
    ap = lock.get("architecturePattern") or {}
    return str(ap.get("key") or "").strip().lower()


def resolve_role_folder_basename(
    lock: dict[str, Any],
    role: str,
    prefix: str,
) -> str:
    """Folder basename for a role; legacy workspaces fall back to semantic names."""
    folders = architecture_folders_from_lock(lock)
    if role in folders:
        base = folders[role].get("folderBasename", "")
        if base:
            return base
    return f"{prefix}_{role}"


def resolve_all_role_folder_basenames(
    lock: dict[str, Any],
    prefix: str,
    pattern_key: str,
) -> dict[str, str]:
    folders = architecture_folders_from_lock(lock)
    if folders:
        return {
            role: entry.get("folderBasename", f"{prefix}_{role}")
            for role, entry in folders.items()
        }
    return {role: f"{prefix}_{role}" for role in PATTERN_ROLE_DIRS.get(pattern_key, ())}


def semantic_dir_pattern(prefix: str) -> re.Pattern[str]:
    return re.compile(_SEMANTIC_DIR_RE_TEMPLATE.format(prefix=re.escape(prefix)))


def stub_class_name(prefix: str, entry: dict[str, str]) -> str:
    pascal = prefix_pascal(prefix)
    suffix = entry.get("stubClassSuffix") or "Layer"
    if entry.get("role") == "models":
        return f"{pascal}ShapeCore"
    return f"{pascal}Base{suffix}"


def build_architecture_folder_prompt_block(
    folders: dict[str, dict[str, str]],
) -> str:
    """Agent instruction listing opaque architecture role folders from lock."""
    if not folders:
        return ""
    lines = [
        "\n[Architecture Folders — LOCKED opaque paths]",
        "Use ONLY these role directories from 本包维度锁.json / 本包代码组合.json. "
        "Do NOT create semantic dirs ({prefix}_models/, _controllers/, etc.).",
    ]
    for role in sorted(folders):
        entry = folders[role]
        folder = entry.get("folderBasename", "")
        stub = entry.get("stubBasename", "")
        lines.append(f"- {role}: `{folder}/` (stub: `{stub}.dart`)")
    return "\n".join(lines) + "\n"


def merge_architecture_folders_into_combo(
    data: dict[str, Any],
    *,
    workspace: Path,
    app_name: str,
    pattern_key: str,
    naming_rule_label: str,
) -> dict[str, dict[str, str]]:
    prefix = str(data.get("dartCodePrefix") or "").strip()
    if not prefix or not pattern_key:
        return {}
    folders = generate_architecture_folders(
        prefix=prefix,
        pattern_key=pattern_key,
        workspace=workspace,
        app_name=app_name,
        naming_rule_label=naming_rule_label,
    )
    data["architectureFolders"] = folders
    return folders
