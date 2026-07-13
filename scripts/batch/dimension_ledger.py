"""Global dimension-combo ledger for ios-03 gacha (1400 combos)."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from batch.csv_tasks import (
    COL_ARCHITECTURE,
    COL_NAMING_RULE,
    COL_PROGRAMMING_STYLE,
    COL_STATE_MANAGEMENT,
    NAMING_OBFUSCATION_RULES,
    PROGRAMMING_STYLES,
    _ALLOWED_STATE_PATTERN,
)
from batch.task_schema import COL_NAME, diversity_cap

FULL_SIZE = 1400

_KEY_TO_STATE_LABEL: dict[str, str] = {
    "getx": "GETX",
    "setstate": "SetState",
    "bloc": "Bloc",
    "provider": "Provider",
    "mobx": "MobX",
    "redux": "Redux",
}

_KEY_TO_PATTERN_LABEL: dict[str, str] = {
    "mvc": "MVC",
    "mvp": "MVP",
    "mvvm": "MVVM",
    "viper": "VIPER",
    "simple_mv": "简单 MV",
}

_DIM_COLS = (
    COL_STATE_MANAGEMENT,
    COL_ARCHITECTURE,
    COL_NAMING_RULE,
    COL_PROGRAMMING_STYLE,
)


def ledger_path(project_root: Path | None = None) -> Path:
    """Default ledger: data/registry/dimension-combos-ledger.json."""
    from batch.config import _project_root

    root = project_root or _project_root()
    return root / "data" / "registry" / "dimension-combos-ledger.json"


def combo_token(entry: dict[str, Any]) -> str:
    return (
        f"{entry['stateManagement']}|{entry['architecturePattern']}|"
        f"{entry['namingObfuscationRule']}|{entry['programmingStyle']}"
    )


def enumerate_full_combo_entries() -> list[dict[str, Any]]:
    """Build all 1400 legal combos, each with used=false."""
    entries: list[dict[str, Any]] = []
    pairs = sorted(_ALLOWED_STATE_PATTERN)
    for state_key, pattern_key in pairs:
        state = _KEY_TO_STATE_LABEL[state_key]
        pattern = _KEY_TO_PATTERN_LABEL[pattern_key]
        for naming in NAMING_OBFUSCATION_RULES:
            for style in PROGRAMMING_STYLES:
                entries.append(
                    {
                        "stateManagement": state,
                        "architecturePattern": pattern,
                        "namingObfuscationRule": naming,
                        "programmingStyle": style,
                        "used": False,
                    }
                )
    return entries


def enumerate_full_combos() -> frozenset[str]:
    """Token set for validation."""
    return frozenset(combo_token(e) for e in enumerate_full_combo_entries())


def empty_ledger() -> dict[str, Any]:
    return {
        "cycle": 1,
        "full": FULL_SIZE,
        "updatedAt": date.today().isoformat(),
        "combos": enumerate_full_combo_entries(),
    }


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"账本不存在: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("账本必须是 JSON 对象")
    return data


def write_ledger(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updatedAt"] = date.today().isoformat()
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def init_ledger(path: Path, *, overwrite: bool = False) -> bool:
    """Create ledger if missing. Returns True if created or overwritten."""
    if path.is_file() and not overwrite:
        return False
    write_ledger(path, empty_ledger())
    return True


def _combo_list(data: dict[str, Any]) -> list[dict[str, Any]] | None:
    combos = data.get("combos")
    if not isinstance(combos, list):
        return None
    return combos


def validate_ledger(path: Path) -> list[str]:
    """Return list of validation errors (empty = OK)."""
    errors: list[str] = []
    try:
        data = load_ledger(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)]

    full_set = enumerate_full_combos()

    if data.get("full") != FULL_SIZE:
        errors.append(f"full 应为 {FULL_SIZE}，实际为 {data.get('full')!r}")

    cycle = data.get("cycle")
    if not isinstance(cycle, int) or cycle < 1:
        errors.append(f"cycle 应为 >=1 的整数，实际为 {cycle!r}")

    combos = _combo_list(data)
    if combos is None:
        errors.append("combos 必须是数组")
        return errors

    if len(combos) != FULL_SIZE:
        errors.append(f"combos 长度应为 {FULL_SIZE}，实际为 {len(combos)}")

    seen: set[str] = set()
    for i, entry in enumerate(combos):
        if not isinstance(entry, dict):
            errors.append(f"combos[{i}] 必须是对象")
            continue
        for key in (
            "stateManagement",
            "architecturePattern",
            "namingObfuscationRule",
            "programmingStyle",
            "used",
        ):
            if key not in entry:
                errors.append(f"combos[{i}] 缺少字段 {key!r}")
        if entry.get("used") is not True and entry.get("used") is not False:
            errors.append(f"combos[{i}].used 必须是布尔值")
        token = combo_token(entry)
        if token in seen:
            errors.append(f"combos 重复: {token!r}")
        seen.add(token)
        if token not in full_set:
            errors.append(f"combos[{i}] 非法组合: {token!r}")

    if seen and seen != full_set:
        missing = full_set - seen
        extra = seen - full_set
        if missing:
            errors.append(f"combos 缺少 {len(missing)} 个合法组合")
        if extra:
            errors.append(f"combos 含 {len(extra)} 个非法组合")

    return errors


def ledger_status(path: Path) -> dict[str, Any]:
    data = load_ledger(path)
    combos = _combo_list(data) or []
    used_count = sum(1 for c in combos if c.get("used") is True)
    return {
        "path": str(path.resolve()),
        "cycle": data.get("cycle", 0),
        "full": data.get("full", FULL_SIZE),
        "used_count": used_count,
        "remaining": max(0, FULL_SIZE - used_count),
        "updatedAt": data.get("updatedAt", ""),
    }


def reset_ledger(path: Path) -> dict[str, Any]:
    data = load_ledger(path)
    cycle = data.get("cycle", 1)
    if not isinstance(cycle, int):
        cycle = 1
    new_data = empty_ledger()
    new_data["cycle"] = cycle + 1
    write_ledger(path, new_data)
    return new_data


def _remaining_indices(combos: list[dict[str, Any]]) -> list[int]:
    return [i for i, c in enumerate(combos) if c.get("used") is not True]


def _maybe_auto_reset(data: dict[str, Any]) -> bool:
    """Reset cycle when no remaining combos. Returns True if reset."""
    combos = _combo_list(data)
    if combos is None or _remaining_indices(combos):
        return False
    cycle = data.get("cycle", 1)
    if not isinstance(cycle, int):
        cycle = 1
    data["cycle"] = cycle + 1
    for entry in combos:
        entry["used"] = False
    return True


def _row_needs_fill(row: dict[str, str], *, force: bool) -> bool:
    if force:
        return True
    return any(not (row.get(col) or "").strip() for col in _DIM_COLS)


def _apply_combo_to_row(row: dict[str, str], entry: dict[str, Any]) -> None:
    row[COL_STATE_MANAGEMENT] = entry["stateManagement"]
    row[COL_ARCHITECTURE] = entry["architecturePattern"]
    row[COL_NAMING_RULE] = entry["namingObfuscationRule"]
    row[COL_PROGRAMMING_STYLE] = entry["programmingStyle"]


def _row_combo_token(row: dict[str, str]) -> str | None:
    parts = [row.get(col, "").strip() for col in _DIM_COLS]
    if not all(parts):
        return None
    return "|".join(parts)


def _find_combo_index(combos: list[dict[str, Any]], token: str) -> int | None:
    for i, entry in enumerate(combos):
        if combo_token(entry) == token:
            return i
    return None


def _diversity_limits(n: int) -> dict[str, int]:
    return {
        "state": diversity_cap(n, 6),
        "arch": diversity_cap(n, 5),
        "pair": diversity_cap(n, 20),
    }


def _empty_diversity_counts() -> dict[str, Counter]:
    return {"state": Counter(), "arch": Counter(), "pair": Counter()}


def _add_to_counts(counts: dict[str, Counter], entry: dict[str, Any]) -> None:
    state = entry["stateManagement"]
    arch = entry["architecturePattern"]
    counts["state"][state] += 1
    counts["arch"][arch] += 1
    counts["pair"][(state, arch)] += 1


def _can_add_combo(
    counts: dict[str, Counter], entry: dict[str, Any], limits: dict[str, int]
) -> bool:
    state = entry["stateManagement"]
    arch = entry["architecturePattern"]
    pair = (state, arch)
    if counts["state"][state] + 1 > limits["state"]:
        return False
    if counts["arch"][arch] + 1 > limits["arch"]:
        return False
    if counts["pair"][pair] + 1 > limits["pair"]:
        return False
    return True


def _release_row_combo(combos: list[dict[str, Any]], row: dict[str, str]) -> None:
    token = _row_combo_token(row)
    if not token:
        return
    idx = _find_combo_index(combos, token)
    if idx is not None:
        combos[idx]["used"] = False


def _assign_diverse_combos(
    rows: list[dict[str, str]],
    combos: list[dict[str, Any]],
    *,
    preserve_apps: frozenset[str],
    rng: random.Random,
) -> int:
    """Assign combos to non-preserved rows while satisfying batch diversity caps."""
    n = len(rows)
    limits = _diversity_limits(n)
    counts = _empty_diversity_counts()

    for row in rows:
        app = (row.get(COL_NAME) or "").strip()
        if app in preserve_apps:
            token = _row_combo_token(row)
            if not token:
                raise ValueError(f"{app} 四维不完整，无法保留")
            idx = _find_combo_index(combos, token)
            if idx is None:
                raise ValueError(f"{app} 四维组合不在账本: {token}")
            combos[idx]["used"] = True
            _add_to_counts(counts, combos[idx])

    to_assign = [
        row
        for row in rows
        if (row.get(COL_NAME) or "").strip() not in preserve_apps
    ]
    for row in to_assign:
        _release_row_combo(combos, row)

    rng.shuffle(to_assign)
    assigned = 0
    for row in to_assign:
        remaining = _remaining_indices(combos)
        valid = [
            i
            for i in remaining
            if _can_add_combo(counts, combos[i], limits)
        ]
        if not valid:
            app = (row.get(COL_NAME) or "").strip()
            raise RuntimeError(
                f"无法为 {app} 分配满足批内多样性的四维组合"
            )
        pick = rng.choice(valid)
        entry = combos[pick]
        entry["used"] = True
        _apply_combo_to_row(row, entry)
        _add_to_counts(counts, entry)
        assigned += 1
    return assigned


def draw_dimensions_to_csv(
    csv_path: Path,
    ledger_path: Path,
    *,
    force: bool = False,
    preserve_apps: frozenset[str] | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Assign dimension columns from ledger; mark combos used=true."""
    from batch.csv_tasks import load_task_csv_raw, write_task_csv_rows

    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV 不存在: {csv_path}")

    data = load_ledger(ledger_path)
    combos = _combo_list(data)
    if combos is None:
        raise ValueError("账本 combos 无效")

    meta, rows, fieldnames = load_task_csv_raw(csv_path)
    for col in _DIM_COLS:
        if col not in fieldnames:
            raise ValueError(f"CSV 缺少列 {col!r}: {csv_path}")

    preserve = preserve_apps or frozenset()
    assigned = 0
    skipped = 0
    reset_count = 0
    randomizer = rng or random.Random()

    if force and preserve:
        assigned = _assign_diverse_combos(
            rows, combos, preserve_apps=preserve, rng=randomizer
        )
        skipped = len(rows) - assigned
    else:
        for row in rows:
            app = (row.get(COL_NAME) or "").strip()
            if app in preserve:
                token = _row_combo_token(row)
                if token:
                    idx = _find_combo_index(combos, token)
                    if idx is not None:
                        combos[idx]["used"] = True
                skipped += 1
                continue
            if not _row_needs_fill(row, force=force):
                skipped += 1
                continue

            remaining = _remaining_indices(combos)
            if not remaining:
                if _maybe_auto_reset(data):
                    reset_count += 1
                    remaining = _remaining_indices(combos)
                if not remaining:
                    raise RuntimeError("账本无可用组合（重置后仍为空）")

            pick = randomizer.choice(remaining)
            entry = combos[pick]
            entry["used"] = True
            _apply_combo_to_row(row, entry)
            assigned += 1

    write_task_csv_rows(csv_path, meta, rows, fieldnames)
    write_ledger(ledger_path, data)

    st = ledger_status(ledger_path)
    return {
        "csv": str(csv_path.resolve()),
        "assigned": assigned,
        "skipped": skipped,
        "reset_count": reset_count,
        "used_count": st["used_count"],
        "remaining": st["remaining"],
        "cycle": st["cycle"],
    }


def print_status(path: Path) -> None:
    st = ledger_status(path)
    print(f"账本: {st['path']}")
    print(f"cycle: {st['cycle']}")
    print(f"已用: {st['used_count']}/{st['full']}")
    print(f"剩余: {st['remaining']}")
    if st["updatedAt"]:
        print(f"updatedAt: {st['updatedAt']}")


def _build_parser(prog: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=prog,
        description="四维抽卡全局账本 dimension-combos-ledger.json",
    )
    p.add_argument(
        "--ledger",
        type=Path,
        default=None,
        help="账本路径（默认 data/registry/dimension-combos-ledger.json）",
    )
    sub = p.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="初始化完整账本（1400 条 combos）")
    init_p.add_argument(
        "--overwrite",
        action="store_true",
        help="覆盖已存在账本",
    )

    sub.add_parser("status", help="查看 cycle / 已用 / 剩余")
    sub.add_parser("validate", help="校验 JSON 与 1400 组合完整性")

    reset_p = sub.add_parser("reset", help="cycle+1 并将全部 combos.used 置 false")
    reset_p.add_argument(
        "--force",
        action="store_true",
        help="确认重置（必填，否则拒绝）",
    )

    draw_p = sub.add_parser(
        "draw",
        help="从账本抽卡写入 CSV 四维度列，并标记 combos.used=true",
    )
    draw_p.add_argument(
        "--csv",
        type=Path,
        default=None,
        metavar="CSV",
        help="task.csv 路径（默认项目根 task.csv）",
    )
    draw_p.add_argument(
        "--force",
        action="store_true",
        help="覆盖已有四维度列",
    )
    draw_p.add_argument(
        "--preserve-apps",
        default="",
        help="保留这些应用的四维不变（逗号分隔，需配合 --force）",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    prog = Path(sys.argv[0]).name
    args = _build_parser(prog).parse_args(argv)
    path = args.ledger or ledger_path()

    if args.command == "init":
        created = init_ledger(path, overwrite=args.overwrite)
        if created:
            print(f">>> 已创建账本（{FULL_SIZE} 条 combos）: {path.resolve()}")
        else:
            print(f">>> 账本已存在，未覆盖（可用 init --overwrite）: {path.resolve()}")
        return 0

    if args.command == "status":
        if not path.is_file():
            print(f"错误: 账本不存在，请先 init: {path}", file=sys.stderr)
            return 1
        print_status(path)
        return 0

    if args.command == "validate":
        if not path.is_file():
            print(f"错误: 账本不存在: {path}", file=sys.stderr)
            return 1
        errors = validate_ledger(path)
        if errors:
            for err in errors:
                print(f"FAIL: {err}", file=sys.stderr)
            return 1
        print(f">>> 账本校验通过 ({path.resolve()})")
        return 0

    if args.command == "reset":
        if not args.force:
            print("错误: reset 需要 --force 确认", file=sys.stderr)
            return 1
        if not path.is_file():
            print(f"错误: 账本不存在，请先 init: {path}", file=sys.stderr)
            return 1
        data = reset_ledger(path)
        print(f">>> 已重置账本 cycle → {data['cycle']}, 全部 combos.used=false")
        print(f"    路径: {path.resolve()}")
        return 0

    if args.command == "draw":
        if not path.is_file():
            print(f"错误: 账本不存在，请先 init: {path}", file=sys.stderr)
            return 1
        csv_target = args.csv
        if csv_target is None:
            from batch.task_schema import task_csv_path
            from batch.config import _project_root

            csv_target = task_csv_path(_project_root())
        try:
            preserve = frozenset(
                a.strip()
                for a in (args.preserve_apps or "").split(",")
                if a.strip()
            )
            result = draw_dimensions_to_csv(
                csv_target.resolve(),
                path,
                force=args.force,
                preserve_apps=preserve if preserve else None,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 1
        print(f">>> 抽卡完成: {result['csv']}")
        print(f"    分配 {result['assigned']} 行, 跳过 {result['skipped']} 行")
        if result["reset_count"]:
            print(f"    自动重置 cycle → {result['cycle']}（本轮 1400 已用完）")
        print(
            f"    账本: {result['used_count']}/{FULL_SIZE} 已用, "
            f"剩余 {result['remaining']}"
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
