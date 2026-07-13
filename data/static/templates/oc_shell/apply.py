#!/usr/bin/env python3
"""Apply the oc_shell template to a concrete app (from Hathoo-OC reference)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def _prefix_cap(prefix: str) -> str:
    p = (prefix or "").strip()
    if not p:
        return "App"
    return p[0].upper() + p[1:]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply oc_shell template placeholders.")
    parser.add_argument("--src", required=True, help="Path to {{APP_NAME}} template root")
    parser.add_argument("--dst", default="", help="Destination workspace root")
    parser.add_argument("--app-name", required=True, help="App display name (PascalCase)")
    parser.add_argument("--prefix", required=True, help="Obfuscated prefix (lowercase)")
    parser.add_argument("--app-slug", required=True, help="H5 remote slug")
    parser.add_argument("--h5-host", required=True, help="H5 production host")
    parser.add_argument("--bundle-id", required=True, help="iOS bundle identifier")
    parser.add_argument("--team-id", default="", help="Apple development team ID")
    parser.add_argument("--asset-scheme", required=True, help="WKURLSchemeHandler scheme")
    parser.add_argument("--callback-scheme", default="app-callback", help="Native→H5 callback URL scheme")
    return parser.parse_args()


def build_values(args: argparse.Namespace) -> dict[str, str]:
    cap = _prefix_cap(args.prefix)
    root = Path(__file__).resolve().parents[4]
    scripts = root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from batch.h5_site_paths import H5_VITE_DEV_PORT, h5_dev_entry_url

    values = {
        "{{APP_NAME}}": args.app_name,
        "{{APP_NAME_LOWER}}": args.app_name.lower(),
        "{{PREFIX}}": args.prefix,
        "{{PREFIX_CAP}}": cap,
        "{{APP_SLUG}}": args.app_slug,
        "{{H5_HOST}}": args.h5_host,
        "{{H5_ENTRY_URL}}": h5_dev_entry_url(),
        "{{H5_DEV_PORT}}": str(H5_VITE_DEV_PORT),
        "{{BUNDLE_ID}}": args.bundle_id,
        "{{TEAM_ID}}": args.team_id or "",
        "{{ASSET_SCHEME}}": args.asset_scheme,
        "{{CALLBACK_SCHEME}}": args.callback_scheme,
    }
    from batch.native_launch_style import default_launch_style_values

    values.update(default_launch_style_values())
    return values


def substitute_in_text(text: str, values: dict[str, str]) -> str:
    for placeholder, value in values.items():
        text = text.replace(placeholder, value)
    return text


def rename_path(path: Path, values: dict[str, str]) -> Path:
    new_name = substitute_in_text(path.name, values)
    if new_name == path.name:
        return path
    new_path = path.with_name(new_name)
    path.rename(new_path)
    return new_path


def _sanitize_pbxproj_team(text: str, team_id: str) -> str:
    """pbxproj must not contain `DEVELOPMENT_TEAM = ;` (invalid when team id empty)."""
    tid = (team_id or "").strip()
    if tid:
        return text
    import re

    return re.sub(r"\t\t\t\tDEVELOPMENT_TEAM = \"\";\n", "", text)


def apply_template(src: Path, dst: Path | None, values: dict[str, str]) -> Path:
    if dst is None:
        dst = src.with_name(values["{{APP_NAME}}"])
    if dst.exists() and dst != src:
        shutil.rmtree(dst)
    if dst != src:
        shutil.copytree(src, dst)

    paths = sorted(dst.rglob("*"), key=lambda p: len(p.parts), reverse=True)
    for path in paths:
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
                new_text = substitute_in_text(text, values)
                if new_text != text:
                    path.write_text(new_text, encoding="utf-8")
            except UnicodeDecodeError:
                pass
        rename_path(path, values)
    rename_path(dst, values)
    team_id = values.get("{{TEAM_ID}}", "")
    for pbx in dst.rglob("project.pbxproj"):
        try:
            raw = pbx.read_text(encoding="utf-8")
            cleaned = _sanitize_pbxproj_team(raw, team_id)
            if cleaned != raw:
                pbx.write_text(cleaned, encoding="utf-8")
        except OSError:
            pass
    _enforce_no_storekit(dst)
    _apply_shell_placeholders(dst, values)
    return dst


def _apply_shell_placeholders(dst: Path, values: dict[str, str]) -> None:
    root = Path(__file__).resolve().parents[4]
    scripts = root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from batch.h5_shell_placeholders import apply_shell_placeholders

    prefix = values.get("{{PREFIX}}", "")
    changed = apply_shell_placeholders(dst, prefix=prefix, force=True)
    for rel in changed:
        print(f"  >>> Shell placeholder: {rel}")
    from batch.native_launch_style import sync_oc_host_launch_ui

    synced = sync_oc_host_launch_ui(dst, write=True)
    if synced is not None:
        print(f"  >>> Native launch UI: {synced.relative_to(dst)}")


def _enforce_no_storekit(dst: Path) -> None:
    root = Path(__file__).resolve().parents[4]
    scripts = root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from batch.native_iap_policy import enforce_no_storekit

    changed = enforce_no_storekit(dst)
    for rel in changed:
        print(f"  >>> IAP policy: removed/forbidden StoreKit artifact: {rel}")


def main() -> int:
    args = parse_args()
    src = Path(args.src).resolve()
    if not src.is_dir():
        print(f"Source path does not exist: {src}", file=sys.stderr)
        return 1

    dst = Path(args.dst).resolve() if args.dst else None
    values = build_values(args)
    final = apply_template(src, dst, values)
    print(f"Applied oc_shell template to: {final}")

    manifest_path = Path(__file__).resolve().parent / "template.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        locked = manifest.get("lockedBridge", {})
        print("Locked bridge station:")
        for dim, val in locked.items():
            print(f"  {dim}: {val}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
