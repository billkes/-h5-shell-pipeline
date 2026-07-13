"""Post-process batch detailed logs: PASS folding, TOC, phase duration table."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from batch.batch_log import _FULL_STAMP_PREFIX, _SHORT_STAMP_PREFIX
from batch.report import _fmt_dur
from batch.state import (
    PHASE_LABELS,
    phase_status_from_data,
    phases_for_version,
    pipeline_version_from_data,
)

_AGENT_START = re.compile(r"^>>> Agent 开始")
_AGENT_END = re.compile(r"^>>> Agent (?:完成|失败)")
_PASS_IN_BODY = re.compile(r"\bPASS\b", re.IGNORECASE)
_FAIL_IN_BODY = re.compile(r"\bFAIL\b|\bERROR\b|❌", re.IGNORECASE)
_FOOTER_MARKER = re.compile(r"\n---\n\n- 批次结束:")


def log_section(title: str) -> None:
    """Write a markdown ### heading to the detailed log (file-only)."""
    from batch.batch_log import log_detail

    log_detail("")
    log_detail(f"### {title}")
    log_detail("")


def heading_anchor(title: str) -> str:
    anchor = title.strip().lower()
    anchor = re.sub(r"[^\w\s-]", "", anchor, flags=re.UNICODE)
    anchor = re.sub(r"\s+", "-", anchor.strip())
    return anchor


def build_toc(headings: list[str]) -> str:
    if not headings:
        return ""
    lines = ["## 目录", ""]
    for heading in headings:
        lines.append(f"- [{heading}](#{heading_anchor(heading)})")
    lines.append("")
    return "\n".join(lines)


def build_phase_duration_table(output_base: Path) -> str:
    from batch.pipeline_steps import STEP_LABELS, step_display, step_duration_key, steps_for_run

    rows: list[tuple[str, str, str, str]] = []
    for sf in sorted(output_base.rglob(".build-state.json")):
        if not sf.is_file():
            continue
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        name = str(data.get("name") or sf.parent.name)
        ver = pipeline_version_from_data(data)
        if ver == "v3":
            pack_type = str(data.get("pack_type") or "contentpack")
            ordered = steps_for_run(pack_type=pack_type)
            steps_map = data.get("steps") if isinstance(data.get("steps"), dict) else {}
            for step_id in ordered:
                status = str(steps_map.get(step_id) or "pending")
                dur = data.get(step_duration_key(step_id))
                label = step_display(step_id)
                icon = {
                    "done": "✅",
                    "failed": "❌",
                    "skipped": "⏭️",
                    "running": "⚡",
                }.get(status, "⬜")
                rows.append((name, label, _fmt_dur(dur), icon))
            continue
        for phase in phases_for_version(ver):
            status = phase_status_from_data(data, phase) or "pending"
            dur = data.get(f"{phase}_duration_s")
            label = PHASE_LABELS.get(phase, phase)
            icon = {
                "done": "✅",
                "failed": "❌",
                "skipped": "⏭️",
                "running": "⚡",
            }.get(status, "⬜")
            rows.append((name, label, _fmt_dur(dur), icon))
    if not rows:
        return ""
    lines = [
        "## 步骤耗时",
        "",
        "| App | 步骤 | 耗时 | 状态 |",
        "|-----|------|------|------|",
    ]
    for name, label, dur, icon in rows:
        lines.append(f"| {name} | {label} | {dur} | {icon} |")
    lines.append("")
    return "\n".join(lines)


def _strip_line_prefix(line: str) -> str:
    match = _FULL_STAMP_PREFIX.match(line)
    if match:
        return line[match.end() :].lstrip()
    match = _SHORT_STAMP_PREFIX.match(line)
    if match:
        return line[match.end() :].lstrip()
    return line


def classify_agent_body(body: str) -> str:
    if _FAIL_IN_BODY.search(body):
        return "fail"
    if _PASS_IN_BODY.search(body):
        return "pass"
    return "neutral"


def extract_agent_summary(body: str, section_title: str = "") -> str:
    for line in body.splitlines():
        stripped = _strip_line_prefix(line).strip()
        if not stripped or stripped.startswith(">>>"):
            continue
        if "PASS" in stripped or "FAIL" in stripped or "**" in stripped:
            cleaned = stripped.replace("**", "").strip()
            return cleaned[:140] if cleaned else section_title
    return section_title or "Agent 输出"


def _duration_from_lines(lines: list[str]) -> str:
    stamps: list[datetime] = []
    for line in lines:
        match = _FULL_STAMP_PREFIX.match(line)
        if not match:
            continue
        try:
            stamps.append(
                datetime.strptime(match.group(0)[1:-1], "%Y-%m-%d %H:%M:%S")
            )
        except ValueError:
            continue
    if len(stamps) < 2:
        return ""
    sec = max(0, int((stamps[-1] - stamps[0]).total_seconds()))
    if sec >= 60:
        return f"{sec // 60}m {sec % 60:02d}s"
    return f"{sec}s"


def _section_title_before(lines: list[str], index: int) -> str:
    for offset in range(1, 6):
        pos = index - offset
        if pos < 0:
            break
        stripped = _strip_line_prefix(lines[pos]).strip()
        if stripped.startswith("### "):
            return stripped[4:].strip()
    return ""


def fold_agent_segments(content: str) -> str:
    lines = content.splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = _strip_line_prefix(line)
        if not _AGENT_START.match(stripped):
            out.append(line)
            index += 1
            continue

        start_index = index
        index += 1
        body_lines: list[str] = []
        end_index: int | None = None
        while index < len(lines):
            body_stripped = _strip_line_prefix(lines[index])
            if _AGENT_END.match(body_stripped):
                end_index = index
                break
            body_lines.append(lines[index])
            index += 1
        if end_index is None:
            out.extend(lines[start_index:])
            break

        section = _section_title_before(lines, start_index)
        control_lines: list[str] = []
        agent_lines: list[str] = []
        for body_line in body_lines:
            if _strip_line_prefix(body_line).startswith(">>>"):
                control_lines.append(body_line)
            else:
                agent_lines.append(body_line)

        agent_text = "\n".join(agent_lines)
        kind = classify_agent_body(agent_text)

        out.append(lines[start_index])
        out.extend(control_lines)

        if kind == "pass" and agent_text.strip():
            summary = extract_agent_summary(agent_text, section)
            duration = _duration_from_lines(body_lines)
            if duration:
                summary = f"{summary} · {duration}"
            out.append("<details>")
            out.append(f"<summary>{summary}</summary>")
            out.append("")
            out.extend(agent_lines)
            out.append("")
            out.append("</details>")
        else:
            out.extend(body_lines)

        out.append(lines[end_index])
        index = end_index + 1

    return "\n".join(out)


def collect_section_headings(content: str) -> list[str]:
    headings: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("### "):
            headings.append(stripped[4:].strip())
    return headings


def insert_navigation_blocks(content: str, output_base: Path | None) -> str:
    headings = collect_section_headings(content)
    toc = build_toc(headings)
    duration = build_phase_duration_table(output_base) if output_base else ""
    navigation = "\n".join(block for block in (toc, duration) if block)
    if not navigation:
        return content

    marker = "- 日志文件:"
    marker_index = content.find(marker)
    if marker_index == -1:
        return navigation + content

    insert_at = content.find("\n", marker_index)
    if insert_at == -1:
        return content
    insert_at += 1
    if insert_at < len(content) and content[insert_at] == "\n":
        insert_at += 1
    return content[:insert_at] + navigation + content[insert_at:]


def enrich_detailed_log(log_path: Path, *, output_base: Path | None = None) -> None:
    """Fold PASS agent blocks and inject TOC + duration table into *log_path*."""
    if not log_path.is_file():
        return
    raw = log_path.read_text(encoding="utf-8")
    footer_match = _FOOTER_MARKER.search(raw)
    if footer_match:
        body = raw[: footer_match.start()]
        footer = raw[footer_match.start() :]
    else:
        body = raw
        footer = ""

    body = fold_agent_segments(body)
    body = insert_navigation_blocks(body, output_base)
    log_path.write_text(body + footer, encoding="utf-8")
