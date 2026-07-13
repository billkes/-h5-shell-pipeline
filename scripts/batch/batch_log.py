"""Capture batch stdout/stderr to a detailed log file for post-run analysis."""

from __future__ import annotations

import re
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator, TextIO

_FULL_STAMP_PREFIX = re.compile(r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]")
_SHORT_STAMP_PREFIX = re.compile(r"^\[\d{2}:\d{2}:\d{2}\]")
_MD_BODY_PREFIX = re.compile(
    r"^(?:\||#{1,6}\s|>{1,2}\s|-{3,}\s*$|\*{1,3}\s|\*\*[^*])"
)

_detail_writer: ContextVar[Callable[[str], None] | None] = ContextVar(
    "batch_detail_writer", default=None
)


def log_detail(line: str) -> None:
    """Write a line to the detailed log file only (no stdout)."""
    writer = _detail_writer.get()
    if writer is not None:
        writer(line)
    else:
        print(line)


def format_log_timestamp(when: datetime | None = None) -> str:
    moment = when or datetime.now()
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def line_needs_timestamp(line: str) -> bool:
    """Return False when *line* already has a stamp or is markdown body (tables, headings)."""
    if _FULL_STAMP_PREFIX.match(line) or _SHORT_STAMP_PREFIX.match(line):
        return False
    stripped = line.lstrip()
    if not stripped:
        return True
    if stripped.startswith("|") or _MD_BODY_PREFIX.match(stripped):
        return False
    return True


def format_stamped_log_line(line: str, when: datetime | None = None) -> str:
    """Format one log line; skip duplicate stamps and markdown rows."""
    if line_needs_timestamp(line):
        stamp = format_log_timestamp(when)
        return f"[{stamp}] {line}\n"
    return f"{line}\n"


class _LineTimestampWriter:
    """Write each complete line to the log file with a wall-clock prefix."""

    def __init__(self, target: TextIO) -> None:
        self._target = target
        self._pending = ""

    def write(self, data: str) -> int:
        if not data:
            return 0
        self._pending += data
        while "\n" in self._pending:
            line, self._pending = self._pending.split("\n", 1)
            self._write_stamped_line(line)
        return len(data)

    def _write_stamped_line(self, line: str) -> None:
        self._target.write(format_stamped_log_line(line))

    def flush(self) -> None:
        if self._pending:
            self._write_stamped_line(self._pending.rstrip("\r"))
            self._pending = ""
        self._target.flush()

    def isatty(self) -> bool:
        return False


class _TeeStream:
    """Mirror writes to console; optional second sink gets timestamped lines."""

    def __init__(self, primary, stamped_secondary) -> None:
        self._primary = primary
        self._stamped = stamped_secondary

    def write(self, data: str) -> int:
        self._primary.write(data)
        self._stamped.write(data)
        return len(data)

    def flush(self) -> None:
        self._primary.flush()
        self._stamped.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._primary, "isatty", lambda: False)())

    def __getattr__(self, name: str):
        """Delegate encoding/buffer/etc. so wrapped imports (e.g. ui-ux-pro-max) work."""
        return getattr(self._primary, name)


def make_batch_stamp(when: datetime | None = None) -> str:
    moment = when or datetime.now()
    return moment.strftime("%Y-%m-%d_%H-%M")


def detailed_log_path(output_base: Path, batch_stamp: str) -> Path:
    return output_base / f"{batch_stamp}详细日志.md"


def batch_report_path(output_base: Path, batch_stamp: str) -> Path:
    return output_base / f"{batch_stamp}_batch-report.md"


@contextmanager
def batch_log_session(
    log_path: Path,
    *,
    header_lines: list[str] | None = None,
    started_at: datetime | None = None,
    output_base: Path | None = None,
) -> Iterator[Path]:
    """Mirror stdout/stderr to ``log_path`` with per-line timestamps."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    batch_start = started_at or datetime.now()
    started = format_log_timestamp(batch_start)

    with log_path.open("w", encoding="utf-8") as log_file:
        log_file.write("# 批次详细日志\n\n")
        log_file.write(f"- 批次开始: {started}\n")
        log_file.write(f"- 日志文件: `{log_path}`\n\n")
        if header_lines:
            log_file.write("## 批次信息\n\n")
            for line in header_lines:
                log_file.write(f"{line.rstrip()}\n")
            log_file.write("\n---\n\n")
        log_file.write("## 终端输出\n\n")
        log_file.write(
            "> 队列摘要见上方终端；以下为带时间戳的完整镜像。"
            "标记为 file-only 的行仅出现在本文件。\n\n"
        )
        log_file.flush()

        def _write_detail(line: str) -> None:
            log_file.write(format_stamped_log_line(line))
            log_file.flush()

        detail_token = _detail_writer.set(_write_detail)
        stamped = _LineTimestampWriter(log_file)
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        sys.stdout = _TeeStream(orig_stdout, stamped)
        sys.stderr = _TeeStream(orig_stderr, stamped)
        try:
            yield log_path
        finally:
            _detail_writer.reset(detail_token)
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
            stamped.flush()
            finished = format_log_timestamp()
            elapsed_s = int((datetime.now() - batch_start).total_seconds())
            log_file.write("\n---\n\n")
            log_file.write(f"- 批次结束: {finished}\n")
            log_file.write(f"- 总耗时: {elapsed_s}s\n")
            log_file.flush()

    from batch.batch_log_enrich import enrich_detailed_log

    enrich_detailed_log(log_path, output_base=output_base)
