"""Sidecar name pools keyed by theme_code (10 candidates per theme, cursor for rename)."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from batch.name_rules import (
    Denylist,
    NameCandidate,
    pick_diverse_candidate_index,
)

POOL_SIZE = 10


@dataclass
class ThemeNamePool:
    theme_code: str
    generated_at: str
    cursor: int = 0
    product_flow: str = ""
    context: dict[str, str] = field(default_factory=dict)
    candidates: list[dict[str, str]] = field(default_factory=list)

    def active(self) -> NameCandidate:
        if self.cursor < 0 or self.cursor >= len(self.candidates):
            raise IndexError(
                f"主题 {self.theme_code} 候选池已耗尽（cursor={self.cursor}）"
            )
        raw = self.candidates[self.cursor]
        return NameCandidate(
            name=raw["name"],
            full_name=raw["full_name"],
            product_code=raw["product_code"],
        )

    def advance(self) -> NameCandidate:
        if self.cursor + 1 >= len(self.candidates):
            raise RuntimeError(
                f"主题 {self.theme_code} 的 {POOL_SIZE} 个候选已全部拒绝，请另选主题"
            )
        self.cursor += 1
        return self.active()

    def as_name_candidates(self) -> list[NameCandidate]:
        return [
            NameCandidate(
                raw["name"],
                raw["full_name"],
                raw["product_code"],
            )
            for raw in self.candidates
        ]

    def select_diverse(
        self,
        deny: Denylist,
        a_face_counts: Counter[str],
        *,
        limit: int,
        start: int | None = None,
    ) -> NameCandidate:
        """选定满足批内 A 面词上限的候选并更新 cursor。"""
        idx = pick_diverse_candidate_index(
            self.as_name_candidates(),
            deny,
            a_face_counts,
            limit=limit,
            start=self.cursor if start is None else start,
        )
        self.cursor = idx
        return self.active()


def sidecar_path(csv_path: Path) -> Path:
    return csv_path.with_name(csv_path.name + ".name-pools.json")


def load_pools(csv_path: Path) -> dict[str, ThemeNamePool]:
    path = sidecar_path(csv_path)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    pools: dict[str, ThemeNamePool] = {}
    for code, raw in (data.get("pools") or {}).items():
        if not isinstance(raw, dict):
            continue
        pools[str(code)] = ThemeNamePool(
            theme_code=str(code),
            generated_at=str(raw.get("generated_at") or ""),
            cursor=int(raw.get("cursor") or 0),
            product_flow=str(raw.get("product_flow") or ""),
            context=dict(raw.get("context") or {}),
            candidates=list(raw.get("candidates") or []),
        )
    return pools


def save_pools(csv_path: Path, pools: dict[str, ThemeNamePool]) -> Path:
    path = sidecar_path(csv_path)
    payload = {
        "pools": {
            code: {
                "generated_at": pool.generated_at,
                "cursor": pool.cursor,
                "product_flow": pool.product_flow,
                "context": pool.context,
                "candidates": pool.candidates,
            }
            for code, pool in pools.items()
        }
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_pool(
    theme_code: str,
    *,
    context: dict[str, str],
    candidates: list[NameCandidate],
    product_flow: str,
) -> ThemeNamePool:
    if len(candidates) != POOL_SIZE:
        raise ValueError(f"需要恰好 {POOL_SIZE} 个候选，当前 {len(candidates)}")
    return ThemeNamePool(
        theme_code=theme_code,
        generated_at=utc_now_iso(),
        cursor=0,
        product_flow=product_flow,
        context=context,
        candidates=[
            {
                "name": c.name,
                "full_name": c.full_name,
                "product_code": c.product_code,
            }
            for c in candidates
        ],
    )
