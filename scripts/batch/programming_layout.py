"""Programming-persona layout matrix — lib tree shape & asset roots (dims 6–7)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from batch.csv_tasks import CsvTaskRow, normalize_programming_style
from batch.asset_naming import resolve_asset_layout_from_lock
from batch.h5_site_paths import (
    DEFAULT_H5_SITE_ROOT,
    app_slug_from_name,
    build_h5_remote_prompt_block,
    resolve_h5_remote_config,
)

RESOURCE_LAYOUT_FILE = "本包资源布局.json"

# Dimension 6 — lib/{prefix}_{pkg}/ topology (architecture role folders unchanged).
LIB_LAYOUT_BY_PERSONA: dict[str, str] = {
    "美国人": "flat_skin_role",
    "英国人": "flat_skin_role_helper",
    "德国人": "nested_role_leaf",
    "法国人": "dual_hub",
    "俄罗斯人": "single_lane",
    "日本人": "shell_bay",
    "中国人": "feature_mod_wrap",
}

# Dimension 7 — pubspec asset roots + naming convention.
ASSET_LAYOUT_BY_PERSONA: dict[str, str] = {
    "美国人": "assets_images_flat",
    "英国人": "assets_media_split",
    "德国人": "assets_prefix_bundled",
    "法国人": "assets_prefix_surfaces_glyphs",
    "俄罗斯人": "assets_img_flat",
    "日本人": "assets_prefix_panels_icons",
    "中国人": "assets_bundle_prefix",
}

FORBIDDEN_ASSET_BASENAMES = frozenset(
    {
        "splash_background.png",
        "global_background.png",
        "splash_background.jpg",
        "global_background.jpg",
    }
)

_LIB_LAYOUT_DESC: dict[str, str] = {
    "flat_skin_role": (
        "`lib/{prefix}_{pkg}/{prefix}_skin/` + architecture role folders as siblings "
        "(default flat topology)."
    ),
    "flat_skin_role_helper": (
        "Same as flat_skin_role plus `{prefix}_helper/` sibling for shared UI helpers."
    ),
    "nested_role_leaf": (
        "Each architecture role folder MUST contain `{prefix}_{roleKey}_leaf/` for "
        "business `.dart` files; stubs stay at role root."
    ),
    "dual_hub": (
        "Split `{prefix}_core/` (tokens, models) vs `{prefix}_surface/` (views, "
        "presenters/controllers); no top-level `{prefix}_skin/`."
    ),
    "single_lane": (
        "Minimal `{prefix}_skin/` (tokens only) + `{prefix}_lane/` holds home, stubs, "
        "and most UI `.dart` files."
    ),
    "shell_bay": (
        "Rename skin bucket to `{prefix}_shell/`; each role folder adds "
        "`{prefix}_bay/` subfolder for screens."
    ),
    "feature_mod_wrap": (
        "`{prefix}_skin/` plus `{prefix}_mod_{role}/` wrapper dirs grouping each "
        "architecture role subtree."
    ),
}

_ASSET_LAYOUT_DESC: dict[str, str] = {
    "assets_images_flat": (
        "Single obfuscated raster root under `assets/` (naming transform, "
        "NOT `assets/images/`)."
    ),
    "assets_media_split": (
        "Two obfuscated roots: raster vs glyph buckets (naming transform)."
    ),
    "assets_prefix_bundled": (
        "One obfuscated bundled vault folder under `assets/`."
    ),
    "assets_prefix_surfaces_glyphs": (
        "Two obfuscated roots: surface vs glyph rasters."
    ),
    "assets_img_flat": (
        "One obfuscated flat img lane under `assets/`."
    ),
    "assets_prefix_panels_icons": (
        "Two obfuscated roots: panel vs icon rasters."
    ),
    "assets_bundle_prefix": (
        "Obfuscated bundle root with nested ui/tex subfolders."
    ),
}

# h5_shell deploy is ALWAYS Vite singlefile monolith — programming persona no longer
# forks {prefix}_entry.htm / css / js layouts (legacy keys kept for gate back-compat).
H5_VAULT_PATTERN_BY_ASSET_LAYOUT: dict[str, str] = {
    "assets_img_flat": "h5_monolith",
    "assets_prefix_bundled": "h5_monolith",
    "assets_images_flat": "h5_monolith",
    "assets_media_split": "h5_monolith",
    "assets_prefix_surfaces_glyphs": "h5_monolith",
    "assets_prefix_panels_icons": "h5_monolith",
    "assets_bundle_prefix": "h5_monolith",
}

H5_DEPLOY_PATTERN = "h5_monolith"

_H5_VAULT_PATTERN_DESC: dict[str, str] = {
    "h5_monolith": (
        "Single `index.html` under `h5_site/{appSlug}/` "
        "(vite-plugin-singlefile deploy output — ONLY allowed pattern)."
    ),
    # Legacy descriptors — kept so old register dumps remain readable; never emitted.
    "h5_modular_css": (
        "DEPRECATED — was `{prefix}_entry.htm` + `{prefix}_baseline.css`."
    ),
    "h5_modular_svg": (
        "DEPRECATED — was entry + baseline.css + `{prefix}_marks.svg`."
    ),
    "h5_modular_full": (
        "DEPRECATED — was entry + baseline.css + marks.svg + `{prefix}_panels/`."
    ),
}


def resolve_h5_vault_layout(
    persona: str,
    *,
    prefix: str = "",
    asset_layout: str | None = None,
    app_name: str = "",
) -> dict[str, Any]:
    """Return fixed H5 deploy topology: h5_site/{appSlug}/index.html (monolith).

    ``persona`` / ``prefix`` / ``asset_layout`` only affect ``h5VaultLayout`` labeling
    (Native asset naming); deploy pattern is always ``h5_monolith``.
    """
    del prefix  # deploy path uses appSlug, not dart prefix
    key = persona_key(persona)
    layout_key = asset_layout or ASSET_LAYOUT_BY_PERSONA.get(key, "assets_images_flat")
    pattern = H5_DEPLOY_PATTERN
    slug = app_slug_from_name(app_name) if app_name else "app"
    upload_root = DEFAULT_H5_SITE_ROOT
    deploy_dir = f"{upload_root.rstrip('/')}/{slug}/"
    entry = f"{deploy_dir}index.html"
    return {
        "h5VaultPattern": pattern,
        "h5VaultLayout": layout_key,
        "bundleVaultDir": deploy_dir,
        "bundleEntryPath": entry,
        "h5VaultFiles": [entry],
        "h5VaultPatternDesc": _H5_VAULT_PATTERN_DESC[pattern],
    }


def build_h5_vault_layout_prompt_block(
    row: CsvTaskRow | None,
    *,
    prefix: str = "",
    app_name: str = "",
) -> str:
    if row is None:
        return ""
    layout = resolve_persona_layout(row.programming_style, prefix=prefix)
    h5 = resolve_h5_vault_layout(
        row.programming_style,
        prefix=prefix,
        asset_layout=str(layout.get("assetLayout") or ""),
        app_name=app_name,
    )
    remote = resolve_h5_remote_config(app_name or prefix, prefix=prefix)
    h5.update(
        {
            k: remote[k]
            for k in (
                "appSlug",
                "h5SiteUploadRoot",
                "h5SiteRoot",
                "h5SiteEntry",
                "h5SourceRoot",
                "h5BuildCommand",
                "h5EntryUrl",
                "h5EntryUrlDev",
                "h5EntryUrlProd",
                "launchPlaceholderAsset",
                "bundleVaultDir",
                "bundleEntryPath",
            )
        }
    )
    files = "\n".join(f"  - `{f}`" for f in h5["h5VaultFiles"])
    remote_block = build_h5_remote_prompt_block(app_name or prefix, prefix=prefix)
    return (
        "\n[H5 Site Structure — LOCKED monolith — REQUIRED]\n"
        "- Flutter CSV 架构模式 (MVP/MVC/…) + programmingStyle govern **shell runtime / "
        "Native naming only** — they do **NOT** change H5 deploy file layout.\n"
        "- Deployable H5 site is **always** vite-plugin-singlefile monolith:\n"
        f"  - h5VaultPattern: `{h5['h5VaultPattern']}` — {h5['h5VaultPatternDesc']}\n"
        f"  - h5SiteRoot: `{h5['h5SiteRoot']}`\n"
        f"  - h5SiteEntry: `{h5['h5SiteEntry']}` (must be `index.html`)\n"
        "- Required site files (exactly one):\n"
        f"{files}\n"
        "- **Forbidden**: `{prefix}_entry.htm`, split css/js/htm deploy trees, or "
        "`h5_modular_*` patterns.\n"
        "- Register `h5VaultPattern=h5_monolith`, `h5VaultLayout`, `h5SourceRoot`, `h5SiteRoot`, "
        "`h5SiteEntry=index.html`, `h5BuildCommand`, `appSlug`, `h5EntryUrl*` in 本包登记信息.json.\n"
        "- **Forbidden**: hand-editing `h5_site/` — use `h5/` + `dev.h5.build`.\n"
        "- **Forbidden**: declaring `h5SiteRoot` under Flutter `pubspec.yaml` assets.\n"
        f"{remote_block}"
    )


def persona_key(raw: str) -> str:
    return normalize_programming_style(raw) or "美国人"


def resolve_persona_layout(
    persona: str,
    *,
    prefix: str = "",
    lock: dict[str, Any] | None = None,
    theme_hint: str = "",
    include_tool_slots: bool = False,
) -> dict[str, Any]:
    """Return lib/asset layout keys and obfuscated asset roots for a persona."""
    key = persona_key(persona)
    lib_layout = LIB_LAYOUT_BY_PERSONA.get(key, "flat_skin_role")
    asset_layout = ASSET_LAYOUT_BY_PERSONA.get(key, "assets_images_flat")
    p = (prefix or "app").strip().lower()
    if not re.fullmatch(r"[a-z]{4,6}", p):
        p = "app"
    skin = skin_bucket_name(p, lib_layout)

    rule_key, _meta = _naming_from_lock_helper(lock) if lock else ("", None)
    if lock and rule_key:
        asset_part = resolve_asset_layout_from_lock(
            lock,
            asset_layout=asset_layout,
            theme_hint=theme_hint,
            include_tool_slots=include_tool_slots,
        )
        roots = asset_part["assetRoots"]
        slots = asset_part.get("assetSlots") or []
        naming_pattern = asset_part.get("assetNamingPattern") or ""
    else:
        roots = asset_pubspec_roots(asset_layout, p)
        slots = []
        naming_pattern = (
            "transform_identifier(entity=file|folder) when namingRuleMeta present"
        )

    return {
        "persona": key,
        "libLayout": lib_layout,
        "assetLayout": asset_layout,
        "skinBucket": skin,
        "assetRoots": roots,
        "assetSlots": slots,
        "assetNamingPattern": naming_pattern,
        "forbiddenAssetBasenames": sorted(FORBIDDEN_ASSET_BASENAMES),
    }


def _naming_from_lock_helper(lock: dict[str, Any]) -> tuple[str, Any]:
    from batch.naming import NamingMeta, meta_from_lock

    naming = lock.get("namingObfuscationRule") or {}
    meta_dict = naming.get("namingRuleMeta")
    meta = meta_from_lock(meta_dict if isinstance(meta_dict, dict) else None)
    rule_key = meta.rule_key or str(
        (meta_dict or {}).get("ruleKey") or ""
    ).strip()
    return rule_key, meta


def skin_bucket_name(prefix: str, lib_layout: str) -> str:
    if lib_layout == "shell_bay":
        return f"{prefix}_shell"
    return f"{prefix}_skin"


def asset_pubspec_roots(asset_layout: str, prefix: str) -> list[str]:
    mapping: dict[str, list[str]] = {
        "assets_images_flat": ["assets/images/"],
        "assets_media_split": ["assets/media/", "assets/media/icons/"],
        "assets_prefix_bundled": [f"assets/{prefix}/bundled/"],
        "assets_prefix_surfaces_glyphs": [
            f"assets/{prefix}/surfaces/",
            f"assets/{prefix}/glyphs/",
        ],
        "assets_img_flat": ["assets/img/"],
        "assets_prefix_panels_icons": [
            f"assets/{prefix}/panels/",
            f"assets/{prefix}/icons/",
        ],
        "assets_bundle_prefix": [
            f"assets/bundle/{prefix}/",
            f"assets/bundle/{prefix}/ui/",
            f"assets/bundle/{prefix}/tex/",
        ],
    }
    return mapping.get(asset_layout, ["assets/images/"])


def asset_naming_pattern(asset_layout: str, prefix: str) -> str:
    patterns = {
        "assets_images_flat": "{theme}_{purpose}.png",
        "assets_media_split": "{theme}_{purpose}.png under media/; icons under media/icons/",
        "assets_prefix_bundled": f"{{prefix}}_{{purpose}}_{{nn}}.png under assets/{prefix}/bundled/",
        "assets_prefix_surfaces_glyphs": f"{{prefix}}_{{surface|glyph}}_{{nn}}.png",
        "assets_img_flat": f"{{prefix}}{{nn}}.png under assets/img/",
        "assets_prefix_panels_icons": f"{{prefix}}_panel_{{nn}}.png / {{prefix}}_icon_{{nn}}.png",
        "assets_bundle_prefix": f"assets/bundle/{prefix}/ui/{{prefix}}_{{purpose}}.png",
    }
    return patterns.get(asset_layout, "{theme}_{purpose}.png").replace("{prefix}", prefix)


def _merge_h5_retry_slots_if_missing(
    lock: dict[str, Any],
    slots: list[Any],
    *,
    theme_hint: str = "",
) -> list[dict[str, Any]]:
    """Backfill h5_shell retry_illustration slot when lock predates PR-A."""
    ps = lock.get("programmingStyle") or {}
    if not isinstance(ps, dict) or not ps.get("h5VaultPattern"):
        return list(slots) if slots else []
    existing = [s for s in slots if isinstance(s, dict)]
    has_retry = any(
        str(s.get("role") or "").startswith("retry")
        or str(s.get("slot") or "").startswith("retry")
        for s in existing
    )
    if has_retry:
        return existing
    prefix = str((lock.get("namingObfuscationRule") or {}).get("dartCodePrefix") or "")
    rule_key, meta = _naming_from_lock_helper(lock)
    if not rule_key or not prefix:
        return existing
    from batch.asset_naming import build_h5_shell_retry_slots

    retry_slots = build_h5_shell_retry_slots(
        str(ps.get("assetLayout") or ""),
        rule_key=rule_key,
        meta=meta,
        prefix=prefix,
        theme_hint=theme_hint,
    )
    return existing + retry_slots


def layout_from_lock(lock: dict[str, Any] | None) -> dict[str, Any]:
    if not lock:
        return resolve_persona_layout("美国人")
    ps = lock.get("programmingStyle") or {}
    persona = ps.get("value") if isinstance(ps, dict) else str(ps or "")
    prefix = str((lock.get("namingObfuscationRule") or {}).get("dartCodePrefix") or "")
    theme = _theme_hint_from_workspace_lock(lock)
    fresh = resolve_persona_layout(
        str(persona or "美国人"),
        prefix=prefix,
        lock=lock,
        theme_hint=theme,
        include_tool_slots=bool(ps.get("assetSlots")),
    )
    if isinstance(ps, dict) and ps.get("libLayout"):
        merged = dict(fresh)
        merged["persona"] = ps.get("value") or fresh.get("persona")
        merged["libLayout"] = ps.get("libLayout")
        merged["assetLayout"] = ps.get("assetLayout")
        merged["skinBucket"] = ps.get("skinBucket")
        if ps.get("assetSlots"):
            merged["assetSlots"] = ps.get("assetSlots")
        merged["assetSlots"] = _merge_h5_retry_slots_if_missing(
            lock,
            merged.get("assetSlots") or [],
            theme_hint=theme,
        )
        # Deploy layout is always monolith — ignore stale h5_modular_* from old locks.
        if ps.get("h5VaultPattern") or ps.get("bundleEntryPath"):
            reg = lock.get("registration") or {}
            app_name = ""
            if isinstance(reg, dict):
                app_name = str(reg.get("appName") or reg.get("name") or "").strip()
            merged.update(
                resolve_h5_vault_layout(
                    str(persona or "美国人"),
                    prefix=prefix,
                    asset_layout=str(merged.get("assetLayout") or ""),
                    app_name=app_name,
                )
            )
        return merged
    fresh_slots = _merge_h5_retry_slots_if_missing(
        lock,
        fresh.get("assetSlots") or [],
        theme_hint=theme,
    )
    if fresh_slots != (fresh.get("assetSlots") or []):
        fresh = dict(fresh)
        fresh["assetSlots"] = fresh_slots
    return fresh


def _theme_hint_from_workspace_lock(lock: dict[str, Any]) -> str:
    reg = lock.get("registration") or {}
    if isinstance(reg, dict):
        for key in ("themeAngle", "mainFeature", "theme"):
            val = str(reg.get(key) or "").strip()
            if val:
                return val[:120]
    return ""


def enrich_programming_style_block(
    style: dict[str, Any],
    *,
    persona: str,
    prefix: str,
    lock: dict[str, Any] | None = None,
    theme_hint: str = "",
    include_tool_slots: bool = False,
    include_h5_vault: bool = False,
    app_name: str = "",
) -> dict[str, Any]:
    """Merge layout keys into programmingStyle section of dimension lock."""
    layout = resolve_persona_layout(
        persona,
        prefix=prefix,
        lock=lock,
        theme_hint=theme_hint,
        include_tool_slots=include_tool_slots,
    )
    out = dict(style)
    out.update(
        {
            "libLayout": layout["libLayout"],
            "assetLayout": layout["assetLayout"],
            "skinBucket": layout["skinBucket"],
            "assetRoots": layout["assetRoots"],
            "assetSlots": layout.get("assetSlots") or [],
            "assetNamingPattern": layout["assetNamingPattern"],
            "forbiddenAssetBasenames": layout["forbiddenAssetBasenames"],
        }
    )
    if include_h5_vault and prefix:
        name = (app_name or "").strip()
        if not name and isinstance(lock, dict):
            reg = lock.get("registration") or {}
            if isinstance(reg, dict):
                name = str(reg.get("appName") or reg.get("name") or "").strip()
        out.update(
            resolve_h5_vault_layout(
                persona,
                prefix=prefix,
                asset_layout=str(layout.get("assetLayout") or ""),
                app_name=name,
            )
        )
        rule_key, meta = _naming_from_lock_helper(lock) if lock else ("", None)
        if rule_key and meta is not None:
            from batch.asset_naming import build_h5_shell_retry_slots

            out["assetSlots"] = build_h5_shell_retry_slots(
                str(layout.get("assetLayout") or ""),
                rule_key=rule_key,
                meta=meta,
                prefix=prefix,
                theme_hint=theme_hint,
            )
    return out


def _read_theme_hint(workspace: Path) -> str:
    reg = workspace / "本包登记信息.json"
    if reg.is_file():
        try:
            data = json.loads(reg.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for key in ("themeAngle", "mainFeature", "theme"):
                    val = str(data.get(key) or "").strip()
                    if val:
                        return val[:120]
        except json.JSONDecodeError:
            pass
    return ""


def _workspace_has_content_list(workspace: Path) -> bool:
    path = workspace / "默认内容列表.json"
    if not path.is_file():
        return False
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return isinstance(items, list) and bool(items)


def refresh_tool_asset_manifest(workspace: Path, lock: dict[str, Any]) -> dict[str, Any]:
    """Fill assetSlots for tool packs and persist back to dimension lock."""
    from batch.dimension_lock import LOCK_FILE

    ps = lock.get("programmingStyle") or {}
    is_h5 = bool(ps.get("h5VaultPattern")) if isinstance(ps, dict) else False
    if _workspace_has_content_list(workspace) and not is_h5:
        return layout_from_lock(lock)

    persona = ps.get("value") if isinstance(ps, dict) else str(ps or "")
    prefix = str((lock.get("namingObfuscationRule") or {}).get("dartCodePrefix") or "")
    reg = lock.get("registration") or {}
    app_name = ""
    if isinstance(reg, dict):
        app_name = str(reg.get("appName") or reg.get("name") or "").strip()
    if not app_name:
        app_name = workspace.name.split("-")[0] if workspace.name else ""
    enriched = enrich_programming_style_block(
        ps if isinstance(ps, dict) else {"value": persona, "enforcement": "soft"},
        persona=str(persona),
        prefix=prefix,
        lock=lock,
        theme_hint=_read_theme_hint(workspace),
        include_tool_slots=not is_h5,
        include_h5_vault=is_h5,
        app_name=app_name,
    )
    lock = dict(lock)
    lock["programmingStyle"] = enriched
    (workspace / LOCK_FILE).write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return layout_from_lock(lock)


def write_resource_layout_manifest(workspace: Path, layout: dict[str, Any]) -> Path:
    path = workspace / RESOURCE_LAYOUT_FILE
    payload = {
        "libLayout": layout.get("libLayout"),
        "assetLayout": layout.get("assetLayout"),
        "skinBucket": layout.get("skinBucket"),
        "assetRoots": layout.get("assetRoots") or [],
        "assetSlots": layout.get("assetSlots") or [],
        "assetNamingPattern": layout.get("assetNamingPattern"),
        "forbiddenAssetBasenames": layout.get("forbiddenAssetBasenames") or [],
    }
    for key in (
        "h5VaultPattern",
        "h5VaultLayout",
        "bundleVaultDir",
        "bundleEntryPath",
        "h5VaultFiles",
    ):
        if layout.get(key):
            payload[key] = layout[key]
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def build_programming_layout_prompt_block(row: CsvTaskRow | None, *, prefix: str = "") -> str:
    if row is None:
        return ""
    layout = resolve_persona_layout(row.programming_style, prefix=prefix)
    lib_desc = _LIB_LAYOUT_DESC.get(layout["libLayout"], layout["libLayout"])
    asset_desc = _ASSET_LAYOUT_DESC.get(layout["assetLayout"], layout["assetLayout"])
    roots = ", ".join(f"`{r}`" for r in layout["assetRoots"])
    forbidden = ", ".join(layout["forbiddenAssetBasenames"][:4])
    return (
        "\n[CSV Programming Style — Layout (dims 6–7) — REQUIRED]\n"
        f"- libLayout: `{layout['libLayout']}` — {lib_desc}\n"
        f"- assetLayout: `{layout['assetLayout']}` — {asset_desc}\n"
        f"- skinBucket directory: `{layout['skinBucket']}/`\n"
        f"- pubspec asset roots (ONLY these): {roots}\n"
        f"- assetNamingPattern: {layout['assetNamingPattern']}\n"
        f"- FORBIDDEN basenames (never use): {forbidden}\n"
        "- Read 本包资源布局.json; all Image.asset paths MUST live under declared roots.\n"
    )


def role_implementation_subdir(prefix: str, role: str, lib_layout: str) -> str | None:
    """Optional subfolder under a role dir for business code."""
    if lib_layout == "nested_role_leaf":
        short = role.removesuffix("s") if role.endswith("s") else role
        return f"{prefix}_{short}_leaf"
    if lib_layout == "shell_bay":
        return f"{prefix}_bay"
    if lib_layout == "feature_mod_wrap":
        return f"{prefix}_mod_{role}"
    return None


_DUAL_HUB_CORE_ROLES = frozenset({"models", "entities"})


def apply_layout_topology_markers(
    flutter_root: Path,
    lock: dict[str, Any],
) -> list[str]:
    """Create persona-specific layout dirs (.gitkeep) without overwriting `.dart`."""
    from batch.scaffold_templates import lib_root_segment

    layout = layout_from_lock(lock)
    lib_layout = str(layout.get("libLayout") or "flat_skin_role")
    naming = lock.get("namingObfuscationRule") or {}
    prefix = str(naming.get("dartCodePrefix") or "").strip()
    dart_pkg = str(lock.get("dartPackageName") or "").strip()
    if not prefix or not dart_pkg:
        return []

    seg = lib_root_segment(prefix, dart_pkg)
    lib_root = flutter_root / "lib" / seg
    created: list[str] = []

    def touch_gitkeep(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        marker = path / ".gitkeep"
        if not marker.is_file():
            marker.write_text("")
        rel = path.relative_to(flutter_root).as_posix()
        if rel not in created:
            created.append(rel)

    if lib_layout == "flat_skin_role_helper":
        touch_gitkeep(lib_root / f"{prefix}_helper")
    if lib_layout == "single_lane":
        touch_gitkeep(lib_root / f"{prefix}_lane")
    if lib_layout == "shell_bay":
        touch_gitkeep(lib_root / f"{prefix}_shell")
    if lib_layout == "dual_hub":
        touch_gitkeep(lib_root / f"{prefix}_core")
        touch_gitkeep(lib_root / f"{prefix}_surface")

    folders = lock.get("architectureFolders") or {}
    for role, entry in folders.items():
        if not isinstance(entry, dict):
            continue
        folder_basename = entry.get("folderBasename") or f"{prefix}_{role}"
        if lib_layout == "dual_hub":
            hub = (
                f"{prefix}_core"
                if role in _DUAL_HUB_CORE_ROLES
                else f"{prefix}_surface"
            )
            role_dir = lib_root / hub / folder_basename
        else:
            role_dir = lib_root / folder_basename
        sub = role_implementation_subdir(prefix, role, lib_layout)
        if sub:
            touch_gitkeep(role_dir / sub)

    for root in layout.get("assetRoots") or []:
        touch_gitkeep(flutter_root / root.rstrip("/"))

    return created


def apply_layout_to_workspace(workspace: Path) -> dict[str, Any]:
    """Enrich dimension lock, resource manifest, pubspec assets, layout markers."""
    from batch.dimension_lock import LOCK_FILE, read_dimension_lock
    from batch.flutter_ops import find_flutter_project
    from batch.workspace import ensure_pubspec_assets

    lock = read_dimension_lock(workspace)
    if lock is None:
        raise ValueError(f"缺少 {LOCK_FILE}: {workspace}")

    naming = lock.get("namingObfuscationRule") or {}
    prefix = str(naming.get("dartCodePrefix") or "").strip()
    ps = lock.get("programmingStyle") or {}
    persona = ps.get("value") if isinstance(ps, dict) else str(ps or "")
    ps_block = lock.get("programmingStyle") or {}
    is_h5 = bool(ps_block.get("h5VaultPattern")) if isinstance(ps_block, dict) else False
    reg = lock.get("registration") or {}
    app_name = ""
    if isinstance(reg, dict):
        app_name = str(reg.get("appName") or reg.get("name") or "").strip()
    if not app_name:
        app_name = workspace.name.split("-")[0] if workspace.name else ""
    enriched = enrich_programming_style_block(
        ps if isinstance(ps, dict) else {"value": persona, "enforcement": "soft"},
        persona=str(persona),
        prefix=prefix,
        lock=lock,
        theme_hint=_read_theme_hint(workspace),
        include_tool_slots=not _workspace_has_content_list(workspace) and not is_h5,
        include_h5_vault=is_h5,
        app_name=app_name,
    )
    lock["programmingStyle"] = enriched
    (workspace / LOCK_FILE).write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    layout = refresh_tool_asset_manifest(workspace, lock)
    ps_block = lock.get("programmingStyle") or {}
    if isinstance(ps_block, dict):
        for key in (
            "h5VaultPattern",
            "h5VaultLayout",
            "bundleVaultDir",
            "bundleEntryPath",
            "h5VaultFiles",
        ):
            if ps_block.get(key):
                layout[key] = ps_block[key]
    write_resource_layout_manifest(workspace, layout)
    ensure_pubspec_assets(workspace)
    fp = find_flutter_project(workspace) or workspace
    markers = apply_layout_topology_markers(fp, lock)
    return {
        "persona": persona,
        "libLayout": layout.get("libLayout"),
        "assetLayout": layout.get("assetLayout"),
        "skinBucket": layout.get("skinBucket"),
        "assetRoots": layout.get("assetRoots") or [],
        "markersCreated": markers,
    }
