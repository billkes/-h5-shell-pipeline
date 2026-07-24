"""H5 Vite helpers — no code template copy. Agent creates h5/ from docs/H5壳Vite工程规范.md."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from batch.h5_site_paths import app_slug_from_name, sync_h5_dev_entry_urls
from batch.pack_type import is_h5_shell

H5_SOURCE_ROOT = "h5/"
_REPO_ROOT = Path(__file__).resolve().parents[2]
BROWSER_MOCK_SNIPPET = (
    _REPO_ROOT / "data" / "static" / "h5_snippets" / "bridge" / "browserMock.ts"
)
_BROWSER_MOCK_MARKER = "tryBrowserBridgeMock"


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
    """Placeholder map for any remaining string substitution (not template copy)."""
    slug = app_slug_from_name(app_name)
    cap = _prefix_cap(prefix)
    register = _read_register(project)
    asset_scheme = str(register.get("assetScheme") or f"{slug}-asset")
    return {
        "{{APP_NAME}}": app_name,
        "{{APP_NAME_LOWER}}": app_name.lower(),
        "{{APP_SLUG}}": slug,
        "{{PREFIX}}": prefix.lower(),
        "{{PREFIX_CAP}}": cap,
        "{{ASSET_SCHEME}}": asset_scheme,
    }


def substitute_text(text: str, values: dict[str, str]) -> str:
    for key, val in values.items():
        text = text.replace(key, val)
    return text


def h5_source_dir(project: Path) -> Path:
    return project / H5_SOURCE_ROOT.rstrip("/")


def scaffold_exists(project: Path) -> bool:
    """True when Agent (or prior run) already created an h5/ package.json."""
    return (h5_source_dir(project) / "package.json").is_file()


def ensure_public_native_img_symlink(h5_dir: Path, project: Path) -> bool:
    """Expose ios/{AppName}/SeedBundle via public/assets/img for Vite dev."""
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
    """Legacy Flutter/vite path — no-op when native bundle is used."""
    del h5_dir, prefix
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


def _app_name_lower_for_project(project: Path, app_name: str) -> str:
    name = (app_name or "").strip()
    if not name:
        reg = _read_register(project)
        name = str(reg.get("appName") or reg.get("name") or "").strip()
    if not name:
        name = project.name.split("-")[0] if project.name else "app"
    return name.lower()


def ensure_browser_bridge_mock(
    h5_dir: Path,
    *,
    app_name_lower: str,
    force: bool = False,
) -> list[str]:
    """Install browserMock.ts and soft-wire bridgeCall no-native branch.

    Returns list of relative paths changed. Does not invent a full bridge/index.ts;
    only patches an existing reject('Bridge unavailable') fallback when present.
    """
    changed: list[str] = []
    if not BROWSER_MOCK_SNIPPET.is_file():
        return changed
    bridge_dir = h5_dir / "src" / "bridge"
    if not bridge_dir.is_dir() and not (h5_dir / "src").is_dir():
        return changed
    bridge_dir.mkdir(parents=True, exist_ok=True)
    dest = bridge_dir / "browserMock.ts"
    raw = BROWSER_MOCK_SNIPPET.read_text(encoding="utf-8")
    body = raw.replace("{{APP_NAME_LOWER}}", app_name_lower)
    if force or not dest.is_file() or "{{APP_NAME_LOWER}}" in dest.read_text(encoding="utf-8"):
        dest.write_text(body, encoding="utf-8")
        changed.append("src/bridge/browserMock.ts")
    elif dest.read_text(encoding="utf-8") != body and force:
        dest.write_text(body, encoding="utf-8")
        changed.append("src/bridge/browserMock.ts")

    index = bridge_dir / "index.ts"
    if not index.is_file():
        return changed
    text = index.read_text(encoding="utf-8")
    if _BROWSER_MOCK_MARKER in text:
        return changed
    if "Bridge unavailable" not in text:
        # Snippet installed; Agent / implementer must wire per README
        return changed

    import_line = "import { tryBrowserBridgeMock } from './browserMock';\n"
    if "from './browserMock'" not in text and 'from "./browserMock"' not in text:
        m = list(re.finditer(r"^import .+?;\s*\n", text, re.M))
        if m:
            pos = m[-1].end()
            text = text[:pos] + import_line + text[pos:]
        else:
            text = import_line + text

    patterns = [
        (
            r"if\s*\(\s*action\s*===\s*['\"]shellReady['\"]\s*\)\s*resolve\(\{\}\)\s*;\s*"
            r"else\s*reject\(\s*new\s*Error\(\s*['\"]Bridge unavailable['\"]\s*\)\s*\)\s*;",
            "if (action === 'shellReady') resolve({});\n"
            "    else void tryBrowserBridgeMock(action, body).then(resolve, reject);",
        ),
        (
            r"reject\(\s*new\s*Error\(\s*['\"]Bridge unavailable['\"]\s*\)\s*\)\s*;",
            "void tryBrowserBridgeMock("
            "action, typeof body !== 'undefined' ? body : payload).then(resolve, reject);",
        ),
    ]
    patched = False
    for pat, repl in patterns:
        new_text, n = re.subn(pat, repl, text, count=1, flags=re.S)
        if n:
            text = new_text
            patched = True
            break

    if not patched:
        text += (
            "\n// TODO: replace Bridge unavailable reject with "
            "tryBrowserBridgeMock (data/static/h5_snippets/bridge/README.md)\n"
        )

    index.write_text(text, encoding="utf-8")
    changed.append("src/bridge/index.ts")
    return changed


def apply_h5_vite_scaffold(
    project: Path,
    *,
    app_name: str,
    prefix: str,
    force: bool = False,
) -> Path:
    """No template copy. Returns h5/ path; does not create sources from a template tree."""
    del app_name, prefix, force
    project = project.expanduser().resolve()
    return h5_source_dir(project)


def ensure_h5_vite_scaffold(
    project: Path,
    *,
    app_name: str,
    prefix: str,
    pack_type: str,
    force: bool = False,
) -> Path | None:
    """Agent-owned h5/: only sync LAN/dev helpers when tree already exists."""
    del force
    if not is_h5_shell(pack_type):
        return None
    p = (prefix or "app").strip().lower()
    if not re.fullmatch(r"[a-z]{4,6}", p):
        p = "app"
    project = project.expanduser().resolve()
    dst = h5_source_dir(project)
    if not scaffold_exists(project):
        print(
            ">>> lock.dimensions: h5/ not present — Agent creates Vite tree per "
            "docs/H5壳Vite工程规范.md (no template copy)"
        )
        sync_h5_dev_entry_urls(project)
        return None
    ensure_vite_lan_server(dst)
    ensure_public_native_img_symlink(dst, project)
    ensure_public_vault_symlink(dst, p)
    mock_changed = ensure_browser_bridge_mock(
        dst,
        app_name_lower=_app_name_lower_for_project(project, app_name),
    )
    if mock_changed:
        print(f">>> lock.dimensions: browser bridge mock → {', '.join(mock_changed)}")
    sync_h5_dev_entry_urls(project)
    return dst


def registration_h5_vite_fields() -> dict[str, str]:
    return {
        "h5SourceRoot": H5_SOURCE_ROOT,
        "h5BuildCommand": "npm run build:deploy",
        "h5DevServerPort": "5174",
    }
