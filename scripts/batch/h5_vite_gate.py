"""Gate helpers for h5_vite (Vue 3 + Vite singlefile) projects."""

from __future__ import annotations

import re
from pathlib import Path

from batch.h5_vite_scaffold import h5_source_dir, scaffold_exists

_TABBAR_FONT_EXEMPT = re.compile(r"tabbar|nav-label|chip-label", re.I)


def is_h5_vite_project(project: Path) -> bool:
    return scaffold_exists(project)


def h5_src_dir(project: Path) -> Path:
    return h5_source_dir(project) / "src"


def collect_vite_source_text(project: Path, *suffixes: str) -> str:
    src = h5_src_dir(project)
    if not src.is_dir():
        return ""
    parts: list[str] = []
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        if suffixes and path.suffix not in suffixes:
            continue
        try:
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n".join(parts)


def vite_vue_and_ts_text(project: Path) -> str:
    return collect_vite_source_text(project, ".vue", ".ts")


def vite_css_text(project: Path) -> str:
    styles = h5_src_dir(project) / "styles"
    if not styles.is_dir():
        return ""
    parts: list[str] = []
    for css in sorted(styles.rglob("*.css")):
        try:
            parts.append(css.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n".join(parts)


def find_welcome_view_text(project: Path) -> str:
    src = h5_src_dir(project)
    if not src.is_dir():
        return ""
    candidates: list[Path] = []
    for path in src.rglob("*.vue"):
        name = path.name.lower()
        if "welcome" in name:
            candidates.append(path)
    if not candidates:
        return ""
    candidates.sort(key=lambda p: (p.name != "WelcomeView.vue", len(p.parts)))
    try:
        return candidates[0].read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def vite_legal_card_present(
    render_text: str, css: str, class_token: str, *, prefix: str = ""
) -> bool:
    card_key = f"{class_token}-card"
    if card_key in render_text or card_key in css:
        return True
    dialog_keys = [f"{class_token}-dialog"]
    if prefix:
        dialog_keys.append(f"c-{prefix}-dialog")
    combined = f"{render_text}\n{css}"
    for dialog_key in dialog_keys:
        if dialog_key in combined:
            if "flex-direction" in combined and ("90vw" in combined or "340px" in combined):
                return True
    return False


def vite_font_size_issues(css: str) -> list[str]:
    issues: list[str] = []
    for match in re.finditer(r"font-size:\s*(\d+)px", css):
        if int(match.group(1)) >= 12:
            continue
        start = max(0, match.start() - 240)
        chunk = css[start : match.end()]
        if _TABBAR_FONT_EXEMPT.search(chunk):
            continue
        issues.append("UX Gate: 存在 font-size < 12px 的正文样式")
        break
    return issues
