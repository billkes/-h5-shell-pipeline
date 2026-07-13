"""Native launch veil + retry UI — themed light/dark from H5 design tokens."""

from __future__ import annotations

import json
import re
from pathlib import Path

TEMPLATE_HOST = (
    Path(__file__).resolve().parents[2]
    / "data/static/templates/oc_shell/{{APP_NAME}}/{{APP_NAME}}/{{PREFIX_CAP}}HostController.m"
)

_CSS_VAR_RE = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;]+);", re.I)
_RGBA_RE = re.compile(
    r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)",
    re.I,
)

_DEFAULT_DARK = {
    "bg": "#0F172A",
    "fg": "#FFFFFF",
    "sheet": "#201C27",
    "on_muted": "#CBD5E1",
    "primary": "#EA580C",
    "accent": "#059669",
    "scrim_a": "0.72",
    "gauge_track_a": "0.12",
}

_DEFAULT_LIGHT = {
    "bg": "#F5F5F7",
    "fg": "#0F172A",
    "sheet": "#FFFFFF",
    "on_muted": "#64748B",
    "primary": "#EA580C",
    "accent": "#059669",
    "scrim_a": "0.45",
    "gauge_track_a": "0.14",
}

_GENERIC_MARKERS = (
    "Connection issue",
    "BrandPink",
    "VeilSpinner",
    "VeilHud",
    "colorWithRed:0.925 green:0.286 blue:0.600",
    "colorWithRed:0.486 green:0.227 blue:0.929",
)


def _hex_to_rgb_float(hex_color: str) -> tuple[float, float, float]:
    h = (hex_color or "").strip().lstrip("#")
    if len(h) != 6:
        return 0.0, 0.0, 0.0
    return int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0


def _parse_color(value: str) -> tuple[float, float, float, float]:
    raw = (value or "").strip()
    if raw.startswith("#") and len(raw) >= 7:
        r, g, b = _hex_to_rgb_float(raw[:7])
        return r, g, b, 1.0
    match = _RGBA_RE.match(raw)
    if match:
        r, g, b = float(match.group(1)), float(match.group(2)), float(match.group(3))
        a = float(match.group(4)) if match.group(4) is not None else 1.0
        if r > 1 or g > 1 or b > 1:
            r, g, b = r / 255.0, g / 255.0, b / 255.0
        return r, g, b, a
    return 0.0, 0.0, 0.0, 1.0


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _prefix_cap(prefix: str) -> str:
    p = (prefix or "").strip()
    if not p:
        return "App"
    return p[0].upper() + p[1:]


def resolve_prefix(workspace: Path) -> str:
    reg = _read_json(workspace / "本包登记信息.json")
    anti = reg.get("codeAntiCorrelation") or {}
    if isinstance(anti, dict):
        p = str(anti.get("dartCodePrefix") or "").strip()
        if p:
            return p
    return ""


def _parse_h5_theme_tokens(css_text: str, prefix: str) -> tuple[dict[str, str], dict[str, str]]:
    light: dict[str, str] = {}
    dark: dict[str, str] = {}
    p = prefix.lower()

    root_match = re.search(r":root\s*\{([^}]+)\}", css_text, re.S)
    if root_match:
        for key, val in _CSS_VAR_RE.findall(root_match.group(1)):
            if key.startswith(f"{p}-"):
                light[key[len(p) + 1 :].replace("-", "_")] = val.strip()

    dark_block = re.search(
        r"@media\s*\(\s*prefers-color-scheme:\s*dark\s*\)\s*\{[^{]*:root\s*\{([^}]+)\}",
        css_text,
        re.S | re.I,
    )
    if dark_block:
        for key, val in _CSS_VAR_RE.findall(dark_block.group(1)):
            if key.startswith(f"{p}-"):
                dark[key[len(p) + 1 :].replace("-", "_")] = val.strip()
    return light, dark


def _theme_bundle(raw: dict[str, str], defaults: dict[str, str]) -> dict[str, str]:
    return {
        "bg": raw.get("bg") or defaults["bg"],
        "fg": raw.get("fg") or defaults["fg"],
        "sheet": raw.get("sheet") or defaults["sheet"],
        "on_muted": raw.get("on_muted") or defaults["on_muted"],
        "primary": raw.get("primary") or defaults["primary"],
        "accent": raw.get("accent") or defaults["accent"],
        "scrim_a": defaults["scrim_a"],
        "gauge_track_a": defaults["gauge_track_a"],
    }


def _resolve_themes(workspace: Path, prefix: str) -> tuple[dict[str, str], dict[str, str]]:
    css_path = workspace / "h5" / "src" / "styles" / "global.css"
    if css_path.is_file():
        light_raw, dark_raw = _parse_h5_theme_tokens(css_path.read_text(encoding="utf-8"), prefix)
        if light_raw or dark_raw:
            light = _theme_bundle(light_raw, _DEFAULT_LIGHT)
            dark = _theme_bundle(dark_raw or light_raw, _DEFAULT_DARK)
            if not dark_raw:
                dark = _theme_bundle(
                    {
                        "bg": _DEFAULT_DARK["bg"],
                        "fg": _DEFAULT_DARK["fg"],
                        "sheet": "rgba(32,28,39,0.88)",
                        "on_muted": _DEFAULT_DARK["on_muted"],
                        "primary": light.get("primary", _DEFAULT_DARK["primary"]),
                        "accent": light.get("accent", _DEFAULT_DARK["accent"]),
                    },
                    _DEFAULT_DARK,
                )
            return light, dark

    lock = _read_json(workspace / "本包视觉锁.json")
    tokens = lock.get("colorTokens") if isinstance(lock.get("colorTokens"), dict) else {}
    overrides = lock.get("packageTokenOverrides") if isinstance(lock.get("packageTokenOverrides"), dict) else {}
    dark = _theme_bundle(
        {
            "bg": str(tokens.get("backgroundDark") or overrides.get("--uhfnf-bg-dark") or _DEFAULT_DARK["bg"]),
            "fg": str(tokens.get("onSurface") or _DEFAULT_DARK["fg"]),
            "sheet": str(tokens.get("surface") or "rgba(32,28,39,0.88)"),
            "on_muted": str(tokens.get("onMuted") or _DEFAULT_DARK["on_muted"]),
            "primary": str(tokens.get("primary") or overrides.get("--uhfnf-primary") or _DEFAULT_DARK["primary"]),
            "accent": str(tokens.get("accent") or overrides.get("--uhfnf-accent") or _DEFAULT_DARK["accent"]),
        },
        _DEFAULT_DARK,
    )
    light = dict(_DEFAULT_LIGHT)
    light["primary"] = dark["primary"]
    light["accent"] = dark["accent"]
    return light, dark


def _emit_color(prefix_key: str, color_key: str, theme: dict[str, str]) -> dict[str, str]:
    r, g, b, a = _parse_color(theme[color_key])
    out = {
        f"{{{{{prefix_key}_{color_key.upper()}_R}}}}": f"{r:.3f}",
        f"{{{{{prefix_key}_{color_key.upper()}_G}}}}": f"{g:.3f}",
        f"{{{{{prefix_key}_{color_key.upper()}_B}}}}": f"{b:.3f}",
    }
    if color_key == "sheet":
        out[f"{{{{{prefix_key}_{color_key.upper()}_A}}}}"] = f"{a:.3f}"
    return out


def launch_style_values(workspace: Path) -> dict[str, str]:
    prefix = resolve_prefix(workspace) or "app"
    light, dark = _resolve_themes(workspace, prefix)
    values: dict[str, str] = {}
    for color_key in ("bg", "fg", "sheet", "on_muted", "primary", "accent"):
        values.update(_emit_color("LAUNCH_D", color_key, dark))
        values.update(_emit_color("LAUNCH_L", color_key, light))
    values["{{LAUNCH_D_SCRIM_A}}"] = dark["scrim_a"]
    values["{{LAUNCH_L_SCRIM_A}}"] = light["scrim_a"]
    values["{{LAUNCH_D_GAUGE_TRACK_A}}"] = dark["gauge_track_a"]
    values["{{LAUNCH_L_GAUGE_TRACK_A}}"] = light["gauge_track_a"]
    sheet_d_a = values.get("{{LAUNCH_D_SHEET_A}}", "1.000")
    sheet_l_a = values.get("{{LAUNCH_L_SHEET_A}}", "1.000")
    values.setdefault("{{LAUNCH_D_SHEET_A}}", sheet_d_a)
    values.setdefault("{{LAUNCH_L_SHEET_A}}", sheet_l_a)
    return values


def default_launch_style_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for color_key in ("bg", "fg", "sheet", "on_muted", "primary", "accent"):
        values.update(_emit_color("LAUNCH_D", color_key, _theme_bundle({}, _DEFAULT_DARK)))
        values.update(_emit_color("LAUNCH_L", color_key, _theme_bundle({}, _DEFAULT_LIGHT)))
    values["{{LAUNCH_D_SCRIM_A}}"] = _DEFAULT_DARK["scrim_a"]
    values["{{LAUNCH_L_SCRIM_A}}"] = _DEFAULT_LIGHT["scrim_a"]
    values["{{LAUNCH_D_GAUGE_TRACK_A}}"] = _DEFAULT_DARK["gauge_track_a"]
    values["{{LAUNCH_L_GAUGE_TRACK_A}}"] = _DEFAULT_LIGHT["gauge_track_a"]
    values.setdefault("{{LAUNCH_D_SHEET_A}}", "1.000")
    values.setdefault("{{LAUNCH_L_SHEET_A}}", "1.000")
    return values


def _substitute(text: str, values: dict[str, str]) -> str:
    for key, val in values.items():
        text = text.replace(key, val)
    return text


def sync_oc_host_launch_ui(workspace: Path, *, write: bool = True) -> Path | None:
    ws = workspace.expanduser().resolve()
    reg = _read_json(ws / "本包登记信息.json")
    app_name = str(reg.get("appName") or ws.name.split("-")[0] or "App").strip()
    prefix = resolve_prefix(ws)
    if not prefix or not TEMPLATE_HOST.is_file():
        return None

    cap = _prefix_cap(prefix)
    host_path = ws / app_name / f"{cap}HostController.m"
    if not host_path.is_file():
        matches = list(ws.rglob(f"{cap}HostController.m"))
        host_path = matches[0] if matches else None
    if host_path is None or not host_path.is_file():
        return None

    tpl = TEMPLATE_HOST.read_text(encoding="utf-8")
    values = {
        "{{APP_NAME}}": app_name,
        "{{PREFIX}}": prefix,
        "{{PREFIX_CAP}}": cap,
        "{{APP_SLUG}}": str(reg.get("appSlug") or app_name.lower()),
        "{{H5_HOST}}": "localhost",
        "{{ASSET_SCHEME}}": f"{prefix}asset",
    }
    values.update(launch_style_values(ws))
    rendered = _substitute(tpl, values)

    if write and rendered != host_path.read_text(encoding="utf-8"):
        host_path.write_text(rendered, encoding="utf-8")
    return host_path


def collect_native_launch_ui_violations(workspace: Path) -> list[str]:
    issues: list[str] = []
    for path in workspace.rglob("*HostController.m"):
        if "/build/" in str(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = path.relative_to(workspace)
        for marker in _GENERIC_MARKERS:
            if marker in text:
                issues.append(f"Native launch UI 仍为通用抄版（禁止 {marker}）: {rel}")
                break
        if "VeilCaption" not in text:
            issues.append(f"Native launch UI 须使用 LaunchVeil gauge（缺 VeilCaption）: {rel}")
        if "ApplyLaunchTheme" not in text:
            issues.append(f"Native launch UI 须支持深浅主题（缺 ApplyLaunchTheme）: {rel}")
    return issues
