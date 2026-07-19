"""H5 Vite theme tokens — system light/dark via prefers-color-scheme."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

THEME_START = "/* THEME:pipeline — auto-synced; do not hand-edit */"
THEME_END = "/* THEME:end */"

_THEME_KEYS = (
    "primary",
    "secondary",
    "accent",
    "background",
    "foreground",
    "muted",
    "border",
    "destructive",
)

_LIGHT_DEFAULTS: dict[str, str] = {
    "background": "#F5F5F7",
    "foreground": "#0F172A",
    "muted": "#E8EAED",
    "border": "rgba(15, 23, 42, 0.12)",
    "card": "rgba(255, 255, 255, 0.94)",
    "sheet": "#FFFFFF",
    "on_muted": "#64748B",
    "ambient_a": "rgba(234, 88, 12, 0.12)",
    "ambient_b": "rgba(249, 115, 22, 0.08)",
    "ambient_c": "rgba(5, 150, 105, 0.08)",
    "ambient_ring": "rgba(234, 88, 12, 0.18)",
    "ambient_grid": "rgba(15, 23, 42, 0.06)",
    "ambient_scan": "rgba(5, 150, 105, 0.25)",
}


def _read_register(project: Path) -> dict[str, Any]:
    path = project / "本包登记信息.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def resolve_prefix(project: Path) -> str:
    reg = _read_register(project)
    anti = reg.get("codeAntiCorrelation") or {}
    if isinstance(anti, dict):
        prefix = str(anti.get("dartCodePrefix") or "").strip().lower()
        if prefix:
            return prefix
    from batch.workspace import dart_prefix

    return dart_prefix(project)


from batch.preview_tabs import preview_dir


def _has_preview_html(project: Path) -> bool:
    pdir = preview_dir(project)
    if not pdir.is_dir():
        return False
    return any(f.name.endswith("-tabs-preview.html") for f in pdir.iterdir())


def _load_candidate_colors(project: Path) -> dict[str, str]:
    preview_path = project / "skill-adapt" / "preview-approved-colors.json"
    if preview_path.is_file():
        try:
            data = json.loads(preview_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            colors = data.get("colors")
            if isinstance(colors, dict) and colors:
                return {str(k): str(v) for k, v in colors.items() if v}
            light = data.get("light")
            if isinstance(light, dict) and light:
                return {str(k): str(v) for k, v in light.items() if v}
            if any(k in data for k in ("primary", "background", "accent")):
                return {str(k): str(v) for k, v in data.items() if v and isinstance(v, str)}
    if _has_preview_html(project):
        return {}
    path = project / "skill-adapt" / "selected-candidate.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    colors = (data.get("designSystem") or {}).get("colors") or {}
    if not isinstance(colors, dict):
        return {}
    return {str(k): str(v) for k, v in colors.items() if v}


def _load_preview_dark_colors(project: Path) -> dict[str, str]:
    preview_path = project / "skill-adapt" / "preview-approved-colors.json"
    if not preview_path.is_file():
        return {}
    try:
        data = json.loads(preview_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    dark = data.get("dark")
    if isinstance(dark, dict) and dark:
        return {str(k): str(v) for k, v in dark.items() if v}
    return {}


def _preview_extras(colors: dict[str, str]) -> dict[str, str]:
    """Hero / tile / compare / dock tokens from preview-approved palette."""
    primary = colors.get("primary") or "#EA580C"
    accent = colors.get("accent") or "#059669"
    border = colors.get("border") or "#FED7AA"
    return {
        "hero_from": colors.get("hero-from") or colors.get("hero_from") or "#FB923C",
        "hero_to": colors.get("hero-to") or colors.get("hero_to") or primary,
        "tile_challenge": colors.get("tile-challenge") or "#EF4444",
        "tile_gift": colors.get("tile-gift") or "#F59E0B",
        "tile_trap": colors.get("tile-trap") or "#57534E",
        "tile_safe": colors.get("tile-safe") or "#22C55E",
        "tile_fate": colors.get("tile-fate") or "#A855F7",
        "tile_shop": colors.get("tile-shop") or "#3B82F6",
        "shadow_sm": "0 4px 14px rgba(67, 20, 7, 0.06)",
        "pill_bg": "rgba(255, 255, 255, 0.92)",
        "pill_border": border,
        "teal_soft": colors.get("teal-soft") or "#D1FAE5",
        "compare_a": colors.get("compare-a") or "#FFF7ED",
        "compare_b": colors.get("compare-b") or "#F0FDF4",
        "compare_border_a": colors.get("compare-border-a") or "#FDBA74",
        "compare_border_b": colors.get("compare-border-b") or "#6EE7B7",
        "stripe_a": colors.get("stripe-a") or primary,
        "stripe_b": colors.get("stripe-b") or accent,
        "stripe_c": colors.get("stripe-c") or "#D97706",
        "section_label": colors.get("section-label") or "#78716C",
        "tab_inactive": colors.get("tab-inactive") or "#A8A29E",
        "game_pop": "3px 3px 0 rgba(67, 20, 7, 0.14)",
        "game_pop_lg": "4px 4px 0 rgba(67, 20, 7, 0.2)",
        "border_soft": colors.get("border-soft") or border,
        "fg_soft": colors.get("fg-soft") or "#7C2D12",
    }


def _dark_palette(colors: dict[str, str], *, preview_dark: dict[str, str] | None = None) -> dict[str, str]:
    src = {**colors, **(preview_dark or {})}
    bg = src.get("background") or "#0F172A"
    fg = src.get("foreground") or src.get("text") or "#FFFFFF"
    muted = src.get("muted") or "#2A2636"
    border = src.get("border") or "rgba(255, 255, 255, 0.14)"
    base = {
        "primary": src.get("primary") or "#2563EB",
        "secondary": src.get("secondary") or src.get("primary") or "#3B82F6",
        "accent": src.get("accent") or src.get("cta") or src.get("primary") or "#2563EB",
        "background": bg,
        "foreground": fg,
        "muted": muted,
        "border": border,
        "destructive": src.get("destructive") or "#DC2626",
        "card": src.get("card") or "rgba(22, 30, 48, 0.88)",
        "sheet": src.get("sheet") or "rgba(32, 28, 39, 0.92)",
        "on_muted": src.get("on-muted") or src.get("on_muted") or "#CBD5E1",
        "ambient_a": "rgba(234, 88, 12, 0.22)",
        "ambient_b": "rgba(249, 115, 22, 0.14)",
        "ambient_c": "rgba(5, 150, 105, 0.10)",
        "ambient_ring": "rgba(234, 88, 12, 0.28)",
        "ambient_grid": "rgba(255, 255, 255, 0.08)",
        "ambient_scan": "rgba(5, 150, 105, 0.35)",
    }
    base.update(_preview_extras(src))
    return base


def _on_primary_color(accent: str) -> str:
    """Readable label color on accent-filled buttons."""
    return "#0F172A" if _is_light_hex(accent) else "#FFFFFF"


def _apply_semantic_tokens(light: dict[str, str], dark: dict[str, str]) -> None:
    """Long-form CSS var aliases + ambient/on-primary semantics."""
    on_ambient = dark["foreground"]
    for palette in (light, dark):
        palette["on_ambient"] = on_ambient
        palette["on_primary"] = _on_primary_color(palette["accent"])


def _is_light_hex(hex_color: str) -> bool:
    val = hex_color.lstrip("#")
    if len(val) == 3:
        val = "".join(c * 2 for c in val)
    if len(val) != 6:
        return False
    try:
        r, g, b = int(val[0:2], 16), int(val[2:4], 16), int(val[4:6], 16)
    except ValueError:
        return False
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance > 0.55


def _light_palette(colors: dict[str, str], dark: dict[str, str]) -> dict[str, str]:
    light = dict(_LIGHT_DEFAULTS)
    light["primary"] = colors.get("primary") or dark["primary"]
    light["secondary"] = colors.get("secondary") or dark["secondary"]
    light["accent"] = colors.get("accent") or dark["accent"]
    light["destructive"] = dark["destructive"]
    bg = str(colors.get("background") or "")
    if bg.startswith("#") and _is_light_hex(bg):
        light["background"] = bg
    fg = str(colors.get("foreground") or "")
    if fg.startswith("#"):
        light["foreground"] = fg
    else:
        light["foreground"] = "#431407"
    if colors.get("muted"):
        light["muted"] = str(colors["muted"])
    if colors.get("border"):
        light["border"] = str(colors["border"])
    if colors.get("card"):
        light["card"] = str(colors["card"])
    if colors.get("sheet"):
        light["sheet"] = str(colors["sheet"])
    light.update(_preview_extras({**dark, **colors}))
    return light


def _css_var_lines(prefix: str, palette: dict[str, str]) -> list[str]:
    p = prefix.lower()
    mapping = {
        f"--{p}-primary": palette["primary"],
        f"--{p}-secondary": palette["secondary"],
        f"--{p}-accent": palette["accent"],
        f"--{p}-bg": palette["background"],
        f"--{p}-fg": palette["foreground"],
        f"--{p}-background": palette["background"],
        f"--{p}-foreground": palette["foreground"],
        f"--{p}-on-primary": palette.get("on_primary", "#FFFFFF"),
        f"--{p}-on-ambient": palette.get("on_ambient", palette["foreground"]),
        f"--{p}-muted": palette["muted"],
        f"--{p}-on-muted": palette["on_muted"],
        f"--{p}-destructive": palette["destructive"],
        f"--{p}-border": palette["border"],
        f"--{p}-card": palette["card"],
        f"--{p}-sheet": palette["sheet"],
        f"--{p}-ambient-a": palette["ambient_a"],
        f"--{p}-ambient-b": palette["ambient_b"],
        f"--{p}-ambient-c": palette["ambient_c"],
        f"--{p}-ambient-ring": palette["ambient_ring"],
        f"--{p}-ambient-grid": palette["ambient_grid"],
        f"--{p}-ambient-scan": palette["ambient_scan"],
        f"--{p}-hero-from": palette.get("hero_from", palette["primary"]),
        f"--{p}-hero-to": palette.get("hero_to", palette["primary"]),
        f"--{p}-tile-challenge": palette.get("tile_challenge", "#EF4444"),
        f"--{p}-tile-gift": palette.get("tile_gift", "#F59E0B"),
        f"--{p}-tile-trap": palette.get("tile_trap", "#57534E"),
        f"--{p}-tile-safe": palette.get("tile_safe", "#22C55E"),
        f"--{p}-tile-fate": palette.get("tile_fate", "#A855F7"),
        f"--{p}-tile-shop": palette.get("tile_shop", "#3B82F6"),
        f"--{p}-shadow-sm": palette.get("shadow_sm", "0 4px 14px rgba(0,0,0,0.08)"),
        f"--{p}-pill-bg": palette.get("pill_bg", "rgba(255,255,255,0.92)"),
        f"--{p}-pill-border": palette.get("pill_border", palette["border"]),
        f"--{p}-teal-soft": palette.get("teal_soft", "#D1FAE5"),
        f"--{p}-compare-a": palette.get("compare_a", "#FFF7ED"),
        f"--{p}-compare-b": palette.get("compare_b", "#F0FDF4"),
        f"--{p}-compare-border-a": palette.get("compare_border_a", "#FDBA74"),
        f"--{p}-compare-border-b": palette.get("compare_border_b", "#6EE7B7"),
        f"--{p}-stripe-a": palette.get("stripe_a", palette["primary"]),
        f"--{p}-stripe-b": palette.get("stripe_b", palette["accent"]),
        f"--{p}-stripe-c": palette.get("stripe_c", "#D97706"),
        f"--{p}-section-label": palette.get("section_label", "#78716C"),
        f"--{p}-tab-inactive": palette.get("tab_inactive", "#A8A29E"),
        f"--{p}-game-pop": palette.get("game_pop", "3px 3px 0 rgba(67,20,7,0.14)"),
        f"--{p}-game-pop-lg": palette.get("game_pop_lg", "4px 4px 0 rgba(67,20,7,0.2)"),
        f"--{p}-border-soft": palette.get("border_soft", palette["border"]),
        f"--{p}-fg-soft": palette.get("fg_soft", palette["foreground"]),
    }
    return [f"  {k}: {v};" for k, v in mapping.items()]


def build_theme_block(prefix: str, colors: dict[str, str] | None = None, *, project: Path | None = None) -> str:
    colors = colors or {}
    preview_dark = _load_preview_dark_colors(project) if project else {}
    dark = _dark_palette(colors, preview_dark=preview_dark or None)
    light = _light_palette(colors, dark)
    _apply_semantic_tokens(light, dark)
    lines = [
        THEME_START,
        ":root {",
        "  color-scheme: light dark;",
        *_css_var_lines(prefix, light),
        "}",
        "",
        "@media (prefers-color-scheme: dark) {",
        "  :root {",
        *_css_var_lines(prefix, dark),
        "  }",
        "}",
        THEME_END,
    ]
    return "\n".join(lines)


def _strip_orphan_theme_comments(css: str) -> str:
    lines: list[str] = []
    in_block = False
    for line in css.splitlines():
        if THEME_START in line:
            in_block = True
            lines.append(line)
            continue
        if THEME_END in line:
            in_block = False
            lines.append(line)
            continue
        if "/* THEME:pipeline" in line and not in_block:
            continue
        lines.append(line)
    return "\n".join(lines) + ("\n" if css.endswith("\n") else "")


def _replace_theme_block(css: str, block: str) -> str:
    pattern = re.compile(
        re.escape(THEME_START) + r"[\s\S]*?" + re.escape(THEME_END),
        re.MULTILINE,
    )
    if pattern.search(css):
        cleaned = pattern.sub("", css)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).lstrip("\n")
        return block + "\n\n" + cleaned

    root_match = re.search(r":root\s*\{", css)
    if root_match:
        start = root_match.start()
        depth = 0
        i = root_match.end() - 1
        while i < len(css):
            ch = css[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return css[:start] + block + css[i + 1 :]
            i += 1
    return block + "\n\n" + css


def _ensure_static_root_vars(css: str, prefix: str) -> str:
    p = prefix.lower()
    needed = {
        f"--{p}-font-display": "'Calistoga', serif",
        f"--{p}-font-body": "'Inter', system-ui, sans-serif",
        f"--{p}-font-mono": "'JetBrains Mono', monospace",
        f"--{p}-radius-md": "12px",
        f"--{p}-radius-lg": "16px",
        "--safe-top": "env(safe-area-inset-top, 0px)",
        "--safe-bottom": "env(safe-area-inset-bottom, 0px)",
    }
    missing = [k for k in needed if k not in css]
    if not missing:
        return css
    lines = [":root {"]
    for key in missing:
        lines.append(f"  {key}: {needed[key]};")
    lines.append("}")
    block = "\n".join(lines)
    if THEME_END in css:
        return css.replace(THEME_END, f"{THEME_END}\n\n{block}", 1)
    return css + "\n\n" + block


def sync_h5_global_theme(project: Path, *, write: bool = True) -> Path | None:
    """Inject dual-theme :root block into h5/src/styles/global.css."""
    project = project.expanduser().resolve()
    css_path = project / "h5" / "src" / "styles" / "global.css"
    if not css_path.is_file():
        return None
    prefix = resolve_prefix(project)
    colors = _load_candidate_colors(project)
    block = build_theme_block(prefix, colors, project=project)
    raw = css_path.read_text(encoding="utf-8")
    updated = _replace_theme_block(raw, block)
    updated = _strip_orphan_theme_comments(updated)
    updated = _ensure_static_root_vars(updated, prefix)
    if write and updated != raw:
        css_path.write_text(updated, encoding="utf-8")
    if write and css_path.is_file():
        text = css_path.read_text(encoding="utf-8")
        if ".h5-app-shell" not in text:
            shell = (
                "\n.h5-app-shell {\n"
                "  position: relative;\n"
                "  z-index: 1;\n"
                "  min-height: 100vh;\n"
                "  isolation: isolate;\n"
                "}\n"
            )
            css_path.write_text(text.rstrip() + shell, encoding="utf-8")
    from batch.h5_layout_contract import sync_h5_layout_contract

    sync_h5_layout_contract(project, write=write)
    return css_path


def verify_h5_theme_system(project: Path) -> list[str]:
    issues: list[str] = []
    css_path = project / "h5" / "src" / "styles" / "global.css"
    if not css_path.is_file():
        return issues
    css = css_path.read_text(encoding="utf-8", errors="ignore")
    if css.count(THEME_START) > 1:
        issues.append("UX Gate: global.css 存在重复 THEME:pipeline 块")
    orphan_comments = [
        ln for ln in css.splitlines()
        if "/* THEME:pipeline" in ln and THEME_START not in ln
    ]
    if orphan_comments:
        issues.append("UX Gate: global.css 存在游离 THEME:pipeline 注释（须仅一块 auto-synced）")
    if "color-scheme: light dark" not in css.replace(" ", "") and "color-scheme:lightdark" not in css.replace(" ", ""):
        issues.append("UX Gate: global.css 缺少 color-scheme: light dark（须跟随系统深浅色）")
    if not re.search(r"@media\s*\(\s*prefers-color-scheme:\s*dark\s*\)", css, re.I):
        issues.append("UX Gate: global.css 缺少 @media (prefers-color-scheme: dark) token 块")
    if ".h5-app-shell" not in css and "h5-app-shell" not in css:
        issues.append("UX Gate: 缺少 .h5-app-shell 内容层（Ambient 可能遮挡 Welcome）")
    prefix = resolve_prefix(project).lower()
    if prefix:
        theme_slice = css
        if THEME_START in css and THEME_END in css:
            theme_slice = css.split(THEME_START, 1)[1].split(THEME_END, 1)[0]
        for alias in ("background", "foreground", "on-primary", "on-ambient"):
            token = f"--{prefix}-{alias}"
            if token not in theme_slice:
                issues.append(f"UX Gate: THEME 块缺少 {token}（须与 --{prefix}-bg/--{prefix}-fg 同步别名）")
    from batch.preview_fidelity_gate import verify_preview_theme_drift

    issues.extend(verify_preview_theme_drift(project))
    return issues
