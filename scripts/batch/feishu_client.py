"""Thin lark-cli wrapper (adapted from HaiNaBaiChuan/core/feishu_client.py)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time

_TRANSIENT_ERROR_KEYWORDS = (
    "EOF",
    "connection reset",
    "i/o timeout",
    "connection refused",
    "broken pipe",
    "no such host",
    "dial tcp",
)
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0


def is_lark_cli_installed() -> bool:
    return shutil.which("lark-cli") is not None


def get_lark_cli_version() -> str | None:
    try:
        result = subprocess.run(
            ["lark-cli", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def parse_version(version_str: str | None) -> tuple[int, int, int] | None:
    if not version_str:
        return None
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", version_str)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def install_lark_cli(version: str | None = None) -> bool:
    pkg = f"@larksuite/cli@{version}" if version else "@larksuite/cli"
    print(f"  正在安装 {pkg} ...")
    try:
        result = subprocess.run(
            ["npm", "install", "-g", pkg],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            print(f"  安装完成: {get_lark_cli_version()}")
            return True
        stderr = (result.stderr or "").strip()[:500]
        print(f"  安装失败 (exit={result.returncode}): {stderr}")
        return False
    except subprocess.TimeoutExpired:
        print("  安装超时 (120s)")
        return False
    except FileNotFoundError:
        print("  未找到 npm，请先安装 Node.js")
        return False
    except Exception as e:
        print(f"  安装异常: {e}")
        return False


def _is_transient_error(message: str) -> bool:
    msg_lower = message.lower()
    return any(kw.lower() in msg_lower for kw in _TRANSIENT_ERROR_KEYWORDS)


def run_lark_cmd(args: list[str], timeout: int = 30) -> dict:
    """Run lark-cli; return parsed JSON dict."""
    cmd = ["lark-cli", *args]
    cmd_str = " ".join(cmd)

    for attempt in range(1, _MAX_RETRIES + 1):
        if attempt > 1:
            delay = _RETRY_BASE_DELAY * (2 ** (attempt - 2))
            print(f"  第 {attempt} 次重试 (等待 {delay:.0f}s): {cmd_str}")
            time.sleep(delay)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if not stdout:
                if stderr:
                    try:
                        err_data = json.loads(stderr)
                        err_msg = err_data.get("error", {}).get("message", "未知错误")
                        if _is_transient_error(err_msg) and attempt < _MAX_RETRIES:
                            continue
                        return err_data
                    except json.JSONDecodeError:
                        pass
                if _is_transient_error(stderr) and attempt < _MAX_RETRIES:
                    continue
                return {
                    "ok": False,
                    "error": {"type": "empty_output", "message": "命令无输出"},
                }

            try:
                data = json.loads(stdout)
            except json.JSONDecodeError:
                return {"ok": True, "raw": stdout}

            if data.get("ok") is False:
                err_msg = data.get("error", {}).get("message", "未知错误")
                if _is_transient_error(err_msg) and attempt < _MAX_RETRIES:
                    continue
            return data

        except subprocess.TimeoutExpired:
            if attempt < _MAX_RETRIES:
                continue
            return {
                "ok": False,
                "error": {"type": "timeout", "message": f"命令执行超过 {timeout} 秒"},
            }
        except Exception as e:
            return {"ok": False, "error": {"type": "exception", "message": str(e)}}

    return {
        "ok": False,
        "error": {"type": "max_retries", "message": f"重试 {_MAX_RETRIES} 次后仍失败"},
    }


def run_lark_record_list(extra_args: list[str], timeout: int = 60) -> dict:
    args = ["base", "+record-list", *extra_args]
    if "--format" not in args:
        args = [*args, "--format", "json"]
    return run_lark_cmd(args, timeout=timeout)


def run_lark_interactive(args: list[str], timeout: int = 300, auto_open_url: bool = True) -> bool:
    """Device Flow login when stdout is piped."""
    if args[:2] != ["auth", "login"]:
        try:
            proc = subprocess.run(["lark-cli", *args], timeout=timeout)
            return proc.returncode == 0
        except Exception:
            return False

    init_args = ["lark-cli", *args, "--no-wait", "--json"]
    try:
        result = subprocess.run(init_args, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            if result.stderr:
                print(result.stderr, end="", flush=True)
            return False

        data = json.loads(result.stdout)
        device_code = data.get("device_code", "")
        verification_url = data.get("verification_url", "")
        expires_in = data.get("expires_in", 600)

        if not device_code or not verification_url:
            print("  Device Flow 返回数据不完整")
            return False

        print("  请在浏览器中打开以下链接完成授权：")
        print(f"  {verification_url}")
        print()

        if auto_open_url:
            try:
                subprocess.Popen(
                    ["open", verification_url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass

        poll_interval = 5
        deadline = time.time() + min(timeout, expires_in)

        while time.time() < deadline:
            time.sleep(poll_interval)
            poll_result = subprocess.run(
                ["lark-cli", "auth", "login", "--device-code", device_code],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if poll_result.returncode == 0:
                return True
            stderr = (poll_result.stderr or "").strip()
            if "authorization_pending" in stderr or "slow_down" in stderr:
                continue

        print(f"  Device Flow 授权超时 ({timeout}s)")
        return False

    except json.JSONDecodeError:
        return False
    except Exception:
        return False
