"""iFlow SDK agent invocation."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from batch.agent_common import (
    _agent_output_paths,
    _compress_images_after_agent,
    _format_agent_run_header,
    _print_agent_start_banner,
    is_transient_agent_failure,
)
from batch.config import BatchConfig


_IFLOW_READY_VERIFIED = False


def _approval_mode_enum(name: str) -> Any:
    """Map config string to iflow_sdk.ApprovalMode enum."""
    try:
        from iflow_sdk import ApprovalMode
    except ImportError as exc:
        raise RuntimeError(
            "未安装 iflow-cli-sdk，请执行: pip install iflow-cli-sdk"
        ) from exc
    mapping = {
        "default": ApprovalMode.DEFAULT,
        "auto_edit": ApprovalMode.AUTO_EDIT,
        "yolo": ApprovalMode.YOLO,
        "plan": ApprovalMode.PLAN,
    }
    return mapping.get(name.lower().strip(), ApprovalMode.YOLO)


def _build_iflow_options(cfg: BatchConfig, workspace: Path) -> Any:
    """Build IFlowOptions from BatchConfig."""
    from iflow_sdk import IFlowOptions

    ws = workspace.resolve()
    allowed_dirs = cfg.iflow_file_allowed_dirs or [str(ws)]
    return IFlowOptions(
        url=cfg.iflow_url,
        auto_start_process=cfg.iflow_auto_start_process,
        timeout=cfg.iflow_timeout_sec,
        log_level=cfg.iflow_log_level,
        cwd=str(ws),
        approval_mode=_approval_mode_enum(cfg.iflow_approval_mode),
        file_access=cfg.iflow_file_access,
        file_allowed_dirs=allowed_dirs,
        file_read_only=cfg.iflow_file_read_only,
        file_max_size=cfg.iflow_file_max_size,
        auth_method_id=cfg.iflow_auth_method_id or None,
        auth_method_info=cfg.iflow_auth_method_info or None,
    )


def _message_to_dict(msg: Any) -> dict[str, Any]:
    """Best-effort convert an iFlow message object to a JSON-serializable dict."""
    data: dict[str, Any] = {"_message_type": type(msg).__name__}
    try:
        data.update(asdict(msg))
    except TypeError:
        for attr in ("chunk", "status", "tool_name", "agent_info", "entries", "stop_reason"):
            if hasattr(msg, attr):
                data[attr] = getattr(msg, attr)
    return data


def _format_message_for_pretty(msg: Any) -> list[str]:
    """Convert an iFlow message to human-readable log lines.

    Uses duck-typing (class name + attributes) so it also works with test fakes
    when the real ``iflow_sdk`` package is not installed.
    """
    msg_type = type(msg).__name__
    lines: list[str] = []

    if msg_type == "AssistantMessage":
        text = ""
        chunk = getattr(msg, "chunk", None)
        if chunk and hasattr(chunk, "text"):
            text = str(chunk.text or "")
        if text:
            lines.append(text)
    elif msg_type == "ToolCallMessage":
        status = getattr(msg, "status", "")
        tool_name = getattr(msg, "tool_name", "") or "unknown"
        lines.append(f"🔧 工具调用 · {tool_name} · 状态: {status}")
    elif msg_type == "PlanMessage":
        entries = getattr(msg, "entries", []) or []
        if entries:
            lines.append("📋 执行计划：")
            for entry in entries:
                status = getattr(entry, "status", "")
                priority = getattr(entry, "priority", "")
                content = getattr(entry, "content", "")
                icon = "✅" if status == "completed" else "⏳"
                lines.append(f"{icon} [{priority}] {content}")
    elif msg_type == "TaskFinishMessage":
        stop_reason = getattr(msg, "stop_reason", None)
        reason_name = (
            stop_reason.name
            if stop_reason and hasattr(stop_reason, "name")
            else str(stop_reason)
        )
        lines.append(f"🎯 任务完成 · stop_reason={reason_name}")
    return lines


def ensure_iflow_ready(cfg: BatchConfig) -> None:
    """Verify that the iFlow SDK is importable."""
    global _IFLOW_READY_VERIFIED
    if _IFLOW_READY_VERIFIED:
        return
    try:
        from iflow_sdk import IFlowClient, IFlowOptions  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "未安装 iflow-cli-sdk，请执行: pip install iflow-cli-sdk"
        ) from exc
    _IFLOW_READY_VERIFIED = True


def run_iflow_agent(
    cfg: BatchConfig,
    workspace: Path,
    prompt: str,
    *,
    log_section_title: str = "",
) -> bool:
    """Run iFlow SDK agent; retry on transient connection failures."""
    if log_section_title:
        from batch.batch_log_enrich import log_section

        log_section(log_section_title)
    if not cfg.dry_run:
        ensure_iflow_ready(cfg)
    try:
        return asyncio.run(_run_iflow_agent_async(cfg, workspace, prompt))
    except Exception as exc:
        print(f">>> iFlow Agent 未捕获异常: {exc}")
        return False


async def _run_iflow_agent_async(
    cfg: BatchConfig,
    workspace: Path,
    prompt: str,
) -> bool:
    ws = workspace.resolve()
    pretty_log, jsonl_log, prompt_path = _agent_output_paths(ws)
    max_attempts = cfg.iflow_max_retries
    base_delay = cfg.iflow_retry_delay_sec

    prompt_path.write_text(prompt, encoding="utf-8")

    for attempt in range(1, max_attempts + 1):
        _print_agent_start_banner(
            pretty_log,
            jsonl_log,
            attempt=attempt,
            max_attempts=max_attempts,
        )
        header = _format_agent_run_header(
            workspace=ws,
            cmd=["iflow", "--experimental-acp"],
            prompt=prompt,
            attempt=attempt,
            max_attempts=max_attempts,
        )

        ok, transient = await _run_iflow_once(
            cfg,
            ws,
            prompt,
            pretty_log,
            jsonl_log,
            header,
        )

        if ok:
            print(
                f">>> iFlow Agent 完成 · 第 {attempt}/{max_attempts} 次 · "
                f"日志: {pretty_log}"
            )
            _compress_images_after_agent(ws)
            return True

        tail_parts = []
        if pretty_log.is_file():
            tail_parts.append(
                pretty_log.read_text(encoding="utf-8", errors="replace")[-6000:]
            )
        if jsonl_log.is_file():
            tail_parts.append(
                jsonl_log.read_text(encoding="utf-8", errors="replace")[-6000:]
            )
        tail = "\n".join(tail_parts)[-12000:]
        transient = transient or is_transient_agent_failure(tail)

        if attempt < max_attempts and transient:
            delay = base_delay * attempt
            print(
                f">>> 脚本外层重试: iFlow 异常，"
                f"{delay}s 后第 {attempt + 1}/{max_attempts} 次..."
            )
            time.sleep(delay)
            continue

        print(f">>> iFlow Agent 失败 · 第 {attempt}/{max_attempts} 次 · 日志: {pretty_log}")
        return False

    return False


async def _run_iflow_once(
    cfg: BatchConfig,
    ws: Path,
    prompt: str,
    pretty_log: Path,
    jsonl_log: Path,
    header: str,
) -> tuple[bool, bool]:
    """Run one iFlow attempt. Returns (success, transient)."""
    from iflow_sdk import (
        AssistantMessage,
        ConnectionError as IFlowConnectionError,
        TaskFinishMessage,
        TimeoutError as IFlowTimeoutError,
        ToolCallMessage,
    )

    if cfg.dry_run:
        pretty_log.write_text(header + "\n[dry_run] 跳过 iFlow 调用\n", encoding="utf-8")
        return True, False

    options = _build_iflow_options(cfg, ws)
    pretty_log.parent.mkdir(parents=True, exist_ok=True)

    accumulated_chars = 0
    tool_count = 0
    stop_reason_value: Any = None
    success = False

    async def _message_loop() -> None:
        nonlocal accumulated_chars, tool_count, stop_reason_value, success
        from iflow_sdk import IFlowClient

        async with IFlowClient(options) as client:
            await client.send_message(prompt)
            messages = client.receive_messages()
            while True:
                try:
                    idle_timeout = cfg.iflow_idle_timeout_sec
                    msg = await asyncio.wait_for(
                        messages.__anext__(),
                        timeout=idle_timeout if idle_timeout > 0 else None,
                    )
                except StopAsyncIteration:
                    break

                # JSONL
                msg_dict = _message_to_dict(msg)
                with jsonl_log.open("a", encoding="utf-8") as jsonl_f:
                    jsonl_f.write(json.dumps(msg_dict, ensure_ascii=False, default=str) + "\n")

                # Pretty log
                pretty_lines = _format_message_for_pretty(msg)
                with pretty_log.open("a", encoding="utf-8") as pretty_f:
                    for line in pretty_lines:
                        if isinstance(msg, AssistantMessage):
                            accumulated_chars += len(line)
                            pretty_f.write(line)
                        else:
                            pretty_f.write(line + "\n")

                # Terminal stream
                if cfg.iflow_heartbeat_sec > 0:
                    for line in pretty_lines:
                        if isinstance(msg, AssistantMessage):
                            sys.stdout.write(f"\r📝 生成中: {accumulated_chars} 字符")
                        else:
                            sys.stdout.write(line + "\n")
                        sys.stdout.flush()

                if isinstance(msg, ToolCallMessage):
                    tool_count += 1

                if isinstance(msg, TaskFinishMessage):
                    stop_reason_value = getattr(msg, "stop_reason", None)
                    from iflow_sdk import StopReason

                    success = stop_reason_value == StopReason.END_TURN
                    break

    try:
        with pretty_log.open("w", encoding="utf-8") as pretty_f:
            pretty_f.write(header)

        phase_timeout = cfg.iflow_phase_timeout_sec
        await asyncio.wait_for(
            _message_loop(),
            timeout=phase_timeout if phase_timeout > 0 else None,
        )

        if success:
            with pretty_log.open("a", encoding="utf-8") as pretty_f:
                pretty_f.write(
                    f"\n🎯 完成 · {tool_count} 个工具 · 生成 {accumulated_chars} 字符\n"
                )
            return True, False

        return False, False

    except IFlowConnectionError:
        with pretty_log.open("a", encoding="utf-8") as pretty_f:
            pretty_f.write("\n>>> iFlow ConnectionError\n")
        return False, True
    except IFlowTimeoutError:
        with pretty_log.open("a", encoding="utf-8") as pretty_f:
            pretty_f.write("\n>>> iFlow TimeoutError\n")
        return False, True
    except asyncio.TimeoutError:
        with pretty_log.open("a", encoding="utf-8") as pretty_f:
            pretty_f.write("\n>>> pipeline killed agent: idle_timeout/phase_timeout\n")
        return False, False
