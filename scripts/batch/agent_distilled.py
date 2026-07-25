"""Resolve + project global-brain agent-distilled into the package workspace.

Source of truth stays in global-brain. The pipeline repo does **not** store a
copy of the corpus — only absolute path config and this projector.

``sync.distilled`` (V3 step after ``lock.dimensions``) clears then copies into
``skill-input/distilled/``. Missing source → WARN, step still succeeds.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from batch.config import BatchConfig

# Defaults mirror BatchConfig / config.yaml.example (absolute paths).
DEFAULT_SOURCE_WIN = (
    r"E:\projects\global-brain\1_项目\h5-shell-pipeline\agent-distilled"
)
DEFAULT_SOURCE_MAC = (
    "/Users/ios-dev/Desktop/projects/global-brain/"
    "1_项目/h5-shell-pipeline/agent-distilled"
)

DISTILLED_REL = "skill-input/distilled"
DISTILLED_MANIFEST_REL = "skill-input/distilled-manifest.json"

# Role trees only — skip human-only README / MANIFEST (may mention brain paths).
_COPY_SUBDIRS: tuple[str, ...] = ("shared", "plan", "shell", "h5")

# role_slug → distilled subdirs (always include shared when present).
_ROLE_DISTILLED_SUBDIRS: dict[str, tuple[str, ...]] = {
    "build-agent-plan-spec": ("shared", "plan"),
    "build-agent-plan-pack": ("shared", "plan"),
    "build-agent-plan": ("shared", "plan"),
    "build-agent-shell": ("shared", "shell"),
    "build-agent-h5": ("shared", "h5"),
}


def distilled_focus_file_lines(
    workspace: Path,
    *,
    role_slug: str,
) -> list[str]:
    """Bullet lines for projected ``.md`` files under skill-input/distilled/.

    Empty when sync.distilled has not run or source was skipped.
    """
    root = workspace.expanduser().resolve() / DISTILLED_REL
    if not root.is_dir():
        return []
    subdirs = _ROLE_DISTILLED_SUBDIRS.get(
        role_slug.strip(),
        ("shared", "plan", "shell", "h5"),
    )
    lines: list[str] = []
    for sub in subdirs:
        folder = root / sub
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.md")):
            rel = f"{DISTILLED_REL}/{sub}/{path.name}".replace("\\", "/")
            lines.append(f"   - `{rel}`")
    return lines


def platform_source_dir(cfg: BatchConfig, *, platform: str | None = None) -> str:
    """Pick win/mac absolute path for the current (or given) platform."""
    plat = (platform or sys.platform).lower()
    override = (cfg.agent_distilled_source_dir or "").strip()
    if override:
        return override
    if plat.startswith("win"):
        return (cfg.agent_distilled_source_dir_win or DEFAULT_SOURCE_WIN).strip()
    if plat == "darwin":
        return (cfg.agent_distilled_source_dir_mac or DEFAULT_SOURCE_MAC).strip()
    # Linux CI / other: prefer explicit override; else try mac-style path then win.
    mac = (cfg.agent_distilled_source_dir_mac or DEFAULT_SOURCE_MAC).strip()
    win = (cfg.agent_distilled_source_dir_win or DEFAULT_SOURCE_WIN).strip()
    return mac or win


def resolve_agent_distilled_source(
    cfg: BatchConfig,
    *,
    platform: str | None = None,
    warn: bool = True,
) -> Path | None:
    """Return the agent-distilled directory if enabled and present.

    Priority for path string:
    1. ``agent_distilled_source_dir`` / ``AGENT_DISTILLED_SOURCE`` (any OS)
    2. win → ``source_dir_win``; darwin → ``source_dir_mac``
    """
    if not cfg.agent_distilled_enabled:
        return None
    raw = platform_source_dir(cfg, platform=platform)
    if not raw:
        if warn:
            print(
                ">>> [WARN] agent_distilled: enabled but source path empty; skip"
            )
        return None
    path = Path(raw).expanduser()
    if path.is_dir():
        return path.resolve()
    if warn:
        print(
            f">>> [WARN] agent_distilled: source not found, skip — {path}"
        )
    return None


def _list_projected_files(dest: Path) -> list[str]:
    if not dest.is_dir():
        return []
    out: list[str] = []
    for p in sorted(dest.rglob("*")):
        if p.is_file():
            out.append(p.relative_to(dest).as_posix())
    return out


def copy_agent_distilled(
    cfg: BatchConfig,
    workspace: Path,
    *,
    platform: str | None = None,
    warn: bool = True,
) -> dict[str, object]:
    """Clear ``skill-input/distilled/`` and project role trees from the source.

    Returns a small result dict (also written to ``distilled-manifest.json``).
    Always non-raising for missing source when enabled — caller treats as OK.
    """
    dest = workspace / DISTILLED_REL
    manifest_path = workspace / DISTILLED_MANIFEST_REL
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    if dest.exists():
        shutil.rmtree(dest)

    source = resolve_agent_distilled_source(
        cfg, platform=platform, warn=warn
    )
    if source is None:
        result: dict[str, object] = {
            "ok": False,
            "skipped": True,
            "reason": "source_missing_or_disabled",
            "dest": DISTILLED_REL,
            "copied_files": [],
            "generated_at": ts,
        }
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return result

    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    for name in _COPY_SUBDIRS:
        src_sub = source / name
        if not src_sub.is_dir():
            continue
        shutil.copytree(src_sub, dest / name)
        copied += 1

    files = _list_projected_files(dest)
    result = {
        "ok": True,
        "skipped": False,
        "source": str(source),
        "source_basename": source.name,
        "dest": DISTILLED_REL,
        "subdirs_copied": [n for n in _COPY_SUBDIRS if (dest / n).is_dir()],
        "copied_files": files,
        "file_count": len(files),
        "generated_at": ts,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if warn:
        print(
            f">>> sync.distilled: projected {len(files)} files → {DISTILLED_REL}/ "
            f"(from {source})"
        )
    return result
