"""Tab light/dark preview step — outputs under ``_preview/`` (tracked in per-app Git)."""

from __future__ import annotations

import re
from pathlib import Path

from batch.h5_site_paths import app_slug_from_name

PREVIEW_DIR = "_preview"
CANONICAL_NAME = "preview-canonical.md"


def preview_dir(project: Path) -> Path:
    return project / PREVIEW_DIR


def preview_html_path(project: Path, app_name: str) -> Path:
    slug = app_slug_from_name(app_name)
    return preview_dir(project) / f"{slug}-tabs-preview.html"


def preview_canonical_path(project: Path) -> Path:
    return preview_dir(project) / CANONICAL_NAME


def preview_approved_colors_path(project: Path) -> Path:
    return project / "skill-adapt" / "preview-approved-colors.json"


def sync_preview_colors_after_tabs(project: Path, *, write: bool = True) -> list[str]:
    """Parse canonical → preview-approved-colors.json; return issues."""
    from batch.preview_fidelity_gate import (
        sync_preview_approved_colors_from_canonical,
        verify_preview_approved_colors,
    )

    sync_preview_approved_colors_from_canonical(project, write=write)
    return verify_preview_approved_colors(project, app_name="")


def verify_preview_tabs_outputs(project: Path, app_name: str) -> list[str]:
    """Return human-readable issues when preview.tabs artifacts are missing or empty."""
    issues: list[str] = []
    html = preview_html_path(project, app_name)
    canonical = preview_canonical_path(project)
    if not html.is_file():
        issues.append(f"preview.tabs: 缺少 {html.relative_to(project)}")
    else:
        text = html.read_text(encoding="utf-8", errors="ignore")
        if len(text.strip()) < 500:
            issues.append(f"preview.tabs: {html.name} 过短（须为完整 Tab 预览 HTML）")
        if "prefers-color-scheme" not in text and "dark" not in text.lower():
            issues.append(f"preview.tabs: {html.name} 须含 Light + Dark 预览")
    if not canonical.is_file():
        issues.append(f"preview.tabs: 缺少 {canonical.relative_to(project)}")
    else:
        body = canonical.read_text(encoding="utf-8", errors="ignore").strip()
        if len(body) < 120:
            issues.append(f"preview.tabs: {CANONICAL_NAME} 过短")
        for heading in ("## Tabs", "## Colors", "## Typography"):
            if heading.lower() not in body.lower():
                issues.append(f"preview.tabs: {CANONICAL_NAME} 缺少 {heading} 小节")
                break
    from batch.preview_fidelity_gate import parse_colors_from_canonical, verify_preview_approved_colors

    if preview_approved_colors_path(project).is_file():
        issues.extend(verify_preview_approved_colors(project, app_name))
    else:
        parsed = parse_colors_from_canonical(project)
        if not parsed.get("light") or not parsed.get("dark"):
            issues.append(
                "preview.tabs: preview-canonical.md §Colors 须可解析为 light + dark（供 colors.json）"
            )
    return issues


def count_tabs_in_canonical(project: Path) -> int | None:
    path = preview_canonical_path(project)
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^##\s*Tabs\b[\s\S]*?(?=^##\s|\Z)", text, re.MULTILINE | re.IGNORECASE)
    if not m:
        return None
    routes = re.findall(r"#/[a-z0-9_-]+", m.group(0), re.I)
    return len(set(routes)) if routes else None
