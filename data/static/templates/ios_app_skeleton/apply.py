#!/usr/bin/env python3
"""Apply ios_app_skeleton placeholders to a concrete app tree.

Usage:
    python apply.py \
        --src './{{APP_NAME}}' \
        --app-name MyApp \
        --bundle-id com.example.myapp \
        [--team-id ''] \
        [--dst ./MyApp]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply ios_app_skeleton placeholders.")
    parser.add_argument("--src", required=True, help="Path to copied {{APP_NAME}} template root")
    parser.add_argument("--dst", default="", help="Destination root (default: src with app name)")
    parser.add_argument("--app-name", required=True, help="App display name (PascalCase)")
    parser.add_argument("--bundle-id", required=True, help="iOS bundle identifier")
    parser.add_argument("--team-id", default="", help="Apple development team ID (may be empty)")
    return parser.parse_args()


def build_values(args: argparse.Namespace) -> dict[str, str]:
    return {
        "{{APP_NAME}}": args.app_name,
        "{{APP_NAME_LOWER}}": args.app_name.lower(),
        "{{BUNDLE_ID}}": args.bundle_id,
        "{{TEAM_ID}}": args.team_id,
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
    else:
        dst = src

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

    return rename_path(dst, values)


def main() -> int:
    args = parse_args()
    src = Path(args.src).resolve()
    if not src.exists():
        print(f"Source path does not exist: {src}", file=sys.stderr)
        return 1

    dst = Path(args.dst).resolve() if args.dst else None
    values = build_values(args)
    final = apply_template(src, dst, values)
    print(f"Applied ios_app_skeleton to: {final}")
    xcodeproj = final / f"{values['{{APP_NAME}}']}.xcodeproj" / "project.pbxproj"
    if not xcodeproj.is_file():
        print(f"Missing project.pbxproj at {xcodeproj}", file=sys.stderr)
        return 1
    print(f"Xcode project: {xcodeproj.parent}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
