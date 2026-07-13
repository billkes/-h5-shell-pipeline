"""Plaza dev-entrance guard: strip obvious debug entrances before deployment."""

from __future__ import annotations

import re
from pathlib import Path

from batch.h5_legal_ui import is_h5_shell_project


DEV_ENTRANCE_START = "H5_PLAZA_DEV_ENTRANCE_START"
DEV_ENTRANCE_END = "H5_PLAZA_DEV_ENTRANCE_END"

_VAULT_SUFFIXES = frozenset({".js", ".htm", ".html", ".css"})


def _has_dev_marker(text: str) -> bool:
    return DEV_ENTRANCE_START in text or DEV_ENTRANCE_END in text


def strip_plaza_dev_entrance(vault_dir: Path) -> list[Path]:
    """Remove all blocks wrapped with H5_PLAZA_DEV_ENTRANCE_* markers.

    Markers must each occupy their own line (inside any comment style is fine).
    Returns the list of files that were modified.
    """
    modified: list[Path] = []
    if not vault_dir.is_dir():
        return modified

    for path in vault_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _VAULT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not _has_dev_marker(text):
            continue

        lines = text.splitlines(keepends=True)
        cleaned: list[str] = []
        inside = False
        changed = False
        for line in lines:
            if DEV_ENTRANCE_START in line:
                inside = True
                changed = True
                continue
            if DEV_ENTRANCE_END in line:
                inside = False
                changed = True
                continue
            if not inside:
                cleaned.append(line)

        if changed:
            try:
                path.write_text("".join(cleaned), encoding="utf-8")
                modified.append(path)
            except OSError:
                continue
    return modified


def verify_no_plaza_dev_entrance(vault_dir: Path, root: Path | None = None) -> list[str]:
    """Return error/warning messages for any remaining dev-entrance markers."""
    issues: list[str] = []
    if not vault_dir.is_dir():
        return issues

    for path in vault_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _VAULT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if _has_dev_marker(text):
            rel = path.relative_to(root) if root else path.name
            issues.append(
                f"H5 Gate：部署包仍含广场页开发入口标记 {DEV_ENTRANCE_START!r} → {rel}"
            )
    return issues


def verify_h5_plaza_dev_gate(project: Path) -> list[str]:
    """High-level wrapper used by the bundle gate for h5_shell projects."""
    if not is_h5_shell_project(project):
        return []

    from batch.screen_inventory import project_includes_route

    if not project_includes_route(project, "/plaza"):
        return []

    from batch.h5_bundle_gate import bundle_entry_path

    reg_path = project / "本包登记信息.json"
    if reg_path.is_file():
        import json
        try:
            reg = json.loads(reg_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            reg = {}
    else:
        reg = {}

    entry_rel = bundle_entry_path(reg)
    if not entry_rel:
        return []

    vault_dir = (project / entry_rel).parent
    if not vault_dir.is_dir():
        return []
    return verify_no_plaza_dev_entrance(vault_dir, project)


def find_plaza_obvious_entrance(vault_dir: Path, root: Path | None = None) -> list[str]:
    """Detect obvious plaza entrances that are not wrapped in dev markers.

    This is a heuristic fallback: if the implementer added a visible plaza
    trigger without using the markers, the gate can still warn.
    """
    issues: list[str] = []
    if not vault_dir.is_dir():
        return issues

    patterns = (
        re.compile(r'data-action\s*=\s*["\']go-plaza["\']', re.I),
        re.compile(r'data-route\s*=\s*["\']#/plaza["\']', re.I),
        re.compile(r'router\.(go|navigate)\s*\(\s*["\']#/plaza["\']', re.I),
        re.compile(r'class\s*=\s*["\'][^"\']*plaza-dev-entrance[^"\']*["\']', re.I),
    )

    for path in vault_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _VAULT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not _has_dev_marker(text):
            for pat in patterns:
                if pat.search(text):
                    rel = path.relative_to(root) if root else path.name
                    issues.append(
                        f"H5 Gate：发现未标记的广场页明显入口 → {rel}"
                    )
                    break
    return issues
