"""Shared utilities for agent runners (Cursor CLI and iFlow SDK)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from batch.image_compress import (
    MAX_IMAGE_KB,
    compress_workspace_images,
)

_TRANSIENT_AGENT_PATTERNS = re.compile(
    r"connection\s+lost|connection\s+failed\s+repeatedly|"
    r"econnreset|etimedout|socket\s+hang\s+up|"
    r"network\s+error|temporarily\s+unavailable|"
    r"\[aborted\]\s+read\s+econnreset|"
    r"pipeline killed agent:\s*(?:idle_timeout|phase_timeout)",
    re.IGNORECASE,
)

# log path hints — once per workspace per batch process.
_agent_hint_logged: set[str] = set()

_AGENT_LOG_PRETTY = ".agent-last-run.log"
_AGENT_LOG_JSONL = ".agent-last-run.jsonl"
_AGENT_PROMPT_SNAPSHOT = ".agent-last-prompt.md"


def _agent_output_paths(workspace: Path) -> tuple[Path, Path, Path]:
    ws = workspace.resolve()
    return (
        ws / _AGENT_LOG_PRETTY,
        ws / _AGENT_LOG_JSONL,
        ws / _AGENT_PROMPT_SNAPSHOT,
    )


def _format_agent_run_header(
    *,
    workspace: Path,
    cmd: list[str],
    prompt: str,
    attempt: int,
    max_attempts: int,
) -> str:
    started = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    safe_cmd = " ".join(_shell_quote(arg) for arg in cmd)
    return (
        f"=== Agent run {started} · 第 {attempt}/{max_attempts} 次 ===\n"
        f"workspace: {workspace}\n"
        f"prompt 长度: {len(prompt)} 字符\n"
        f"command: {safe_cmd}\n"
        f"原始 JSONL: {workspace / _AGENT_LOG_JSONL}\n"
        f"可读日志: {workspace / _AGENT_LOG_PRETTY}\n"
        "---\n"
    )


def _shell_quote(arg: str) -> str:
    if re.fullmatch(r"[\w./:=+-]+", arg):
        return arg
    return "'" + arg.replace("'", "'\"'\"'") + "'"


def _print_agent_start_banner(
    pretty_log: Path,
    jsonl_log: Path,
    *,
    attempt: int,
    max_attempts: int,
) -> None:
    print(f">>> Agent 开始 · 第 {attempt}/{max_attempts} 次")
    key = str(pretty_log.resolve())
    if key in _agent_hint_logged:
        return
    _agent_hint_logged.add(key)
    print(f">>> 可读日志: {pretty_log}")
    print(f">>> 原始 JSONL: {jsonl_log}")
    print(f'>>> 另开终端: tail -f "{pretty_log}"')
    print(
        ">>> 提示: stream-json 会实时写入工具调用；"
        "Connection lost 多为 CLI 内建重连，进程未退出则仍在运行"
    )


def _heartbeat_wait_schedule(base_sec: int) -> list[int]:
    """Backoff: base → 3× → 10× (cap) to cut idle spam in long agent runs."""
    if base_sec <= 0:
        return []
    return [base_sec, base_sec * 3, base_sec * 10]


def is_transient_agent_failure(output: str) -> bool:
    """True when agent likely failed due to network/connection, not task logic."""
    return bool(_TRANSIENT_AGENT_PATTERNS.search(output))


def _compress_images_after_agent(workspace: Path) -> None:
    """Compress agent-added assets so no single image exceeds the budget."""
    try:
        report = compress_workspace_images(workspace)
    except OSError as exc:
        print(f">>> 警告: Agent 后图片压缩失败: {exc}")
        return
    if report.compressed:
        print(
            f">>> Agent 后图片审查: 压缩 {report.compressed} 张"
            f"（上限 {MAX_IMAGE_KB}KB/张）"
        )
    if report.still_over_limit:
        print(
            f">>> 警告: {len(report.still_over_limit)} 张图片仍超过 "
            f"{MAX_IMAGE_KB}KB: {', '.join(report.still_over_limit)}"
        )
    if report.errors:
        print(f">>> 警告: 图片压缩错误: {'; '.join(report.errors)}")
