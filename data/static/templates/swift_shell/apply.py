#!/usr/bin/env python3
"""Apply the swift_shell template to a concrete app.

Usage:
    python apply.py \
        --src ./{{APP_NAME}} \
        --app-name MyApp \
        --prefix myprx \
        --app-slug myapp \
        --h5-host test.darin.beauty \
        --bundle-id com.example.myapp \
        --team-id XXXXXXXXXX \
        --asset-scheme myapp-asset \
        [--dst ./MyApp]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


PLACEHOLDERS = {
    "{{APP_NAME}}": "app_name",
    "{{APP_NAME_LOWER}}": "app_name_lower",
    "{{PREFIX}}": "prefix",
    "{{APP_SLUG}}": "app_slug",
    "{{H5_HOST}}": "h5_host",
    "{{BUNDLE_ID}}": "bundle_id",
    "{{TEAM_ID}}": "team_id",
    "{{ASSET_SCHEME}}": "asset_scheme",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply swift_shell template placeholders.")
    parser.add_argument("--src", required=True, help="Path to copied {{APP_NAME}} template root")
    parser.add_argument("--dst", default="", help="Destination root (default: src with app name)")
    parser.add_argument("--app-name", required=True, help="App display name (PascalCase)")
    parser.add_argument("--prefix", required=True, help="Obfuscated prefix (lowercase)")
    parser.add_argument("--app-slug", required=True, help="H5 remote slug")
    parser.add_argument("--h5-host", required=True, help="H5 production host")
    parser.add_argument("--bundle-id", required=True, help="iOS bundle identifier")
    parser.add_argument("--team-id", required=True, help="Apple development team ID")
    parser.add_argument("--asset-scheme", required=True, help="Custom URL scheme for local assets")
    return parser.parse_args()


def build_values(args: argparse.Namespace) -> dict[str, str]:
    root = Path(__file__).resolve().parents[4]
    scripts = root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from batch.h5_site_paths import h5_dev_entry_url

    return {
        "{{APP_NAME}}": args.app_name,
        "{{APP_NAME_LOWER}}": args.app_name.lower(),
        "{{PREFIX}}": args.prefix,
        "{{APP_SLUG}}": args.app_slug,
        "{{H5_HOST}}": args.h5_host,
        "{{H5_ENTRY_URL}}": h5_dev_entry_url(),
        "{{BUNDLE_ID}}": args.bundle_id,
        "{{TEAM_ID}}": args.team_id,
        "{{ASSET_SCHEME}}": args.asset_scheme,
    }


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


def apply_template(src: Path, dst: Path | None, values: dict[str, str]) -> Path:
    if dst is None:
        dst = src.with_name(values["{{APP_NAME}}"])
    if dst.exists() and dst != src:
        shutil.rmtree(dst)
    if dst != src:
        shutil.copytree(src, dst)

    # Process deepest paths first so directory renames do not invalidate child paths.
    paths = sorted(dst.rglob("*"), key=lambda p: len(p.parts), reverse=True)

    for path in paths:
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
                new_text = substitute_in_text(text, values)
                if new_text != text:
                    path.write_text(new_text, encoding="utf-8")
            except UnicodeDecodeError:
                # Binary files are skipped.
                pass
        rename_path(path, values)

    rename_path(dst, values)
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


def main() -> int:
    args = parse_args()
    src = Path(args.src).resolve()
    if not src.exists():
        print(f"Source path does not exist: {src}", file=sys.stderr)
        return 1

    dst = Path(args.dst).resolve() if args.dst else None
    values = build_values(args)

    final = apply_template(src, dst, values)
    print(f"Applied swift_shell template to: {final}")

    # Generate Xcode project if project.yml is present and xcodegen is available.
    project_yml = final / "project.yml"
    if project_yml.is_file():
        try:
            result = subprocess.run(
                ["xcodegen", "generate", "--spec", str(project_yml), "--project", str(final)],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"Generated Xcode project: {final / values['{{APP_NAME}}']}.xcodeproj")
            else:
                print(
                    f"xcodegen not available or failed (exit {result.returncode}); "
                    "run 'xcodegen generate' manually on macOS to create the .xcodeproj.",
                    file=sys.stderr,
                )
        except FileNotFoundError:
            print(
                "xcodegen not found; skip .xcodeproj generation. "
                "Install xcodegen (brew install xcodegen) and run 'xcodegen generate' on macOS.",
                file=sys.stderr,
            )

    # Print a summary of the locked bridge station for verification.
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
