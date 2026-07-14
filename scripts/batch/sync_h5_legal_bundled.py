"""Sync h5_shell legal MD files into auto-generated vault JavaScript."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def _ensure_scripts_path() -> None:
    scripts_root = Path(__file__).resolve().parents[1]
    if str(scripts_root) not in sys.path:
        sys.path.insert(0, str(scripts_root))


_ensure_scripts_path()

from batch.h5_site_paths import (
    DEFAULT_H5_SOURCE_ROOT,
    site_entry_path,
    site_root_from_register,
    vault_dir_path,
)
from batch.h5_vite_scaffold import h5_source_dir, scaffold_exists
from batch.h5_vite_gate import vite_vue_and_ts_text
from batch.pack_type import is_h5_shell

REGISTER_FILE = "本包登记信息.json"

PRIVACY_MD_GLOB = "* Privacy Agreement.md"
TERMS_MD_GLOB = "* User Agreement.md"

PRIVACY_REQUIRED_HEADINGS = ("Children's Privacy",)
TERMS_REQUIRED_HEADINGS = ("Limitation of Liability",)

PRIVACY_CANON_SECTIONS: dict[str, str] = {
    "Children's Privacy": (
        "## Children's Privacy\n\n"
        "{app_name} is intended for users aged 18 and older. We do not knowingly "
        "collect personal information from children under 13. All app data remains "
        "on your device; delete the app to remove local data. If you believe a "
        "child has provided information, contact {contact}."
    ),
}

TERMS_CANON_SECTIONS: dict[str, str] = {
    "Limitation of Liability": (
        "## Limitation of Liability\n\n"
        'TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, {app_name} IS PROVIDED '
        '"AS IS" WITHOUT WARRANTIES OF ANY KIND. THE PUBLISHER SHALL NOT BE LIABLE '
        "FOR INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES "
        "ARISING FROM USE OF THE APP."
    ),
}

HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
JS_STRING_RE = re.compile(
    r"(privacy|terms):\s*(\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')",
    re.DOTALL,
)
INLINE_LEGAL_RE = re.compile(
    r"NS\.ui\.LEGAL\s*=\s*\{",
    re.IGNORECASE,
)


def _read_register(project: Path) -> dict:
    path = project / REGISTER_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def is_h5_shell_project(project: Path) -> bool:
    reg = _read_register(project)
    return is_h5_shell(str(reg.get("packType") or ""))


def find_privacy_md(project: Path) -> Path | None:
    matches = sorted(project.glob(PRIVACY_MD_GLOB))
    return matches[0] if matches else None


def find_terms_md(project: Path) -> Path | None:
    matches = sorted(project.glob(TERMS_MD_GLOB))
    return matches[0] if matches else None


def _resolve_app_display_name(project: Path) -> str:
    reg = _read_register(project)
    for key in ("appDisplayName", "appName", "displayName"):
        value = str(reg.get(key) or "").strip()
        if value:
            return value
    folder = project.name.split("-")[0].strip()
    return folder or "App"


def _resolve_contact_email(project: Path, app_name: str) -> str:
    reg = _read_register(project)
    for key in ("supportEmail", "contactEmail", "legalContact"):
        value = str(reg.get(key) or "").strip()
        if value:
            return value
    slug = str(reg.get("appSlug") or app_name).lower()
    return f"support@{slug}.app"


def _md_has_heading(md_text: str, heading: str) -> bool:
    return heading in md_to_plain(md_text)


def _append_canon_sections(
    md_text: str,
    *,
    sections: dict[str, str],
    required: tuple[str, ...],
    app_name: str,
    contact: str,
) -> tuple[str, list[str]]:
    patched = md_text.rstrip()
    actions: list[str] = []
    for heading in required:
        if _md_has_heading(patched, heading):
            continue
        body = sections[heading].format(app_name=app_name, contact=contact)
        patched = f"{patched}\n\n{body}\n"
        actions.append(f"+{heading}")
    return patched, actions


def ensure_legal_md_canon(project: Path, *, write: bool = True) -> list[str]:
    """Ensure legal MD files include gate-required headings."""
    project = project.expanduser().resolve()
    if not is_h5_shell_project(project):
        return []

    app_name = _resolve_app_display_name(project)
    contact = _resolve_contact_email(project, app_name)
    actions: list[str] = []

    privacy_md = find_privacy_md(project)
    if privacy_md is not None:
        text = privacy_md.read_text(encoding="utf-8")
        patched, added = _append_canon_sections(
            text,
            sections=PRIVACY_CANON_SECTIONS,
            required=PRIVACY_REQUIRED_HEADINGS,
            app_name=app_name,
            contact=contact,
        )
        if added:
            actions.extend(f"privacy {item}" for item in added)
            if write:
                privacy_md.write_text(patched, encoding="utf-8")

    terms_md = find_terms_md(project)
    if terms_md is not None:
        text = terms_md.read_text(encoding="utf-8")
        patched, added = _append_canon_sections(
            text,
            sections=TERMS_CANON_SECTIONS,
            required=TERMS_REQUIRED_HEADINGS,
            app_name=app_name,
            contact=contact,
        )
        if added:
            actions.extend(f"terms {item}" for item in added)
            if write:
                terms_md.write_text(patched, encoding="utf-8")

    return actions


def md_to_plain(text: str) -> str:
    """Convert legal MD (headings + paragraphs) to plain text for H5 display."""
    out: list[str] = []
    prev_blank = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if not prev_blank and out:
                out.append("")
            prev_blank = True
            continue
        prev_blank = False
        heading = HEADING_RE.match(line)
        if heading:
            title = BOLD_RE.sub(r"\1", heading.group(2).strip())
            if out and out[-1] != "":
                out.append("")
            out.append(title)
            out.append("")
            continue
        out.append(BOLD_RE.sub(r"\1", line))
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    normalized: list[str] = []
    blank = False
    for line in out:
        if line == "":
            if not blank:
                normalized.append("")
            blank = True
        else:
            normalized.append(line)
            blank = False
    return "\n".join(normalized)


def normalize_for_compare(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def resolve_prefix(project: Path) -> str:
    reg = _read_register(project)
    anti = reg.get("codeAntiCorrelation") or {}
    if isinstance(anti, dict):
        prefix = str(anti.get("dartCodePrefix") or "").strip()
        if prefix:
            return prefix
    from batch.workspace import dart_prefix

    return dart_prefix(project)


def resolve_global_ns(project: Path) -> str:
    prefix = resolve_prefix(project)
    return prefix[0].upper() + prefix[1:] if prefix else "App"


def bundled_script_rel(project: Path) -> Path:
    prefix = resolve_prefix(project)
    if scaffold_exists(project) or h5_source_dir(project).is_dir():
        return Path(DEFAULT_H5_SOURCE_ROOT) / "src" / "legal" / f"{prefix}_legal_bundled.ts"
    reg = _read_register(project)
    vault = site_root_from_register(reg).rstrip("/")
    return Path(vault) / f"{prefix}_panels" / f"{prefix}_legal_bundled.js"


def bundled_script_path(project: Path) -> Path:
    return project / bundled_script_rel(project)


def entry_htm_path(project: Path) -> Path:
    return site_entry_path(project)


def core_js_path(project: Path) -> Path:
    rel = bundled_script_rel(project)
    prefix = resolve_prefix(project)
    return project / rel.parent / f"{prefix}_core.js"


def render_bundled_ts(
    *,
    privacy_text: str,
    terms_text: str,
    privacy_src: str,
    terms_src: str,
    global_ns: str,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    privacy_json = json.dumps(privacy_text, ensure_ascii=False)
    terms_json = json.dumps(terms_text, ensure_ascii=False)
    return (
        "/* AUTO-GENERATED by sync_h5_legal_bundled.py — DO NOT EDIT */\n"
        f"/* generatedAt: {generated_at} */\n"
        f"/* privacySource: {privacy_src} */\n"
        f"/* termsSource: {terms_src} */\n"
        f"export const LEGAL = {{\n"
        f"  privacy: {privacy_json},\n"
        f"  terms: {terms_json},\n"
        "};\n\n"
        f"declare global {{\n"
        f"  interface Window {{\n"
        f"    {global_ns}?: {{ ui?: {{ LEGAL?: typeof LEGAL }} }};\n"
        f"  }}\n"
        f"}}\n\n"
        f"if (typeof window !== 'undefined') {{\n"
        f"  const root = window as Window & Record<string, unknown>;\n"
        f"  root.{global_ns} = root.{global_ns} || {{}};\n"
        f"  const ui = (root.{global_ns}.ui = root.{global_ns}.ui || {{}});\n"
        f"  ui.LEGAL = LEGAL;\n"
        f"}}\n"
    )


def render_bundled_js(
    *,
    privacy_text: str,
    terms_text: str,
    privacy_src: str,
    terms_src: str,
    global_ns: str,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    privacy_json = json.dumps(privacy_text, ensure_ascii=False)
    terms_json = json.dumps(terms_text, ensure_ascii=False)
    return (
        "/* AUTO-GENERATED by sync_h5_legal_bundled.py — DO NOT EDIT */\n"
        f"/* generatedAt: {generated_at} */\n"
        f"/* privacySource: {privacy_src} */\n"
        f"/* termsSource: {terms_src} */\n"
        "(function (global) {\n"
        "  'use strict';\n"
        f"  var NS = global.{global_ns} = global.{global_ns} || {{}};\n"
        "  NS.ui = NS.ui || {};\n"
        "  NS.ui.LEGAL = {\n"
        f"    privacy: {privacy_json},\n"
        f"    terms: {terms_json}\n"
        "  };\n"
        "})(typeof window !== 'undefined' ? window : globalThis);\n"
    )


def extract_legal_from_js(js_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("privacy", "terms"):
        match = re.search(rf"{key}:\s*(\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')", js_text)
        if not match:
            continue
        out[key] = json.loads(match.group(1))
    return out


def load_expected_legal(project: Path) -> tuple[dict[str, str], dict[str, str]]:
    privacy_md = find_privacy_md(project)
    terms_md = find_terms_md(project)
    if privacy_md is None or terms_md is None:
        missing = []
        if privacy_md is None:
            missing.append(PRIVACY_MD_GLOB)
        if terms_md is None:
            missing.append(TERMS_MD_GLOB)
        raise FileNotFoundError(f"Missing legal MD: {', '.join(missing)}")
    privacy_text = md_to_plain(privacy_md.read_text(encoding="utf-8"))
    terms_text = md_to_plain(terms_md.read_text(encoding="utf-8"))
    meta = {
        "privacy": privacy_md.name,
        "terms": terms_md.name,
    }
    return {"privacy": privacy_text, "terms": terms_text}, meta


def sync_h5_legal_bundled(project: Path, *, write: bool = True) -> Path:
    project = project.expanduser().resolve()
    if not is_h5_shell_project(project):
        raise ValueError(f"Not an h5_shell project: {project}")

    ensure_legal_md_canon(project, write=write)
    expected, meta = load_expected_legal(project)
    out_path = bundled_script_path(project)
    use_ts = out_path.suffix == ".ts"
    if use_ts:
        content = render_bundled_ts(
            privacy_text=expected["privacy"],
            terms_text=expected["terms"],
            privacy_src=meta["privacy"],
            terms_src=meta["terms"],
            global_ns=resolve_global_ns(project),
        )
    else:
        content = render_bundled_js(
            privacy_text=expected["privacy"],
            terms_text=expected["terms"],
            privacy_src=meta["privacy"],
            terms_src=meta["terms"],
            global_ns=resolve_global_ns(project),
        )
    if write:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
    return out_path


def verify_h5_legal_bundled(project: Path, *, project_dir: Path | None = None) -> list[str]:
    """Return issue strings; empty means OK."""
    project = project.expanduser().resolve()
    issues: list[str] = []

    if not is_h5_shell_project(project):
        return issues

    from batch.h5_legal_ui import project_needs_legal_ui

    if not project_needs_legal_ui(project):
        return issues

    from batch.h5_legal_md_gate import verify_h5_legal_md

    issues.extend(verify_h5_legal_md(project, project_dir=project_dir))

    try:
        expected, _meta = load_expected_legal(project)
    except FileNotFoundError as exc:
        issues.append(str(exc))
        return issues

    bundled = bundled_script_path(project)
    if not bundled.is_file():
        issues.append(f"MISSING: {bundled.relative_to(project)}")
        return issues

    actual = extract_legal_from_js(bundled.read_text(encoding="utf-8"))
    for key in ("privacy", "terms"):
        if key not in actual:
            issues.append(f"BUNDLED: missing {key} string in {bundled.name}")
            continue
        if normalize_for_compare(actual[key]) != normalize_for_compare(expected[key]):
            ratio = len(actual[key]) / max(len(expected[key]), 1)
            issues.append(
                f"MISMATCH: {key} bundled text differs from MD "
                f"(len {len(actual[key])} vs {len(expected[key])}, ratio {ratio:.2f})"
            )
        min_len = 0.85 * len(expected[key])
        if len(actual[key]) < min_len:
            issues.append(
                f"SHORT: {key} bundled text too short "
                f"({len(actual[key])} < {min_len:.0f})"
            )

    for heading in PRIVACY_REQUIRED_HEADINGS:
        if heading not in expected["privacy"]:
            issues.append(f"MD: privacy missing required heading {heading!r}")
        elif heading not in actual.get("privacy", ""):
            issues.append(f"BUNDLED: privacy missing required section {heading!r}")

    for heading in TERMS_REQUIRED_HEADINGS:
        if heading not in expected["terms"]:
            issues.append(f"MD: terms missing required heading {heading!r}")
        elif heading not in actual.get("terms", ""):
            issues.append(f"BUNDLED: terms missing required section {heading!r}")

    from batch.h5_vite_scaffold import scaffold_exists

    if scaffold_exists(project):
        src_text = vite_vue_and_ts_text(project)
        if bundled.name not in src_text and "LEGAL" not in src_text:
            issues.append(
                f"VITE: h5/src must import {bundled.name} or reference LEGAL export"
            )
    else:
        entry = entry_htm_path(project)
        if entry.is_file():
            rel_script = bundled_script_rel(project).as_posix()
            panels_rel = (
                rel_script.split("/")[-2] + "/" + bundled_script_path(project).name
            )
            entry_text = entry.read_text(encoding="utf-8", errors="ignore")
            if bundled.name not in entry_text:
                issues.append(
                    f"ENTRY: {entry.name} must load {bundled.name} before core.js"
                )
            elif panels_rel not in entry_text and rel_script not in entry_text:
                issues.append(f"ENTRY: script path for {bundled.name} not referenced")
        else:
            issues.append(
                f"MISSING: entry htm at {entry.name if entry else 'bundleEntryPath'}"
            )

        core = core_js_path(project)
        if core.is_file():
            core_text = core.read_text(encoding="utf-8", errors="ignore")
            if INLINE_LEGAL_RE.search(core_text):
                issues.append(
                    f"CORE: remove inline NS.ui.LEGAL from {core.relative_to(project)} "
                    "(use generated legal_bundled.js only)"
                )

    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path, help="Flutter project directory")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Verify bundled JS matches MD without writing",
    )
    args = parser.parse_args(argv)

    project = args.project_dir.expanduser().resolve()
    if not project.is_dir():
        print(f"ERROR: not a directory: {project}", file=sys.stderr)
        return 2

    if not is_h5_shell_project(project):
        print(f"SKIP: not h5_shell ({project.name})")
        return 0

    if args.check_only:
        issues = verify_h5_legal_bundled(project)
        if issues:
            print(f"project: {project.name}")
            for item in issues:
                print(f"  ISSUE: {item}")
            return 1
        print(f"OK: h5 legal bundled matches MD ({project.name})")
        return 0

    try:
        out_path = sync_h5_legal_bundled(project, write=True)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    issues = verify_h5_legal_bundled(project)
    print(f"Wrote: {out_path.relative_to(project)}")
    if issues:
        print("WARN post-sync:")
        for item in issues:
            print(f"  {item}")
        return 1
    print("OK: synced and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
