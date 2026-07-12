"""Verify h5_shell hash-router overlay routes stack base page under veil scrim."""

from __future__ import annotations

import re
from pathlib import Path

from batch.h5_legal_ui import (
    is_h5_monolith,
    is_h5_shell_project,
    panels_dir,
    resolve_vault_css_text,
    resolve_vault_js_text,
)

VEIL_DIALOG_IN_RENDER_RE = re.compile(
    r"u-[a-z0-9]+-veil-dialog",
    re.IGNORECASE,
)
VEIL_SHEET_IN_RENDER_RE = re.compile(
    r"u-[a-z0-9]+-veil-sheet",
    re.IGNORECASE,
)
HASH_OVERLAY_ROUTE_RE = re.compile(
    r"""(?:case\s+['"]/(legal|[^'"]+/filter)['"]\s*:"""
    r"""|if\s*\(\s*path\s*===\s*['"]/(legal|filter)['"]\s*\))""",
    re.IGNORECASE,
)
NAIVE_DISPATCH_RE = re.compile(
    r"dispatch\s*:\s*function\s*\([^)]*\)\s*\{[^}]*"
    r"innerHTML\s*=\s*[^;]*\.render\s*\(\s*path\s*,",
    re.IGNORECASE | re.DOTALL,
)
STACKED_DISPATCH_RE = re.compile(
    r"render\s*\(\s*base\.path\s*,\s*base\.params\s*\)\s*\+\s*[^;]*\.render\s*\(\s*path\s*,",
    re.IGNORECASE,
)


def find_core_js(project: Path) -> Path | None:
    from batch.h5_legal_ui import resolve_prefix

    panels = panels_dir(project)
    if panels is None or not panels.is_dir():
        return None
    prefix = resolve_prefix(project)
    preferred = panels / f"{prefix}_core.js"
    if preferred.is_file():
        return preferred
    matches = sorted(panels.glob("*_core.js"))
    return matches[0] if matches else None


def _uses_hash_overlay_routes(render_text: str) -> bool:
    if not HASH_OVERLAY_ROUTE_RE.search(render_text):
        return False
    return bool(
        VEIL_DIALOG_IN_RENDER_RE.search(render_text)
        or VEIL_SHEET_IN_RENDER_RE.search(render_text)
    )


def verify_h5_overlay_stack(project: Path) -> list[str]:
    project = project.expanduser().resolve()
    issues: list[str] = []

    if not is_h5_shell_project(project):
        return issues

    render_text, _ = resolve_vault_js_text(project)
    if render_text is None:
        if is_h5_monolith(project):
            issues.append("RENDER: missing vault entry.htm (h5_monolith)")
        else:
            issues.append("RENDER: missing vault *_render.js")
        return issues

    if is_h5_monolith(project):
        core_text = render_text
    else:
        core = find_core_js(project)
        if core is None:
            issues.append("CORE: missing vault *_core.js")
            return issues
        core_text = core.read_text(encoding="utf-8", errors="ignore")

    if not _uses_hash_overlay_routes(render_text):
        return issues

    if "isOverlayPath" not in core_text and "OVERLAY_PATHS" not in core_text:
        issues.append(
            "ROUTER: hash overlay routes use veil but missing isOverlayPath/OVERLAY_PATHS"
        )
    if "_overlayBase" not in core_text:
        issues.append("ROUTER: missing _overlayBase to remember origin page for overlays")
    if not STACKED_DISPATCH_RE.search(core_text):
        issues.append(
            "ROUTER: dispatch must stack base+overlay "
            "(render(base.path, base.params) + render(path, ...))"
        )
    if NAIVE_DISPATCH_RE.search(core_text) and not STACKED_DISPATCH_RE.search(core_text):
        issues.append(
            "ROUTER: overlay dispatch replaces full page — scrim will look opaque grey"
        )

    css = resolve_vault_css_text(project)
    if css is not None:
        if "veil-scrim" in css or "veil-dialog-scrim" in css:
            for token in ("veil-scrim", "veil-dialog-scrim"):
                match = re.search(rf"--[a-z0-9]+-{token}\s*:\s*([^;]+);", css, re.I)
                if match and "rgba" not in match.group(1).lower():
                    issues.append(
                        f"CSS: --*-{token} should use rgba alpha, not opaque color"
                    )

    return issues
