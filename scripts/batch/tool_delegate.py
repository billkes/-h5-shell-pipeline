"""Tool delegate stub — h5-shell-pipeline does not produce native tool apps."""

from __future__ import annotations

TOOL_TYPES: frozenset[str] = frozenset()


def run_tool_single(*_args: object, **_kwargs: object) -> bool:
    raise RuntimeError("h5-shell-pipeline 不支持 tool 包类型")
