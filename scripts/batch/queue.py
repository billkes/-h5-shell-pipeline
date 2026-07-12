"""Parse task queue files."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from batch.pack_type import H5_FLUTTER_SHELL, H5_OC_SHELL, H5_SHELL, H5_SWIFT_SHELL


VALID_TYPES = frozenset({H5_SHELL, H5_FLUTTER_SHELL, H5_SWIFT_SHELL, H5_OC_SHELL})


@dataclass(frozen=True)
class QueueTask:
    pack_type: str
    name: str
    desc: str


def parse_queue_line(line: str, default_type: str) -> QueueTask | None:
    line = line.split("#", 1)[0].strip()
    if not line:
        return None
    if "|" not in line:
        return QueueTask(default_type, line, line)
    first, rest = line.split("|", 1)
    if "|" in rest:
        pack_type, name, desc = first, *rest.split("|", 1)
        return QueueTask(pack_type.strip(), name.strip(), desc.strip())
    return QueueTask(default_type, first.strip(), rest.strip())


def load_queue(path: Path, default_type: str = "h5_shell") -> list[QueueTask]:
    tasks: list[QueueTask] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        task = parse_queue_line(line, default_type)
        if task:
            tasks.append(task)
    return tasks


def effective_default_type(default_type: str) -> str:
    """Honor BATCH_PACK_TYPE when the queue line omits an explicit type."""
    env_type = os.environ.get("BATCH_PACK_TYPE", "").strip()
    if env_type in VALID_TYPES:
        return env_type
    return default_type


def parse_single_arg(arg: str, default_type: str) -> QueueTask:
    default_type = effective_default_type(default_type)
    if "|" not in arg:
        return QueueTask(default_type, arg.strip(), arg.strip())
    parts = [p.strip() for p in arg.split("|")]
    name = parts[0]
    if len(parts) == 2:
        return QueueTask(default_type, name, parts[1])
    desc = parts[1]
    pack = parts[2]
    ptype = pack if pack in VALID_TYPES else default_type
    return QueueTask(ptype, name, desc)
