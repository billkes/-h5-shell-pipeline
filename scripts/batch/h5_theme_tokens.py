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


def _load_candidate_colors(project: Path) -> dict[str, str]:
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


def _dark_palette(colors: dict[str, str]) -> dict[str, str]:
    bg = colors.get("background") or "#0F172A"
    fg = colors.get("foreground") or colors.get("text") or "#FFFFFF"
    muted = colors.get("muted") or "#2A2636"
    border = colors.get("border") or "rgba(255, 255, 255, 0.14)"
    return {
        "primary": colors.get("primary") or "#2563EB",
        "secondary": colors.get("secondary") or colors.get("primary") or "#3B82F6",
        "accent": colors.get("accent") or colors.get("cta") or colors.get("primary") or "#2563EB",
        "background": bg,
        "foreground": fg,
        "muted": muted,
        "border": border,
        "destructive": colors.get("destructive") or "#DC2626",
        "card": "rgba(22, 30, 48, 0.88)",
        "sheet": "rgba(32, 28, 39, 0.92)",
        "on_muted": "#CBD5E1",
        "ambient_a": "rgba(234, 88, 12, 0.22)",
        "ambient_b": "rgba(249, 115, 22, 0.14)",
        "ambient_c": "rgba(5, 150, 105, 0.10)",
        "ambient_ring": "rgba(234, 88, 12, 0.28)",
        "ambient_grid": "rgba(255, 255, 255, 0.08)",
        "ambient_scan": "rgba(5, 150, 105, 0.35)",
    }


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
    light["primary"] = dark["primary"]
    light["secondary"] = dark["secondary"]
    light["accent"] = dark["accent"]
    light["destructive"] = dark["destructive"]
    bg = str(colors.get("background") or "")
    if bg.startswith("#") and _is_light_hex(bg):
        light["background"] = bg
    light["foreground"] = "#0F172A"
    return light


def _css_var_lines(prefix: str, palette: dict[str, str]) -> list[str]:
    p = prefix.lower()
    mapping = {
        f"--{p}-primary": palette["primary"],
        f"--{p}-secondary": palette["secondary"],
        f"--{p}-accent": palette["accent"],
        f"--{p}-bg": palette["background"],
        f"--{p}-fg": palette["foreground"],
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
    }
    return [f"  {k}: {v};" for k, v in mapping.items()]


def build_theme_block(prefix: str, colors: dict[str, str] | None = None) -> str:
    colors = colors or {}
    dark = _dark_palette(colors)
    light = _light_palette(colors, dark)
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


def _replace_theme_block(css: str, block: str) -> str:
    if THEME_START in css and THEME_END in css:
        pattern = re.compile(
            re.escape(THEME_START) + r"[\s\S]*?" + re.escape(THEME_END),
            re.MULTILINE,
        )
        return pattern.sub(block, css, count=1)

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
        f"--{p}-font-display": "'Syncopate', sans-serif",
        f"--{p}-font-body": "'Space Mono', monospace",
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
    block = build_theme_block(prefix, colors)
    raw = css_path.read_text(encoding="utf-8")
    updated = _replace_theme_block(raw, block)
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
    if "color-scheme: light dark" not in css.replace(" ", "") and "color-scheme:lightdark" not in css.replace(" ", ""):
        issues.append("UX Gate: global.css 缺少 color-scheme: light dark（须跟随系统深浅色）")
    if not re.search(r"@media\s*\(\s*prefers-color-scheme:\s*dark\s*\)", css, re.I):
        issues.append("UX Gate: global.css 缺少 @media (prefers-color-scheme: dark) token 块")
    if ".h5-app-shell" not in css and "h5-app-shell" not in css:
        issues.append("UX Gate: 缺少 .h5-app-shell 内容层（Ambient 可能遮挡 Welcome）")
    return issues
