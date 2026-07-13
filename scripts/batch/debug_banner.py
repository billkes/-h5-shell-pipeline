"""Ensure MaterialApp debugShowCheckedModeBanner: false in Flutter projects."""

from __future__ import annotations

import re
from pathlib import Path

_MATERIAL_APP_RE = re.compile(r"\bMaterialApp\s*\(")
_DEBUG_BANNER_FALSE_RE = re.compile(
    r"debugShowCheckedModeBanner\s*:\s*false",
    re.MULTILINE,
)


def _indent_at(text: str, pos: int) -> str:
    """Return the whitespace indentation of the line containing ``pos``."""
    line_start = text.rfind("\n", 0, pos) + 1
    line = text[line_start:pos]
    stripped = line.lstrip()
    if stripped:
        return line[: len(line) - len(stripped)]
    return line


def _fix_file(text: str) -> str | None:
    """Insert debugShowCheckedModeBanner: false into every MaterialApp call that lacks it.

    Returns the modified text, or ``None`` if no changes were needed.
    """
    changed = False
    # Process from end to start so indices remain valid after insertions.
    for match in reversed(list(_MATERIAL_APP_RE.finditer(text))):
        open_pos = match.end()

        # Find the closing parenthesis of this MaterialApp call.
        depth = 1
        i = open_pos
        while i < len(text) and depth > 0:
            ch = text[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            i += 1
        if depth != 0:
            continue
        call_body = text[open_pos:i]

        if _DEBUG_BANNER_FALSE_RE.search(call_body):
            continue

        base_indent = _indent_at(text, match.start())
        inner_indent = base_indent + "  "
        insertion = f"\n{inner_indent}debugShowCheckedModeBanner: false,"

        text = text[:open_pos] + insertion + text[open_pos:]
        changed = True

    return text if changed else None


def ensure_debug_banner_false(project_dir: Path) -> list[str]:
    """Auto-fix all lib/ MaterialApp calls missing ``debugShowCheckedModeBanner: false``.

    Returns a list of relative paths that were modified.
    """
    lib_dir = project_dir / "lib"
    if not lib_dir.is_dir():
        return []

    modified: list[str] = []
    for dart_file in sorted(lib_dir.rglob("*.dart")):
        # Skip test helpers / test files.
        if "/test/" in dart_file.as_posix() or dart_file.name.endswith("_test.dart"):
            continue

        original = dart_file.read_text(encoding="utf-8", errors="replace")
        if not _MATERIAL_APP_RE.search(original):
            continue

        fixed = _fix_file(original)
        if fixed is None:
            continue

        dart_file.write_text(fixed, encoding="utf-8")
        modified.append(dart_file.relative_to(project_dir).as_posix())

    return modified


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("用法: debug_banner.py <Flutter 项目根目录>", file=sys.stderr)
        raise SystemExit(2)

    project = Path(sys.argv[1]).resolve()
    changed = ensure_debug_banner_false(project)
    if changed:
        print("已关闭 DEBUG 角标:")
        for path in changed:
            print(f"  - {path}")
        raise SystemExit(0)
    print("DEBUG 角标已关闭或无需修改")
