"""Materialize Designer's `本包视觉锁.json.assetBrief` slots.

The script no longer downloads from the network or synthesizes real artwork.
For every non-icon slot it:

1. writes a uniform palette-tinted placeholder PNG to the workspace, and
2. records one structured entry in ``image_prompts.{md,json}``.

Icon-class slots are skipped — those render via icon fonts at runtime
(`font_awesome_flutter` or Flutter built-in `Icons.*`).

A downstream agent reads ``image_prompts.json`` / ``image_prompts.md`` to replace
each placeholder with finished artwork (Cursor Agent image generation — not stock APIs).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from batch.image_compress import compress_workspace_images
from batch.image_placeholders import (
    DEFAULT_SIZE,
    ImagePromptEntry,
    PromptManifest,
    build_prompt_text,
    is_icon_slot,
    palette_anchors_hex,
    palette_from_color_tokens,
    recommended_size_for,
    source_hints_for,
    write_placeholder,
    write_prompts_manifest,
)

VISUAL_LOCK_FILE = "本包视觉锁.json"


@dataclass
class AssetReport:
    app: str
    total: int = 0
    placeholders: int = 0
    icon_skipped: int = 0
    failed: list[str] = field(default_factory=list)


def _basename_key(path: str) -> str:
    return Path(str(path or "")).stem


def _icon_font_block(lock: dict) -> dict[str, str]:
    """Read Designer's iconography selection, defaulting to FontAwesome + Material."""
    icono = lock.get("iconography") or {}
    if isinstance(icono, dict):
        family = str(icono.get("family") or "").strip()
        package = str(icono.get("package") or "").strip()
        if family or package:
            return {
                "family": family or "FontAwesome + Material Icons",
                "package": package or "font_awesome_flutter ^10.4.0",
            }
    return {
        "family": "FontAwesome + Material Icons",
        "package": "font_awesome_flutter ^10.4.0  (or built-in Icons.*)",
    }


def _parse_size_override(rec: object) -> tuple[int, int] | None:
    if isinstance(rec, (list, tuple)) and len(rec) == 2:
        try:
            return (int(rec[0]), int(rec[1]))
        except (TypeError, ValueError):
            return None
    if isinstance(rec, str):
        for sep in ("x", "X", "×", "*"):
            if sep in rec:
                parts = rec.split(sep)
                if len(parts) == 2:
                    try:
                        return (int(parts[0].strip()), int(parts[1].strip()))
                    except ValueError:
                        return None
                break
    return None


def fill_visual_lock_assets(
    workspace: Path,
    flutter_dir: Path,
    app_name: str,
) -> AssetReport:
    """Produce placeholders + ``image_prompts.{md,json}`` from 视觉锁 assetBrief."""
    lock_path = workspace / VISUAL_LOCK_FILE
    report = AssetReport(app=app_name)
    if not lock_path.is_file():
        report.failed.append(f"missing {VISUAL_LOCK_FILE}")
        return report

    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.failed.append(f"invalid JSON in {VISUAL_LOCK_FILE}: {exc}")
        return report

    brief = lock.get("assetBrief") or []
    color_tokens = lock.get("colorTokens") or {}
    palette_rgb = palette_from_color_tokens(color_tokens)
    palette_hex = palette_anchors_hex(color_tokens)
    report.total = len(brief)

    manifest_path = flutter_dir / "image_prompts.json"
    manifest = _load_or_init_manifest(manifest_path, app_name)
    manifest.iconFont = _icon_font_block(lock)
    seen_paths = {e.path for e in manifest.entries}

    for slot in brief:
        if not isinstance(slot, dict):
            continue
        rel = str(slot.get("path") or "").strip()
        if not rel:
            continue
        role = str(slot.get("role") or "").strip()
        description = str(slot.get("description") or "").strip()
        keyword = str(slot.get("keyword") or "").strip()
        basename = _basename_key(rel)

        if is_icon_slot(role, rel):
            report.icon_skipped += 1
            if rel not in seen_paths:
                manifest.add(
                    ImagePromptEntry(
                        path=rel,
                        role=role,
                        basename=basename,
                        recommendedSize="—",
                        skipped=True,
                        skipReason="icon font (FontAwesome / Material Icons)",
                    )
                )
                seen_paths.add(rel)
            continue

        size = recommended_size_for(
            role, rel, _parse_size_override(slot.get("recommendedSize"))
        )

        dest = flutter_dir / rel
        try:
            write_placeholder(
                dest,
                role=role or "asset",
                basename=basename,
                palette_anchors=palette_rgb,
                size=size,
            )
        except OSError as exc:
            report.failed.append(f"{rel}: {exc}")
            continue
        report.placeholders += 1

        if rel in seen_paths:
            continue
        slot_palette = list(slot.get("paletteAnchors") or []) or palette_hex
        prompt = str(slot.get("imagePrompt") or "").strip() or build_prompt_text(
            app=app_name,
            role=role,
            basename=basename,
            description=description,
            keyword=keyword,
            palette_hex=slot_palette,
        )
        sources = list(slot.get("sourceHints") or []) or source_hints_for(
            role, basename, keyword or description
        )
        manifest.add(
            ImagePromptEntry(
                path=rel,
                role=role or "asset",
                basename=basename,
                recommendedSize=f"{size[0]}×{size[1]}",
                paletteAnchors=slot_palette,
                prompt=prompt,
                sourceHints=sources,
                description=description,
            )
        )
        seen_paths.add(rel)

    write_prompts_manifest(flutter_dir, manifest)
    compress_workspace_images(flutter_dir)
    return report


def _load_or_init_manifest(json_path: Path, app: str) -> PromptManifest:
    """Load an existing image_prompts.json (so multiple callers can append) or start fresh."""
    if json_path.is_file():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict):
            manifest = PromptManifest(
                app=str(data.get("app") or app),
                iconFont=dict(data.get("iconFont") or {}),
            )
            for raw in data.get("entries") or []:
                if not isinstance(raw, dict):
                    continue
                manifest.add(
                    ImagePromptEntry(
                        path=str(raw.get("path") or ""),
                        role=str(raw.get("role") or ""),
                        basename=str(raw.get("basename") or ""),
                        recommendedSize=str(raw.get("recommendedSize") or "—"),
                        paletteAnchors=list(raw.get("paletteAnchors") or []),
                        prompt=str(raw.get("prompt") or ""),
                        sourceHints=list(raw.get("sourceHints") or []),
                        description=str(raw.get("description") or ""),
                        skipped=bool(raw.get("skipped")),
                        skipReason=str(raw.get("skipReason") or ""),
                    )
                )
            return manifest
    return PromptManifest(app=app)


from batch.csv_tasks import OUTPUT_CONTAINER_SUFFIXES


def _find_workspace(batch_dir: Path, app: str) -> tuple[Path, Path] | None:
    for suffix in OUTPUT_CONTAINER_SUFFIXES:
        root = batch_dir / f"{app}{suffix}"
        if not root.is_dir():
            continue
        direct = root / app
        if direct.is_dir():
            return direct, direct
        for child in root.iterdir():
            if child.is_dir() and (child / VISUAL_LOCK_FILE).is_file():
                return child, child
    return None


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(
        description="Emit placeholders + image_prompts for 本包视觉锁."
    )
    parser.add_argument(
        "--batch-dir",
        type=Path,
        required=True,
        help="Output batch directory (e.g. output/20260614-002-87-0615)",
    )
    parser.add_argument(
        "--app",
        action="append",
        dest="apps",
        help="Limit to app name(s); default all *-Swift / *-OC / *-Flutter dirs",
    )
    args = parser.parse_args(argv)

    batch_dir = args.batch_dir.expanduser().resolve()
    if not batch_dir.is_dir():
        print(f"Batch dir not found: {batch_dir}", file=sys.stderr)
        return 1

    app_dirs: set[str] = set()
    for p in batch_dir.iterdir():
        if not p.is_dir():
            continue
        for suffix in OUTPUT_CONTAINER_SUFFIXES:
            if p.name.endswith(suffix):
                app_dirs.add(p.name[: -len(suffix)])
                break
    app_dirs_sorted = sorted(app_dirs)
    if args.apps:
        app_dirs_sorted = [a for a in app_dirs_sorted if a in set(args.apps)]

    exit_code = 0
    for app in app_dirs_sorted:
        found = _find_workspace(batch_dir, app)
        if not found:
            print(f"[{app}] skip — workspace not found")
            continue
        workspace, flutter_dir = found
        brief_count = len(
            json.loads((workspace / VISUAL_LOCK_FILE).read_text(encoding="utf-8")).get(
                "assetBrief", []
            )
        )
        print(f"[{app}] processing {brief_count} assetBrief slots ...")
        report = fill_visual_lock_assets(workspace, flutter_dir, app)
        print(
            f"[{app}] done: total={report.total} placeholders={report.placeholders} "
            f"icon_skipped={report.icon_skipped} failed={len(report.failed)}"
        )
        if report.failed:
            exit_code = 1
            for item in report.failed:
                print(f"  - {item}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "VISUAL_LOCK_FILE",
    "DEFAULT_SIZE",
    "AssetReport",
    "fill_visual_lock_assets",
    "main",
]
