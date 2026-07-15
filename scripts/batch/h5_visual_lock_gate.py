"""Post-delivery gate: H5 / Native theme fidelity vs 本包视觉锁.json."""

from __future__ import annotations

import json
import re
from pathlib import Path

from batch.h5_theme_tokens import THEME_START, resolve_prefix

VISUAL_LOCK_FILE = "本包视觉锁.json"
_HEX_RE = re.compile(r"#(?:[0-9A-Fa-f]{3}){1,2}\b")
_CSS_VAR_RE = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;]+);", re.I)


def _normalize_hex(value: str) -> str:
    raw = (value or "").strip().upper()
    match = _HEX_RE.search(raw)
    if not match:
        return ""
    h = match.group(0).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return f"#{h}"


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _flatten_color_tokens(tokens: object) -> dict[str, str]:
    if not isinstance(tokens, dict):
        return {}
    if isinstance(tokens.get("light"), dict) or isinstance(tokens.get("dark"), dict):
        flat: dict[str, str] = {}
        for mode in ("light", "dark"):
            block = tokens.get(mode)
            if isinstance(block, dict):
                for key, val in block.items():
                    if isinstance(val, str) and val.strip():
                        flat[f"{mode}.{key}"] = val.strip()
                        if key not in flat:
                            flat[key] = val.strip()
        return flat
    return {str(k): str(v).strip() for k, v in tokens.items() if isinstance(v, str) and str(v).strip()}


def _css_mode_tokens(css: str, prefix: str) -> tuple[dict[str, str], dict[str, str]]:
    p = prefix.lower()
    light: dict[str, str] = {}
    dark: dict[str, str] = {}

    root_match = re.search(r":root\s*\{([^}]+)\}", css, re.S)
    if root_match:
        for key, val in _CSS_VAR_RE.findall(root_match.group(1)):
            if key.startswith(f"{p}-"):
                light[key[len(p) + 1 :]] = val.strip()

    dark_block = re.search(
        r"@media\s*\(\s*prefers-color-scheme:\s*dark\s*\)\s*\{[^{]*:root\s*\{([^}]+)\}",
        css,
        re.S | re.I,
    )
    if dark_block:
        for key, val in _CSS_VAR_RE.findall(dark_block.group(1)):
            if key.startswith(f"{p}-"):
                dark[key[len(p) + 1 :]] = val.strip()
    return light, dark


def _lock_primary(tokens: dict[str, str]) -> str:
    for key in ("primary", "light.primary", "dark.primary"):
        val = _normalize_hex(tokens.get(key, ""))
        if val:
            return val
    return ""


def _lock_dark_bg(tokens: dict[str, str]) -> str:
    for key in ("backgroundDark", "dark.background", "dark.bg", "background"):
        val = _normalize_hex(tokens.get(key, ""))
        if val:
            return val
    return ""


def verify_visual_lock_file(workspace: Path) -> list[str]:
    issues: list[str] = []
    path = workspace / VISUAL_LOCK_FILE
    if not path.is_file():
        issues.append("visual: 缺少 本包视觉锁.json")
        return issues

    lock = _read_json(path)
    if not lock:
        issues.append("visual: 本包视觉锁.json 不是合法 JSON object")
        return issues

    tokens_raw = lock.get("colorTokens")
    if not isinstance(tokens_raw, dict):
        issues.append("visual: 本包视觉锁.json 缺少 colorTokens")
    else:
        flat = _flatten_color_tokens(tokens_raw)
        if not _lock_primary(flat):
            issues.append("visual: 本包视觉锁.json colorTokens 缺少 primary")
        if not _lock_dark_bg(flat):
            issues.append("visual: 本包视觉锁.json colorTokens 缺少 backgroundDark / dark.background")

    selection = lock.get("componentSelection")
    if not isinstance(selection, list) or not selection:
        issues.append("visual: 本包视觉锁.json componentSelection 须为非空 array")

    ambient = lock.get("ambientCanvas")
    if not isinstance(ambient, dict) or not ambient.get("motifKey"):
        issues.append("visual: 本包视觉锁.json ambientCanvas 须含 motifKey + scenes")

    if not lock.get("designerDeckSelections"):
        issues.append("visual: 本包视觉锁.json 缺少 designerDeckSelections")

    return issues


def verify_h5_css_vs_visual_lock(workspace: Path) -> list[str]:
    issues: list[str] = []
    lock = _read_json(workspace / VISUAL_LOCK_FILE)
    tokens = _flatten_color_tokens(lock.get("colorTokens"))
    expected_primary = _lock_primary(tokens)
    expected_dark_bg = _lock_dark_bg(tokens)
    if not expected_primary and not expected_dark_bg:
        return issues

    prefix = resolve_prefix(workspace)
    if not prefix:
        issues.append("visual: 登记信息缺少 codeAntiCorrelation.dartCodePrefix，无法核对 CSS token")
        return issues

    css_path = workspace / "h5" / "src" / "styles" / "global.css"
    if not css_path.is_file():
        issues.append("visual: 缺少 h5/src/styles/global.css")
        return issues

    css = css_path.read_text(encoding="utf-8", errors="ignore")
    if THEME_START not in css:
        issues.append("visual: global.css 缺少 THEME:pipeline 块（须从视觉锁 / preview 同步 token）")

    light, dark = _css_mode_tokens(css, prefix)
    actual_primary = _normalize_hex(light.get("primary", ""))
    actual_dark_bg = _normalize_hex((dark or light).get("bg", ""))

    if expected_primary and actual_primary and actual_primary != expected_primary:
        issues.append(
            f"visual: global.css --{prefix}-primary={actual_primary} 与视觉锁 primary={expected_primary} 不一致"
        )
    elif expected_primary and not actual_primary:
        issues.append(f"visual: global.css 缺少 --{prefix}-primary")

    if expected_dark_bg and actual_dark_bg and actual_dark_bg != expected_dark_bg:
        issues.append(
            f"visual: global.css dark --{prefix}-bg={actual_dark_bg} 与视觉锁 backgroundDark={expected_dark_bg} 不一致"
        )
    elif expected_dark_bg and not actual_dark_bg:
        issues.append(f"visual: global.css 缺少 dark mode --{prefix}-bg")

    return issues


def verify_ambient_canvas_impl(workspace: Path) -> list[str]:
    issues: list[str] = []
    lock = _read_json(workspace / VISUAL_LOCK_FILE)
    ambient = lock.get("ambientCanvas")
    if not isinstance(ambient, dict):
        return issues
    scenes = ambient.get("scenes")
    if not isinstance(scenes, dict) or not scenes:
        return issues

    prefix = resolve_prefix(workspace)
    app_vue = workspace / "h5" / "src" / "App.vue"
    if not app_vue.is_file():
        issues.append("visual: 视觉锁含 ambientCanvas 但缺少 h5/src/App.vue")
        return issues

    text = app_vue.read_text(encoding="utf-8", errors="ignore")
    markers = (
        "setAmbientScene",
        f"u-{prefix}-ambient",
        "ambientCanvas",
        f"data-{prefix}-scene",
    )
    if not any(m in text for m in markers):
        issues.append(
            f"visual: App.vue 须落地 ambientCanvas（setAmbientScene / u-{prefix}-ambient / data-{prefix}-scene）"
        )
    return issues


def verify_typography_lock(workspace: Path) -> list[str]:
    issues: list[str] = []
    lock = _read_json(workspace / VISUAL_LOCK_FILE)
    designer = lock.get("designerDeckSelections")
    if not isinstance(designer, dict):
        return issues

    fonts: list[str] = []
    for key in ("headingFont", "bodyFont", "displayFont", "fontPairing"):
        val = designer.get(key)
        if isinstance(val, str) and val.strip():
            fonts.append(val.strip())
        elif isinstance(val, dict):
            for sub in val.values():
                if isinstance(sub, str) and sub.strip():
                    fonts.append(sub.strip())

    typo_tokens = lock.get("typographyTokens")
    if isinstance(typo_tokens, dict):
        for val in typo_tokens.values():
            if isinstance(val, str) and val.strip():
                fonts.append(val.strip())

    if not fonts:
        return issues

    css_path = workspace / "h5" / "src" / "styles" / "global.css"
    index_html = workspace / "h5" / "index.html"
    joined = ""
    if css_path.is_file():
        joined += css_path.read_text(encoding="utf-8", errors="ignore")
    if index_html.is_file():
        joined += index_html.read_text(encoding="utf-8", errors="ignore")

    missing = [f for f in fonts if f.split(",")[0].strip().replace("'", "").replace('"', "") not in joined]
    if missing:
        issues.append(
            "visual: 视觉锁字体未在 H5 落地（global.css / index.html 缺 "
            + ", ".join(missing[:3])
            + ("…" if len(missing) > 3 else "")
            + "）"
        )
    return issues


def collect_h5_visual_lock_violations(workspace: Path, app_name: str = "") -> list[str]:
    """Post-delivery visual lock fidelity checks for h5-post / 编组 L."""
    ws = workspace.expanduser().resolve()
    h5_src = ws / "h5" / "src"
    if not h5_src.is_dir():
        return []

    issues: list[str] = []
    issues.extend(verify_visual_lock_file(ws))
    issues.extend(verify_h5_css_vs_visual_lock(ws))
    issues.extend(verify_ambient_canvas_impl(ws))
    issues.extend(verify_typography_lock(ws))

    try:
        from batch.h5_theme_tokens import verify_h5_theme_system

        for item in verify_h5_theme_system(ws):
            if not item.startswith("visual:"):
                issues.append(item.replace("UX Gate:", "visual:", 1))
            else:
                issues.append(item)
    except OSError:
        pass

    try:
        from batch.preview_fidelity_gate import collect_preview_fidelity_violations

        for item in collect_preview_fidelity_violations(ws, app_name):
            issues.append(item.replace("preview:", "visual:", 1))
    except OSError:
        pass

    return issues
