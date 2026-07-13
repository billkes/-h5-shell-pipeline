"""Scaffold Vite + Vue H5 source tree (Mockoo/Prepoo pattern)."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from batch.h5_site_paths import app_slug_from_name, sync_h5_dev_entry_urls
from batch.pack_type import is_h5_shell

TEMPLATE_ROOT = (
    Path(__file__).resolve().parents[2] / "data" / "static" / "templates" / "h5_vite"
)
H5_SOURCE_ROOT = "h5/"


def _prefix_cap(prefix: str) -> str:
    p = (prefix or "app").strip()
    if not p:
        return "App"
    return p[0].upper() + p[1:]


def resolve_prefix(project: Path, reg: dict[str, Any] | None = None) -> str:
    if reg is None:
        reg = _read_register(project)
    anti = reg.get("codeAntiCorrelation") or {}
    if isinstance(anti, dict):
        prefix = str(anti.get("dartCodePrefix") or "").strip().lower()
        if prefix:
            return prefix
    from batch.workspace import dart_prefix

    return dart_prefix(project)


def _read_register(project: Path) -> dict[str, Any]:
    path = project / "本包登记信息.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def template_values(project: Path, *, app_name: str, prefix: str) -> dict[str, str]:
    slug = app_slug_from_name(app_name)
    cap = _prefix_cap(prefix)
    return {
        "{{APP_NAME}}": app_name,
        "{{APP_NAME_LOWER}}": app_name.lower(),
        "{{APP_SLUG}}": slug,
        "{{PREFIX}}": prefix.lower(),
        "{{PREFIX_CAP}}": cap,
    }


def substitute_text(text: str, values: dict[str, str]) -> str:
    for key, val in values.items():
        text = text.replace(key, val)
    return text


def rename_with_placeholders(path: Path, values: dict[str, str]) -> Path:
    new_name = substitute_text(path.name, values)
    if new_name == path.name:
        return path
    new_path = path.with_name(new_name)
    path.rename(new_path)
    return new_path


def h5_source_dir(project: Path) -> Path:
    return project / H5_SOURCE_ROOT.rstrip("/")


def scaffold_exists(project: Path) -> bool:
    return (h5_source_dir(project) / "package.json").is_file()


def _has_agent_src_tree(dst: Path) -> bool:
    src = dst / "src"
    if not src.is_dir():
        return False
    for child in src.iterdir():
        if child.name.startswith("."):
            continue
        return True
    return False


def _substitute_tree(root: Path, values: dict[str, str]) -> None:
    paths = sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True)
    for path in paths:
        if path.is_file():
            try:
                raw = path.read_text(encoding="utf-8")
                updated = substitute_text(raw, values)
                if updated != raw:
                    path.write_text(updated, encoding="utf-8")
            except UnicodeDecodeError:
                pass
        rename_with_placeholders(path, values)


def _merge_toolchain_only(dst: Path, values: dict[str, str]) -> None:
    """Add Vite toolchain files without wiping Agent-written src/."""
    dst.mkdir(parents=True, exist_ok=True)
    for rel in (
        "package.json",
        "vite.config.ts",
        "legal-md-sync.plugin.mjs",
        "tsconfig.json",
        "tsconfig.node.json",
        "index.html",
        "README.md",
    ):
        src_file = TEMPLATE_ROOT / rel
        if src_file.is_file():
            text = substitute_text(src_file.read_text(encoding="utf-8"), values)
            (dst / rel).write_text(text, encoding="utf-8")
    scripts_dst = dst / "scripts"
    scripts_dst.mkdir(parents=True, exist_ok=True)
    tpl_scripts = TEMPLATE_ROOT / "scripts"
    if tpl_scripts.is_dir():
        for item in tpl_scripts.iterdir():
            if item.is_file():
                text = substitute_text(item.read_text(encoding="utf-8"), values)
                (scripts_dst / item.name).write_text(text, encoding="utf-8")
    legal_dir = dst / "src" / "legal"
    legal_dir.mkdir(parents=True, exist_ok=True)
    legal_tpl = TEMPLATE_ROOT / "src" / "legal" / "{{PREFIX}}_legal_bundled.ts"
    if legal_tpl.is_file() and not any(legal_dir.glob("*_legal_bundled.ts")):
        cap_name = f"{values['{{PREFIX}}']}_legal_bundled.ts"
        text = substitute_text(legal_tpl.read_text(encoding="utf-8"), values)
        (legal_dir / cap_name).write_text(text, encoding="utf-8")
    for rel in ("main.ts", "App.vue", "env.d.ts"):
        dst_file = dst / "src" / rel
        tpl_file = TEMPLATE_ROOT / "src" / rel
        if tpl_file.is_file() and not dst_file.is_file():
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            text = substitute_text(tpl_file.read_text(encoding="utf-8"), values)
            dst_file.write_text(text, encoding="utf-8")
    router_index = dst / "src" / "router" / "index.ts"
    if not router_index.is_file():
        router_index.parent.mkdir(parents=True, exist_ok=True)
        tpl_router = TEMPLATE_ROOT / "src" / "router" / "index.ts"
        if tpl_router.is_file():
            router_index.write_text(
                substitute_text(tpl_router.read_text(encoding="utf-8"), values),
                encoding="utf-8",
            )


def ensure_public_native_img_symlink(h5_dir: Path, project: Path) -> bool:
    """Expose {AppName}/assets/img via public/assets/img for Vite dev."""
    from batch.native_bundled_media import native_bundled_img_dir, requires_native_bundled_media

    if not requires_native_bundled_media(project):
        return False
    img_src = native_bundled_img_dir(project)
    if not img_src or not img_src.is_dir():
        return False
    public_assets = h5_dir / "public" / "assets"
    link = public_assets / "img"
    public_assets.mkdir(parents=True, exist_ok=True)
    try:
        rel_target = Path("..") / ".." / ".." / img_src.relative_to(h5_dir.parent)
    except ValueError:
        rel_target = img_src
    if link.is_symlink():
        try:
            if link.resolve() == img_src.resolve():
                return False
        except OSError:
            pass
        link.unlink()
    elif link.exists():
        return False
    link.symlink_to(rel_target, target_is_directory=True)
    return True


def ensure_public_vault_symlink(h5_dir: Path, prefix: str) -> bool:
    """Legacy Flutter/vite path — skip when native bundle img dir exists."""
    vault_src = h5_dir / "assets" / f"{prefix}_vault"
    if vault_src.is_dir():
        return False
    return False


def ensure_vite_lan_server(h5_dir: Path) -> bool:
    """Ensure vite.config.ts exposes LAN (host: true). Returns True if file changed."""
    cfg = h5_dir / "vite.config.ts"
    if not cfg.is_file():
        return False
    text = cfg.read_text(encoding="utf-8")
    if re.search(r"server\s*:\s*\{[^}]*\bhost\s*:", text, re.S):
        return False
    updated, n = re.subn(
        r"(server\s*:\s*\{)",
        r"\1\n    host: true,",
        text,
        count=1,
    )
    if n == 0:
        return False
    cfg.write_text(updated, encoding="utf-8")
    return True


def apply_h5_vite_scaffold(
    project: Path,
    *,
    app_name: str,
    prefix: str,
    force: bool = False,
) -> Path:
    """Copy h5_vite template into workspace/h5/ (idempotent unless force)."""
    project = project.expanduser().resolve()
    dst = h5_source_dir(project)
    if scaffold_exists(project) and not force:
        return dst
    if not TEMPLATE_ROOT.is_dir():
        raise FileNotFoundError(f"h5_vite template missing: {TEMPLATE_ROOT}")

    values = template_values(project, app_name=app_name, prefix=prefix)
    if force and dst.exists():
        shutil.rmtree(dst)
    if _has_agent_src_tree(dst):
        _merge_toolchain_only(dst, values)
    elif not dst.exists() or force:
        shutil.copytree(TEMPLATE_ROOT, dst, ignore=shutil.ignore_patterns("template.json"))
        _substitute_tree(dst, values)
    else:
        _merge_toolchain_only(dst, values)

    ensure_vite_lan_server(dst)
    ensure_public_native_img_symlink(dst, project)
    ensure_public_vault_symlink(dst, values["{{PREFIX}}"])
    return dst


def ensure_h5_vite_scaffold(
    project: Path,
    *,
    app_name: str,
    prefix: str,
    pack_type: str,
    force: bool = False,
) -> Path | None:
    if not is_h5_shell(pack_type):
        return None
    p = (prefix or "app").strip().lower()
    if not re.fullmatch(r"[a-z]{4,6}", p):
        p = "app"
    dst = apply_h5_vite_scaffold(project, app_name=app_name, prefix=p, force=force)
    ensure_vite_lan_server(dst)
    ensure_public_native_img_symlink(dst, project)
    ensure_public_vault_symlink(dst, p)
    sync_h5_dev_entry_urls(project)
    return dst


def registration_h5_vite_fields() -> dict[str, str]:
    return {
        "h5SourceRoot": H5_SOURCE_ROOT,
        "h5BuildCommand": "npm run build:deploy",
        "h5DevServerPort": "5174",
    }
