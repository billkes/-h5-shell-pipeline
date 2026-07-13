"""Helpers for persisting phase failure details into .build-state.json."""

from __future__ import annotations

import re
from pathlib import Path


def analyze_log_error_snippets(log_file: Path, *, limit: int = 12) -> list[str]:
    if not log_file.is_file():
        return ["analyze.log 不存在"]
    text = log_file.read_text(encoding="utf-8", errors="replace")
    marker = "--- flutter analyze"
    section = text[text.rfind(marker) :] if marker in text else text
    errors = re.findall(r"^\s*(error •.+)$", section, re.MULTILINE)
    if not errors:
        pub_marker = "--- flutter pub get ---"
        if pub_marker in text and "命令失败" in text:
            return ["flutter pub get 失败，详见 analyze.log"]
        return ["flutter analyze 未通过，详见 analyze.log"]
    return errors[:limit]
