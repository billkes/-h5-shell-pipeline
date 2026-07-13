"""Cursor CLI agent invocation."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from batch.agent_common import (
    _agent_output_paths,
    _compress_images_after_agent,
    _format_agent_run_header,
    _heartbeat_wait_schedule,
    _print_agent_start_banner,
    _shell_quote,
    is_transient_agent_failure,
)
from batch.config import BatchConfig

_CLI_RECONNECT_LINE = re.compile(
    r"connection\s+lost,\s*reconnecting|retry\s+attempt\s+\d+",
    re.IGNORECASE,
)


@dataclass
class StreamJsonProgress:
    """Mutable state while parsing Cursor CLI stream-json lines."""

    tool_count: int = 0
    accumulated_chars: int = 0
    model: str = ""
    terminal_lines: list[str] = field(default_factory=list)
    log_lines: list[str] = field(default_factory=list)

    def consume(self, line: str) -> None:
        """Parse one stdout line; append readable lines to terminal/log buffers."""
        stripped = line.strip()
        if not stripped:
            return
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            self.terminal_lines.append(line.rstrip("\n"))
            self.log_lines.append(line.rstrip("\n"))
            return
        if not isinstance(payload, dict):
            return

        event_type = str(payload.get("type") or "")
        subtype = str(payload.get("subtype") or "")

        if event_type == "system" and subtype == "init":
            model = str(payload.get("model") or "unknown")
            self.model = model
            msg = f"🤖 模型: {model}"
            self.terminal_lines.append(msg)
            self.log_lines.append(msg)
            return

        if event_type == "assistant":
            has_ts = "timestamp_ms" in payload
            has_mc = "model_call_id" in payload
            if has_ts and not has_mc:
                content = _extract_assistant_text(payload)
                if content:
                    self.accumulated_chars += len(content)
                    self.terminal_lines.append(
                        f"\r📝 生成中: {self.accumulated_chars} 字符"
                    )
            return

        if event_type == "tool_call":
            self._handle_tool_call(payload, subtype)
            return

        if event_type == "result":
            duration_ms = int(payload.get("duration_ms") or 0)
            duration_s = max(0, duration_ms // 1000)
            msg = (
                f"🎯 完成 · {duration_s}s · {self.tool_count} 个工具 · "
                f"生成 {self.accumulated_chars} 字符"
            )
            self.terminal_lines.append(msg)
            self.log_lines.append(msg)

    def _handle_tool_call(self, payload: dict[str, object], subtype: str) -> None:
        tool_call = payload.get("tool_call")
        if not isinstance(tool_call, dict):
            return
        if subtype == "started":
            self.tool_count += 1
            msg = f"🔧 工具 #{self.tool_count}: {_format_tool_started(tool_call)}"
            self.terminal_lines.append(msg)
            self.log_lines.append(msg)
            return
        if subtype != "completed":
            return
        detail = _format_tool_completed(tool_call)
        if detail:
            self.terminal_lines.append(detail)
            self.log_lines.append(detail)


def _extract_assistant_text(payload: dict[str, object]) -> str:
    message = payload.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if not isinstance(content, list) or not content:
        return ""
    first = content[0]
    if not isinstance(first, dict):
        return ""
    return str(first.get("text") or "")


def _truncate(text: str, limit: int = 72) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def _basename(path: str) -> str:
    p = str(path or "").strip()
    return p.rsplit("/", 1)[-1] if p else ""


def _find_tool_node(tool_call: dict[str, object]) -> tuple[str, dict[str, object]]:
    for key, node in tool_call.items():
        if key.endswith("ToolCall") and isinstance(node, dict):
            return key, node
    fn = tool_call.get("function")
    if isinstance(fn, dict):
        return str(fn.get("name") or "function"), fn
    return "tool", {}


def _tool_args(node: dict[str, object]) -> dict[str, object]:
    args = node.get("args")
    return args if isinstance(args, dict) else {}


def _extract_tool_summary(kind: str, node: dict[str, object]) -> str:
    args = _tool_args(node)
    if kind == "function":
        return _truncate(str(args.get("arguments") or ""))

    if kind == "shellToolCall":
        desc = str(args.get("description") or "").strip()
        if desc:
            return _truncate(desc)
        return _truncate(str(args.get("command") or ""))

    if kind == "globToolCall":
        pattern = str(args.get("globPattern") or "*")
        where = _basename(str(args.get("targetDirectory") or ""))
        return f"{pattern} @ {where}" if where else pattern

    if kind == "grepToolCall":
        pattern = _truncate(str(args.get("pattern") or ""), 48)
        where = _basename(str(args.get("path") or "."))
        return f"/{pattern}/ @ {where}"

    if kind == "semSearchToolCall":
        query = str(args.get("query") or "").strip()
        return _truncate(query) if query else ""

    if kind == "mcpToolCall":
        provider = str(args.get("providerIdentifier") or "MCP")
        tool_name = str(args.get("toolName") or "")
        return f"{provider}: {tool_name}" if tool_name else provider

    if kind == "taskToolCall":
        return _truncate(str(args.get("description") or "Subagent task"))

    if kind == "webSearchToolCall":
        return _truncate(str(args.get("search_term") or args.get("query") or ""))

    if kind in ("webFetchToolCall", "fetchToolCall"):
        return _truncate(str(args.get("url") or ""))

    for key in (
        "path",
        "query",
        "url",
        "pattern",
        "description",
        "command",
        "toolName",
        "title",
    ):
        if args.get(key):
            val = str(args[key])
            if key == "path":
                val = _basename(val) or val
            return _truncate(val)
    return ""


def _format_tool_started(tool_call: dict[str, object]) -> str:
    kind, node = _find_tool_node(tool_call)
    summary = _extract_tool_summary(kind, node)
    if summary:
        return f"{kind} · {summary}"
    return kind


def _format_tool_completed(tool_call: dict[str, object]) -> str:
    kind, node = _find_tool_node(tool_call)
    result = node.get("result")
    if not isinstance(result, dict):
        return ""

    success = result.get("success")
    if isinstance(success, dict):
        if kind == "readToolCall":
            lines = int(success.get("totalLines") or 0)
            return f"   ✅ 已读取 {lines} 行"
        if kind == "writeToolCall":
            lines = int(success.get("linesCreated") or 0)
            size = int(success.get("fileSize") or 0)
            return f"   ✅ 已写入 {lines} 行 ({size} 字节)"
        if kind == "editToolCall":
            added = int(success.get("linesAdded") or 0)
            removed = int(success.get("linesRemoved") or 0)
            return f"   ✅ 已编辑 +{added}/-{removed} 行"
        if kind == "shellToolCall":
            code = int(success.get("exitCode") or 0)
            out = _truncate(
                str(success.get("stdout") or success.get("interleavedOutput") or ""),
                60,
            )
            mark = "✅" if code == 0 else "⚠️"
            suffix = f" · {out}" if out else ""
            return f"   {mark} exit={code}{suffix}"
        if kind == "globToolCall":
            total = int(success.get("totalFiles") or 0)
            return f"   ✅ 匹配 {total} 个文件"
        if kind == "grepToolCall":
            mode = str(success.get("outputMode") or "content")
            return f"   ✅ 搜索完成 ({mode})"
        if kind == "deleteToolCall":
            return "   ✅ 已删除"
        return f"   ✅ {kind} 完成"

    if result.get("failure"):
        return f"   ❌ {kind} 失败"
    return ""


def _build_agent_cmd(cfg: BatchConfig, workspace: Path, prompt: str) -> list[str]:
    cli = find_cursor_cli(cfg.cursor_cli)
    cmd = [cli, "-p", "--workspace", str(workspace.resolve()), "--trust", "--yolo"]
    if cfg.cursor_agent_sandbox:
        cmd.extend(["--sandbox", "enabled"])
    fmt = (cfg.cursor_agent_output_format or "stream-json").strip()
    if fmt:
        cmd.extend(["--output-format", fmt])
    if fmt == "stream-json" and cfg.cursor_agent_stream_partial:
        cmd.append("--stream-partial-output")
    cmd.append(prompt)
    return cmd


def find_cursor_cli(preferred: str = "") -> str:
    if preferred and _is_executable(preferred):
        return preferred
    for cmd in ("agent", "cursor-agent"):
        path = _which(cmd)
        if path:
            return path
    home = Path.home()
    for candidate in (
        home / ".local/bin/agent",
        home / ".local/bin/cursor-agent",
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    versions = home / ".local/share/cursor-agent/versions"
    if versions.is_dir():
        dirs = sorted(versions.glob("*/"), key=lambda p: p.stat().st_mtime)
        if dirs:
            cli = dirs[-1] / "cursor-agent"
            if cli.is_file() and os.access(cli, os.X_OK):
                return str(cli)
    return "agent"


def _which(cmd: str) -> str | None:
    for part in os.environ.get("PATH", "").split(os.pathsep):
        path = Path(part) / cmd
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return None


def _is_executable(path: str) -> bool:
    p = Path(path)
    return p.is_file() and os.access(p, os.X_OK)


_cursor_ready_verified = False


def ensure_cursor_ready(cfg: BatchConfig) -> None:
    global _cursor_ready_verified
    if _cursor_ready_verified:
        return
    cli = find_cursor_cli(cfg.cursor_cli)
    cfg.cursor_cli = cli
    if not _is_executable(cli) and _which(cli) is None:
        raise RuntimeError(
            "未找到 Cursor CLI。安装: curl https://cursor.com/install -fsS | bash"
        )
    timeout = cfg.cursor_status_timeout
    print(f"正在检查 Cursor 登录状态（最多等 {timeout} 秒）...")
    tmp = Path(tempfile.gettempdir()) / f"cursor_status_{os.getpid()}.txt"
    with open(tmp, "w", encoding="utf-8") as f:
        proc = subprocess.Popen(
            [cli, "status"],
            stdout=f,
            stderr=subprocess.STDOUT,
        )
        time.sleep(timeout)
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        if proc.returncode is None:
            print("警告: 状态检查超时，将继续执行")
    out = tmp.read_text(encoding="utf-8", errors="replace")
    if "Authentication required" in out:
        raise RuntimeError(f"Cursor CLI 未登录，请先执行: {cli} login")
    tmp.unlink(missing_ok=True)
    _cursor_ready_verified = True


def run_cursor_agent(
    cfg: BatchConfig,
    workspace: Path,
    prompt: str,
    *,
    log_section_title: str = "",
) -> bool:
    """Run Cursor agent; retry on transient connection failures.

    The script never passes ``--model``. Whichever model is currently active in
    ``cursor-agent`` (or the Cursor IDE) is used. Switch models there, not here.
    """
    if not cfg.dry_run:
        ensure_cursor_ready(cfg)
    if log_section_title:
        from batch.batch_log_enrich import log_section

        log_section(log_section_title)
    return _run_agent_direct(cfg, workspace, prompt)


def _run_agent_subprocess(
    cmd: list[str],
    ws: Path,
    pretty_log: Path,
    jsonl_log: Path,
    *,
    output_format: str,
    stream: bool,
    heartbeat_sec: int,
    attempt: int,
    max_attempts: int,
    phase_timeout_sec: int = 0,
    idle_timeout_sec: int = 0,
    run_header: str = "",
) -> int:
    """Run agent CLI once; tee stdout to log files and optionally the terminal."""
    pretty_log.parent.mkdir(parents=True, exist_ok=True)
    use_stream_json = output_format == "stream-json"
    proc = subprocess.Popen(
        cmd,
        cwd=ws,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )
    if proc.stdout is None:
        return proc.wait()

    started_at = time.time()
    last_output_at = [started_at]
    stop_heartbeat = threading.Event()
    reconnect_hint_shown = [False]
    killed_reason = [""]
    progress = StreamJsonProgress()

    def heartbeat_loop() -> None:
        schedule = _heartbeat_wait_schedule(heartbeat_sec)
        if not schedule:
            return
        tick = 0
        while not stop_heartbeat.wait(schedule[min(tick, len(schedule) - 1)]):
            tick += 1
            if proc.poll() is not None:
                break
            now = time.time()
            elapsed_min = max(0, int((now - started_at) / 60))
            idle_sec = max(0, int(now - last_output_at[0]))
            if phase_timeout_sec > 0 and (now - started_at) >= phase_timeout_sec:
                killed_reason[0] = "phase_timeout"
                print(
                    f">>> Agent 总时长超过 {phase_timeout_sec}s，终止进程",
                    flush=True,
                )
                proc.kill()
                break
            if idle_timeout_sec > 0 and idle_sec >= idle_timeout_sec:
                killed_reason[0] = "idle_timeout"
                print(
                    f">>> Agent {idle_sec}s 无新输出（上限 {idle_timeout_sec}s），"
                    "视为挂起并终止",
                    flush=True,
                )
                proc.kill()
                break
            msg = (
                f">>> Agent 仍在运行 · 第 {attempt}/{max_attempts} 次"
                f" · 已 {elapsed_min} 分钟"
            )
            if idle_sec >= max(1, heartbeat_sec - 5):
                msg += f" · {idle_sec}s 无新输出"
            msg += f" · 日志: {pretty_log}"
            print(msg, flush=True)

    hb_thread: threading.Thread | None = None
    if heartbeat_sec > 0:
        hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        hb_thread.start()

    def _emit_terminal_lines(lines: list[str]) -> None:
        for item in lines:
            if item.startswith("\r"):
                sys.stdout.write(item)
            else:
                if progress.accumulated_chars and not item.startswith("\r"):
                    sys.stdout.write("\n")
                sys.stdout.write(item + "\n")
            sys.stdout.flush()

    try:
        with pretty_log.open("w", encoding="utf-8") as pretty_f, jsonl_log.open(
            "w", encoding="utf-8"
        ) as jsonl_f:
            if run_header:
                pretty_f.write(run_header)
                pretty_f.flush()
            for line in proc.stdout:
                last_output_at[0] = time.time()
                if use_stream_json:
                    jsonl_f.write(line)
                    jsonl_f.flush()
                    progress.consume(line)
                    if progress.log_lines:
                        pretty_f.write("\n".join(progress.log_lines) + "\n")
                        pretty_f.flush()
                        progress.log_lines.clear()
                    if stream and progress.terminal_lines:
                        _emit_terminal_lines(progress.terminal_lines)
                        progress.terminal_lines.clear()
                else:
                    pretty_f.write(line)
                    pretty_f.flush()
                    if stream:
                        sys.stdout.write(line)
                        sys.stdout.flush()
                if _CLI_RECONNECT_LINE.search(line) and not reconnect_hint_shown[0]:
                    reconnect_hint_shown[0] = True
                    hint = (
                        ">>> [CLI 内建重连] 以上为 Cursor 云端重连，"
                        "不等于本机断网或任务失败"
                    )
                    print(hint, flush=True)
                    pretty_f.write(hint + "\n")
                    pretty_f.flush()
        returncode = proc.wait()
        if killed_reason[0] and returncode != 0:
            note = f"\n>>> pipeline killed agent: {killed_reason[0]}\n"
            with pretty_log.open("a", encoding="utf-8") as pretty_f:
                pretty_f.write(note)
            if use_stream_json:
                with jsonl_log.open("a", encoding="utf-8") as jsonl_f:
                    jsonl_f.write(note)
        return returncode
    finally:
        stop_heartbeat.set()
        if hb_thread is not None:
            hb_thread.join(timeout=1.0)


def _run_agent_direct(
    cfg: BatchConfig,
    workspace: Path,
    prompt: str,
) -> bool:
    """Run Cursor agent directly inside the given workspace."""
    ws = workspace.resolve()
    pretty_log, jsonl_log, prompt_path = _agent_output_paths(ws)
    output_format = (cfg.cursor_agent_output_format or "stream-json").strip()
    max_attempts = cfg.cursor_agent_max_retries
    base_delay = cfg.cursor_agent_retry_delay_sec

    prompt_path.write_text(prompt, encoding="utf-8")

    for attempt in range(1, max_attempts + 1):
        cmd = _build_agent_cmd(cfg, ws, prompt)
        _print_agent_start_banner(
            pretty_log,
            jsonl_log,
            attempt=attempt,
            max_attempts=max_attempts,
        )
        header = _format_agent_run_header(
            workspace=ws,
            cmd=cmd,
            prompt=prompt,
            attempt=attempt,
            max_attempts=max_attempts,
        )
        returncode = _run_agent_subprocess(
            cmd,
            ws,
            pretty_log,
            jsonl_log,
            output_format=output_format,
            stream=cfg.cursor_agent_stream,
            heartbeat_sec=cfg.cursor_agent_heartbeat_sec,
            attempt=attempt,
            max_attempts=max_attempts,
            phase_timeout_sec=cfg.cursor_agent_phase_timeout_sec,
            idle_timeout_sec=cfg.cursor_agent_idle_timeout_sec,
            run_header=header,
        )
        if returncode == 0:
            print(
                f">>> Agent 完成 · 第 {attempt}/{max_attempts} 次 · "
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
        transient = is_transient_agent_failure(tail)
        if attempt < max_attempts and transient:
            delay = base_delay * attempt
            print(
                f">>> 脚本外层重试: Cursor CLI 已退出且日志含连接异常，"
                f"{delay}s 后第 {attempt + 1}/{max_attempts} 次..."
            )
            time.sleep(delay)
            continue

        if transient:
            print(
                f">>> Agent 失败: Cursor 云端连接在 {max_attempts} 次外层尝试后"
                f"仍未恢复 · 日志: {pretty_log}"
            )
        else:
            print(
                f">>> Agent 失败 · 退出码 {returncode} · 日志: {pretty_log}"
            )
        return False

    return False


def run_agent(
    cfg: BatchConfig,
    workspace: Path,
    prompt: str,
    *,
    log_section_title: str = "",
) -> bool:
    """Backward-compatible dispatcher entry point."""
    from batch.agent_runner import run_agent as _dispatch

    return _dispatch(cfg, workspace, prompt, log_section_title=log_section_title)
