"""Run Vite build and deploy monolith to h5_site/{appSlug}/."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from batch.h5_site_paths import app_slug_from_name, site_upload_root_rel
from batch.h5_vite_scaffold import h5_source_dir, resolve_prefix, scaffold_exists
from batch.h5_site_paths import site_entry_path, vault_dir_path
from batch.pack_type import is_h5_shell

REGISTER_FILE = "本包登记信息.json"
NPM_INSTALL_TIMEOUT_S = 600
NPM_BUILD_TIMEOUT_S = 300


def _read_register(project: Path) -> dict:
    path = project / REGISTER_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _resolve_app_slug(project: Path, reg: dict | None = None) -> str:
    reg = reg or _read_register(project)
    slug = str(reg.get("appSlug") or "").strip().lower()
    if slug:
        return slug
    app_name = str(reg.get("appName") or project.name or "").strip()
    return app_slug_from_name(app_name)


def _npm_available() -> bool:
    return shutil.which("npm") is not None


def run_h5_vite_build(project: Path, *, skip_install: bool = False) -> tuple[bool, list[str]]:
    """npm install + build:deploy → h5_site/{appSlug}/index.html."""
    project = project.expanduser().resolve()
    issues: list[str] = []

    if not scaffold_exists(project):
        issues.append(f"MISSING: {h5_source_dir(project).relative_to(project)}/package.json (run lock.dimensions scaffold)")
        return False, issues

    if not _npm_available():
        issues.append("MISSING: npm (Node.js) — required for dev.h5.build")
        return False, issues

    h5_dir = h5_source_dir(project)
    reg = _read_register(project)
    prefix = resolve_prefix(project, reg)
    slug = _resolve_app_slug(project, reg)
    entry_name = str(reg.get("h5SiteEntry") or "index.html").strip() or "index.html"
    # Coerce legacy `{prefix}_entry.htm` / relative paths to locked monolith name.
    if entry_name not in ("index.html", "index.htm") or "/" in entry_name or "\\" in entry_name:
        entry_name = "index.html"
    env = {
        **os.environ,
        "H5_PREFIX": prefix,
        "H5_APP_SLUG": slug,
        "H5_SITE_ENTRY": entry_name,
    }

    if not skip_install or not (h5_dir / "node_modules").is_dir():
        install = subprocess.run(
            ["npm", "install", "--no-audit", "--no-fund"],
            cwd=str(h5_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=NPM_INSTALL_TIMEOUT_S,
            check=False,
        )
        if install.returncode != 0:
            tail = (install.stderr or install.stdout or "")[-2000:]
            issues.append(f"npm install failed (exit {install.returncode}): {tail}")
            return False, issues

    build = subprocess.run(
        ["npm", "run", "build:deploy"],
        cwd=str(h5_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=NPM_BUILD_TIMEOUT_S,
        check=False,
    )
    if build.returncode != 0:
        tail = (build.stderr or build.stdout or "")[-2000:]
        issues.append(f"npm run build:deploy failed (exit {build.returncode}): {tail}")
        return False, issues

    entry = site_entry_path(project, reg)
    if not entry.is_file():
        issues.append(f"MISSING: build output {entry.relative_to(project)}")
        return False, issues

    return True, issues


def verify_h5_vite_build(project: Path) -> list[str]:
    """Gate helper — ensure deployable entry exists after build."""
    issues: list[str] = []
    entry = site_entry_path(project)
    if not entry.is_file():
        issues.append(f"MISSING: {entry.relative_to(project)} (run dev.h5.build)")
        return issues
    try:
        text = entry.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        issues.append(f"READ: {entry.name}: {exc}")
        return issues
    if len(text.strip()) < 500:
        issues.append(f"SHORT: {entry.name} looks empty after Vite build")
    return issues


def cleanup_stale_h5_site_sources(project: Path) -> list[str]:
    """Remove pre-Vite hand-written files from h5_site/ (legacy flat entry, legal JS, panels/)."""
    removed: list[str] = []
    upload_root = project / site_upload_root_rel().rstrip("/")
    if not upload_root.is_dir():
        return removed

    prefix = resolve_prefix(project)
    reg = _read_register(project)
    entry = site_entry_path(project, reg)
    vault = vault_dir_path(project, reg)

    # Legacy flat layout: h5_site/{prefix}_entry.htm
    for path in list(upload_root.iterdir()):
        rel = str(path.relative_to(project))
        if path.is_file() and path.suffix.lower() in {".htm", ".html", ".js", ".css"}:
            if path.resolve() != entry.resolve():
                path.unlink()
                removed.append(rel)
        elif path.is_dir() and path.resolve() != vault.resolve():
            if path.name in {f"{prefix}_panels", "panels"}:
                shutil.rmtree(path)
                removed.append(rel + "/")

    if not vault.is_dir():
        return removed

    for path in list(vault.iterdir()):
        rel = str(path.relative_to(project))
        if path.is_file() and path.resolve() == entry.resolve():
            continue
        if path.is_dir() and path.name in {f"{prefix}_panels", "panels"}:
            shutil.rmtree(path)
            removed.append(rel + "/")
            continue
        if path.is_file() and path.suffix.lower() in {".js", ".ts", ".css", ".htm", ".html"}:
            if path.name != entry.name:
                path.unlink()
                removed.append(rel)
    return removed


def is_h5_shell_project(project: Path) -> bool:
    reg = _read_register(project)
    return is_h5_shell(str(reg.get("packType") or ""))
