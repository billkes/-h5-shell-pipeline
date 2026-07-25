"""Obfuscated asset roots and filenames via per-name naming transform."""

from __future__ import annotations

from typing import Any

from batch.naming import NamingMeta, meta_from_lock, transform_identifier

# Standard tool-pack raster slots (downloaded in Phase 3).
TOOL_ASSET_SLOT_SEMANTICS: list[tuple[str, str]] = [
    ("tab_scene_alpha", "tab backdrop lifestyle minimal person"),
    ("tab_scene_beta", "interior decor aesthetic person"),
    ("tab_scene_gamma", "workspace mood soft person"),
    ("root_grain_layer", "abstract soft texture minimal"),
    ("welcome_hero_plane", "welcome hero lifestyle soft person"),
    ("empty_state_mark", "empty state minimal illustration"),
]

_CONTENT_FILE_SEMANTIC = "content_tile"


def _naming_from_lock(lock: dict[str, Any] | None) -> tuple[str, NamingMeta]:
    if not lock:
        return "", NamingMeta(rule_key="")
    naming = lock.get("namingObfuscationRule") or {}
    meta_dict = naming.get("namingRuleMeta")
    meta = meta_from_lock(meta_dict if isinstance(meta_dict, dict) else None)
    rule_key = meta.rule_key or str(
        (meta_dict or {}).get("ruleKey") or ""
    ).strip()
    return rule_key, meta


def _segment_folder(
    *,
    rule_key: str,
    meta: NamingMeta,
    semantic: str,
    salt: str,
) -> str:
    return transform_identifier(
        rule_key=rule_key,
        meta=meta,
        entity="folder",
        semantic=semantic,
        salt=salt,
    )


def _segment_file(
    *,
    rule_key: str,
    meta: NamingMeta,
    semantic: str,
    salt: str,
) -> str:
    return transform_identifier(
        rule_key=rule_key,
        meta=meta,
        entity="file",
        semantic=semantic,
        salt=salt,
    )


def obfuscated_asset_roots(
    asset_layout: str,
    *,
    rule_key: str,
    meta: NamingMeta,
) -> list[str]:
    """Pubspec asset roots with obfuscated folder names (no English ``images/``)."""
    def f(semantic: str, salt: str) -> str:
        return _segment_folder(
            rule_key=rule_key,
            meta=meta,
            semantic=semantic,
            salt=salt,
        )

    if asset_layout == "assets_images_flat":
        return [f"assets/{f('raster_vault', 'root')}/"]
    if asset_layout == "assets_media_split":
        return [
            f"assets/{f('media_raster', 'a')}/",
            f"assets/{f('media_glyph', 'b')}/",
        ]
    if asset_layout == "assets_prefix_bundled":
        return [f"assets/{f('bundled_vault', 'a')}/"]
    if asset_layout == "assets_prefix_surfaces_glyphs":
        return [
            f"assets/{f('surface_raster', 'a')}/",
            f"assets/{f('glyph_raster', 'b')}/",
        ]
    if asset_layout == "assets_img_flat":
        return [f"assets/{f('img_lane', 'a')}/"]
    if asset_layout == "assets_prefix_panels_icons":
        return [
            f"assets/{f('panel_raster', 'a')}/",
            f"assets/{f('icon_raster', 'b')}/",
        ]
    if asset_layout == "assets_bundle_prefix":
        root = f("bundle_root", "a")
        ui = f("bundle_ui_lane", "b")
        tex = f("bundle_tex_lane", "c")
        return [
            f"assets/{root}/",
            f"assets/{root}/{ui}/",
            f"assets/{root}/{tex}/",
        ]
    return [f"assets/{f('raster_vault', 'root')}/"]


def _primary_raster_root(asset_layout: str, roots: list[str]) -> str:
    if not roots:
        return "assets/raster/"
    if asset_layout in {
        "assets_media_split",
        "assets_prefix_surfaces_glyphs",
        "assets_prefix_panels_icons",
    }:
        return roots[0]
    return roots[0]


def _glyph_root(asset_layout: str, roots: list[str]) -> str | None:
    if asset_layout in {
        "assets_media_split",
        "assets_prefix_surfaces_glyphs",
        "assets_prefix_panels_icons",
    } and len(roots) > 1:
        return roots[1]
    return None


def build_h5_shell_raster_slots(
    asset_layout: str,
    *,
    rule_key: str,
    meta: NamingMeta,
    prefix: str,
    theme_hint: str = "",
) -> list[dict[str, str]]:
    """Fixed shell raster slots for h5_shell (logo / launch×2 / bg×2 / retry)."""
    roots = obfuscated_asset_roots(asset_layout, rule_key=rule_key, meta=meta)
    primary = _primary_raster_root(asset_layout, roots)
    p = (prefix or "app").strip().lower()
    theme = (theme_hint or "brand motif soft").strip()
    base = primary.rstrip("/")

    def _slot(
        slot: str,
        role: str,
        fname: str,
        keyword: str,
        description: str,
        size: str,
    ) -> dict[str, str]:
        return {
            "slot": slot,
            "role": role,
            "path": f"{base}/{fname}",
            "keyword": keyword[:80],
            "description": description,
            "recommendedSize": size,
        }

    return [
        _slot(
            "logo",
            "logo",
            f"{p}_brand_logo.png",
            f"{theme} app logo mark minimal",
            "Brand logo mark for shell chrome / Welcome",
            "1024×1024",
        ),
        _slot(
            "launch_light",
            "splash_background",
            f"{p}_launch_light.png",
            f"{theme} light launch splash full-bleed",
            "iOS LaunchScreen / LaunchVeil light appearance (1125×2436)",
            "1125×2436",
        ),
        _slot(
            "launch_dark",
            "splash_background",
            f"{p}_launch_dark.png",
            f"{theme} dark launch splash full-bleed",
            "iOS LaunchScreen / LaunchVeil dark appearance (1125×2436)",
            "1125×2436",
        ),
        _slot(
            "global_bg_light",
            "global_background",
            f"{p}_global_bg_light.png",
            f"{theme} light ambient global background",
            "Light-theme full-bleed global background for H5 ambient",
            "1242×2688",
        ),
        _slot(
            "global_bg_dark",
            "global_background",
            f"{p}_global_bg_dark.png",
            f"{theme} dark ambient global background",
            "Dark-theme full-bleed global background for H5 ambient",
            "1242×2688",
        ),
        _slot(
            "retry_illustration",
            "retry_error",
            f"{p}_panel_retry_offline.png",
            f"{theme} offline retry illustration soft",
            "WebView load error fallback illustration",
            "320×240",
        ),
    ]


def build_h5_shell_retry_slots(
    asset_layout: str,
    *,
    rule_key: str,
    meta: NamingMeta,
    prefix: str,
    theme_hint: str = "",
) -> list[dict[str, str]]:
    """Alias — H5 shell now ships the full raster slot set (includes retry)."""
    return build_h5_shell_raster_slots(
        asset_layout,
        rule_key=rule_key,
        meta=meta,
        prefix=prefix,
        theme_hint=theme_hint,
    )


def build_tool_asset_slots(
    asset_layout: str,
    *,
    rule_key: str,
    meta: NamingMeta,
    theme_hint: str = "",
) -> list[dict[str, str]]:
    """Return slot manifest for tool_flutter downloads."""
    roots = obfuscated_asset_roots(asset_layout, rule_key=rule_key, meta=meta)
    primary = _primary_raster_root(asset_layout, roots)
    glyph = _glyph_root(asset_layout, roots)
    theme = (theme_hint or "lifestyle minimal").strip()
    slots: list[dict[str, str]] = []
    for idx, (semantic, kw_base) in enumerate(TOOL_ASSET_SLOT_SEMANTICS):
        root = glyph if glyph and idx >= 4 else primary
        fname = _segment_file(
            rule_key=rule_key,
            meta=meta,
            semantic=semantic,
            salt=f"tool{idx}",
        )
        rel = f"{root.rstrip('/')}/{fname}.png"
        keyword = f"{theme} {kw_base}".strip()
        slots.append(
            {
                "slot": semantic,
                "path": rel,
                "keyword": keyword[:80],
            }
        )
    return slots


def build_content_asset_filename(
    *,
    rule_key: str,
    meta: NamingMeta,
    item_id: str | int,
) -> str:
    """Obfuscated contentpack / videostream raster filename."""
    base = _segment_file(
        rule_key=rule_key,
        meta=meta,
        semantic=_CONTENT_FILE_SEMANTIC,
        salt=str(item_id),
    )
    return f"{base}.png"


def resolve_asset_layout_from_lock(
    lock: dict[str, Any],
    *,
    asset_layout: str,
    theme_hint: str = "",
    include_tool_slots: bool = False,
) -> dict[str, Any]:
    """Merge obfuscated roots + optional tool slot manifest."""
    rule_key, meta = _naming_from_lock(lock)
    if not rule_key:
        from batch.programming_layout import asset_pubspec_roots

        prefix = str(
            (lock.get("namingObfuscationRule") or {}).get("dartCodePrefix") or ""
        )
        return {
            "assetRoots": asset_pubspec_roots(asset_layout, prefix),
            "assetSlots": [],
            "assetNamingPattern": "legacy — naming meta missing",
        }

    roots = obfuscated_asset_roots(asset_layout, rule_key=rule_key, meta=meta)
    out: dict[str, Any] = {
        "assetRoots": roots,
        "assetNamingPattern": (
            "Each raster file: transform_identifier(entity=file, semantic=<slot>, "
            "salt=<slotId>).png under declared assetRoots only."
        ),
        "assetSlots": [],
    }
    if include_tool_slots:
        out["assetSlots"] = build_tool_asset_slots(
            asset_layout,
            rule_key=rule_key,
            meta=meta,
            theme_hint=theme_hint,
        )
    return out


def asset_naming_prompt_block(lock: dict[str, Any] | None) -> str:
    """Short Agent block: assets follow naming transform, not English paths."""
    if not lock:
        return ""
    rule_key, meta = _naming_from_lock(lock)
    if not rule_key:
        return ""
    sample_folder = _segment_folder(
        rule_key=rule_key,
        meta=meta,
        semantic="raster_vault",
        salt="prompt",
    )
    sample_file = _segment_file(
        rule_key=rule_key,
        meta=meta,
        semantic="tab_scene_alpha",
        salt="prompt",
    )
    return (
        "\n[Asset Naming — REQUIRED]\n"
        "- Asset **directories and filenames** use the same per-name "
        "`transform_identifier()` as `lib/` code (entity `folder` / `file`).\n"
        "- Do NOT create `assets/images/`, `splash_background.png`, or other "
        "plain-English asset paths unless listed in 本包资源布局.json.\n"
        f"- Example folder segment: `assets/{sample_folder}/`\n"
        f"- Example file: `{sample_file}.png`\n"
        "- Use only paths in 本包资源布局.json → assetRoots / assetSlots.\n"
    )
