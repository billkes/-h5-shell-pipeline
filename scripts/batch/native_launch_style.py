"""Native launch veil + retry UI — colors from 本包视觉锁.json, gate generic copied chrome."""

from __future__ import annotations

import json
import re
from pathlib import Path

TEMPLATE_HOST = (
    Path(__file__).resolve().parents[2]
    / "data/static/templates/oc_shell/{{APP_NAME}}/{{APP_NAME}}/{{PREFIX_CAP}}HostController.m"
)

_DEFAULT_STYLE = {
    "{{LAUNCH_BG_R}}": "0.059",
    "{{LAUNCH_BG_G}}": "0.090",
    "{{LAUNCH_BG_B}}": "0.165",
    "{{LAUNCH_PRIMARY_R}}": "0.918",
    "{{LAUNCH_PRIMARY_G}}": "0.345",
    "{{LAUNCH_PRIMARY_B}}": "0.047",
    "{{LAUNCH_ACCENT_R}}": "0.020",
    "{{LAUNCH_ACCENT_G}}": "0.588",
    "{{LAUNCH_ACCENT_B}}": "0.412",
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
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return r, g, b


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


def launch_style_values(workspace: Path) -> dict[str, str]:
    values = dict(_DEFAULT_STYLE)
    lock = _read_json(workspace / "本包视觉锁.json")
    tokens = lock.get("colorTokens") if isinstance(lock.get("colorTokens"), dict) else {}
    overrides = lock.get("packageTokenOverrides") if isinstance(lock.get("packageTokenOverrides"), dict) else {}

    bg_hex = str(tokens.get("backgroundDark") or overrides.get("--uhfnf-bg-dark") or "#0F172A")
    primary_hex = str(tokens.get("primary") or overrides.get("--uhfnf-primary") or "#EA580C")
    accent_hex = str(tokens.get("accent") or overrides.get("--uhfnf-accent") or "#059669")

    bg = _hex_to_rgb_float(bg_hex.replace("rgba(", "#").split(",")[0] if bg_hex.startswith("rgba") else bg_hex)
    primary = _hex_to_rgb_float(primary_hex)
    accent = _hex_to_rgb_float(accent_hex)

    values["{{LAUNCH_BG_R}}"] = f"{bg[0]:.3f}"
    values["{{LAUNCH_BG_G}}"] = f"{bg[1]:.3f}"
    values["{{LAUNCH_BG_B}}"] = f"{bg[2]:.3f}"
    values["{{LAUNCH_PRIMARY_R}}"] = f"{primary[0]:.3f}"
    values["{{LAUNCH_PRIMARY_G}}"] = f"{primary[1]:.3f}"
    values["{{LAUNCH_PRIMARY_B}}"] = f"{primary[2]:.3f}"
    values["{{LAUNCH_ACCENT_R}}"] = f"{accent[0]:.3f}"
    values["{{LAUNCH_ACCENT_G}}"] = f"{accent[1]:.3f}"
    values["{{LAUNCH_ACCENT_B}}"] = f"{accent[2]:.3f}"
    return values


def default_launch_style_values() -> dict[str, str]:
    return dict(_DEFAULT_STYLE)


def _substitute(text: str, values: dict[str, str]) -> str:
    for key, val in values.items():
        text = text.replace(key, val)
    return text


def sync_oc_host_launch_ui(workspace: Path, *, write: bool = True) -> Path | None:
    """Re-render *HostController.m launch veil + retry from oc_shell template."""
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
        if "VeilCaption" not in text and "LaunchPrimary" not in text:
            issues.append(f"Native launch UI 须使用 LaunchVeil gauge（缺 VeilCaption）: {rel}")
    return issues
