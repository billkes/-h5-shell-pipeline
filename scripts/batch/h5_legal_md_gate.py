"""Hard gate for {App} Privacy/User Agreement.md — enforces docs/法律协议规范.md."""

from __future__ import annotations

import re
from pathlib import Path

from batch.csv_tasks import load_csv_tasks, parse_privacy_style_number
from batch.sync_h5_legal_bundled import (
    PRIVACY_REQUIRED_HEADINGS,
    TERMS_REQUIRED_HEADINGS,
    find_privacy_md,
    find_terms_md,
    is_h5_shell_project,
)

LEGAL_SPEC_DATE = "Latest Updated: May 18, 2026"

STYLE_MIN_WORDS: dict[int, int] = {
    1: 400,
    2: 700,
    3: 350,
}

GLOBAL_PHRASES: tuple[str, ...] = (
    "zero tolerance",
    "24 hours",
    "filtering methods",
    "user reporting mechanism",
)

REGION_BLOCKLIST_RE = re.compile(
    r"\b("
    r"United States|U\.S\.|USA|California|CCPA|GDPR|European Union|EU\b|"
    r"China|PRC|Hong Kong|Taiwan|Japan|Korea|Singapore|"
    r"UK\b|United Kingdom|Australia|Canada\b|"
    r"GDPR|PIPL|LGPD"
    r")\b",
    re.I,
)

LIST_LINE_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\S")
TABLE_LINE_RE = re.compile(r"^\s*\|.*\|.*\|")
HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")


def resolve_main_name(project: Path) -> str:
    project = project.expanduser().resolve()
    return project.name.split("-")[0].strip() or project.name


def resolve_privacy_style(
    project: Path,
    *,
    project_dir: Path | None = None,
    privacy_style: int | None = None,
) -> int:
    if privacy_style is not None and privacy_style in STYLE_MIN_WORDS:
        return privacy_style
    main = resolve_main_name(project)
    csv_path = (project_dir or project.parent.parent.parent).expanduser()
    if not (csv_path / "task.csv").is_file():
        # workspace may sit under output/{App}-Swift/{App}/
        for candidate in (
            project_dir,
            project.parent.parent.parent,
            Path(__file__).resolve().parents[2],
        ):
            if candidate is None:
                continue
            p = candidate / "task.csv"
            if p.is_file():
                csv_path = candidate
                break
    try:
        rows = load_csv_tasks(csv_path / "task.csv")
    except (FileNotFoundError, ValueError):
        return 1
    for row in rows:
        if row.name.split("-")[0].strip().lower() == main.lower():
            num = parse_privacy_style_number(row.privacy_style)
            if num is not None:
                return num
    return 1


def _english_word_count(text: str) -> int:
    body = HEADING_RE.sub("", text)
    return len(re.findall(r"[A-Za-z']+", body))


def _heading_positions(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for match in HEADING_RE.finditer(text):
        title = match.group(2).strip().lower()
        out[title] = match.start()
    return out


def verify_legal_md_text(
    text: str,
    *,
    doc_kind: str,
    main_name: str,
    privacy_style: int = 1,
) -> list[str]:
    """Validate one legal MD file. Returns human-readable issue strings."""
    issues: list[str] = []
    label = "privacy" if doc_kind == "privacy" else "terms"
    expected_h1 = (
        f"# {main_name} Privacy Agreement"
        if doc_kind == "privacy"
        else f"# {main_name} User Agreement"
    )
    lines = text.splitlines()

    if not lines or not lines[0].strip().startswith("# "):
        issues.append(f"MD/{label}: missing H1 title")
    elif lines[0].strip() != expected_h1:
        issues.append(f"MD/{label}: H1 must be {expected_h1!r}")

    h1_count = sum(
        1 for line in lines if line.startswith("# ") and not line.startswith("## ")
    )
    if h1_count != 1:
        issues.append(f"MD/{label}: expected exactly one H1, found {h1_count}")

    if LEGAL_SPEC_DATE not in text:
        issues.append(f"MD/{label}: missing {LEGAL_SPEC_DATE!r}")

    h2_count = sum(1 for line in lines if line.startswith("## "))
    if h2_count < 5:
        issues.append(f"MD/{label}: too few ## sections ({h2_count} < 5)")

    if doc_kind == "privacy":
        for heading in PRIVACY_REQUIRED_HEADINGS:
            if f"## {heading}" not in text:
                issues.append(f"MD/{label}: missing H2 {heading!r}")
    else:
        for heading in TERMS_REQUIRED_HEADINGS:
            if f"## {heading}" not in text:
                issues.append(f"MD/{label}: missing H2 {heading!r}")

    if "## Contact Us" not in text:
        issues.append(f"MD/{label}: missing ## Contact Us section")

    contact_email = f"{main_name}@gmail.com"
    if contact_email.lower() not in text.lower():
        issues.append(f"MD/{label}: missing contact email {contact_email!r}")

    if not re.search(r"18\+|18 and older|18 years", text, re.I):
        issues.append(f"MD/{label}: missing 18+ age rating")

    min_words = STYLE_MIN_WORDS.get(privacy_style, STYLE_MIN_WORDS[1])
    wc = _english_word_count(text)
    if wc < min_words:
        issues.append(
            f"MD/{label}: too short ({wc} words < {min_words} for 风格{privacy_style})"
        )

    if privacy_style == 2 and doc_kind == "privacy":
        headings = _heading_positions(text)
        rights_keys = [k for k in headings if "your rights" in k or "user rights" in k]
        collect_keys = [
            k for k in headings if "information we collect" in k or "data collection" in k
        ]
        if rights_keys and collect_keys:
            if headings[rights_keys[0]] > headings[collect_keys[0]]:
                issues.append(
                    "MD/privacy: 风格2 requires user rights section before data collection"
                )

    for idx, raw in enumerate(lines, start=1):
        line = raw.rstrip()
        if LIST_LINE_RE.match(line):
            issues.append(f"MD/{label}: forbidden list syntax at line {idx}")
        if TABLE_LINE_RE.match(line):
            issues.append(f"MD/{label}: forbidden table syntax at line {idx}")
        if line.strip().startswith("> "):
            issues.append(f"MD/{label}: forbidden blockquote at line {idx}")

    region_hit = REGION_BLOCKLIST_RE.search(text)
    if region_hit:
        issues.append(
            f"MD/{label}: forbidden region-specific term {region_hit.group(0)!r}"
        )

    return issues


def verify_legal_md_pair(
    privacy_text: str,
    terms_text: str,
    *,
    main_name: str,
    privacy_style: int = 1,
) -> list[str]:
    issues: list[str] = []
    issues.extend(
        verify_legal_md_text(
            privacy_text, doc_kind="privacy", main_name=main_name, privacy_style=privacy_style
        )
    )
    issues.extend(
        verify_legal_md_text(
            terms_text, doc_kind="terms", main_name=main_name, privacy_style=privacy_style
        )
    )
    combined = f"{privacy_text}\n{terms_text}".lower()
    for phrase in GLOBAL_PHRASES:
        if phrase not in combined:
            issues.append(f"MD: missing global phrase {phrase!r} (privacy+terms combined)")
    return issues


def verify_h5_legal_md(
    project: Path,
    *,
    project_dir: Path | None = None,
    privacy_style: int | None = None,
) -> list[str]:
    """Return issue strings; empty means compliant with 法律协议规范."""
    project = project.expanduser().resolve()
    if not is_h5_shell_project(project):
        return []

    from batch.h5_legal_ui import project_needs_legal_ui

    if not project_needs_legal_ui(project):
        return []

    main_name = resolve_main_name(project)
    style = resolve_privacy_style(
        project, project_dir=project_dir, privacy_style=privacy_style
    )
    issues: list[str] = []

    privacy_md = find_privacy_md(project)
    terms_md = find_terms_md(project)
    if privacy_md is None:
        issues.append(f"MD: missing {main_name} Privacy Agreement.md")
    if terms_md is None:
        issues.append(f"MD: missing {main_name} User Agreement.md")
    if privacy_md is None or terms_md is None:
        return issues

    issues.extend(
        verify_legal_md_pair(
            privacy_md.read_text(encoding="utf-8"),
            terms_md.read_text(encoding="utf-8"),
            main_name=main_name,
            privacy_style=style,
        )
    )
    return issues
