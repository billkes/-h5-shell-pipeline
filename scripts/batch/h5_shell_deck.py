"""H5 shell Bridge deck: compat-aware pick + task.csv fill (Flutter vs native runtime)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from batch.decks import load_deck, ordered_cards_for_dim
from batch.pack_type import (
    expected_webview_engine,
    h5_shell_runtime,
    is_flutter_runtime,
    is_h5_shell,
    is_native_ios_runtime,
)
from batch.task_schema import (
    COL_BRIDGE_CALLBACK_STYLE,
    COL_BRIDGE_CALL_STYLE,
    COL_BRIDGE_ENVELOPE,
    COL_BRIDGE_ERROR_CODE,
    COL_BRIDGE_INJECT_TIMING,
    COL_MEDIA_SERVE,
    COL_NAME,
    COL_PACK_TYPE,
    COL_WEBVIEW_ENGINE,
    H5_SHELL_BRIDGE_COLUMNS,
    H5_SHELL_BRIDGE_DIM_TO_CSV,
    H5_SHELL_BRIDGE_PICK_ORDER,
)

H5_SHELL_DECK_NAME = "h5-shell-deck.json"
H5_NATIVE_SHELL_DECK_NAME = "h5-native-shell-deck.json"
H5_SHELL_COMPAT_NAME = "h5-shell-compat-matrix.json"
H5_NATIVE_SHELL_COMPAT_NAME = "h5-native-shell-compat-matrix.json"
H5_SHELL_LEDGER_NAME = "h5-shell-combo-ledger.json"


def h5_shell_deck_path(project_dir: Path | str, *, pack_type: str = "") -> Path:
    root = Path(project_dir)
    if is_native_ios_runtime(pack_type):
        return root / "data" / "decks" / H5_NATIVE_SHELL_DECK_NAME
    return root / "data" / "decks" / H5_SHELL_DECK_NAME


def h5_shell_compat_path(project_dir: Path | str, *, pack_type: str = "") -> Path:
    root = Path(project_dir)
    if is_native_ios_runtime(pack_type):
        return root / "data" / "decks" / H5_NATIVE_SHELL_COMPAT_NAME
    return root / "data" / "decks" / H5_SHELL_COMPAT_NAME


def h5_shell_ledger_path(project_dir: Path) -> Path:
    return project_dir / "data" / "registry" / H5_SHELL_LEDGER_NAME


def load_compat_matrix(project_dir: Path, *, pack_type: str = "") -> dict[str, Any]:
    path = h5_shell_compat_path(project_dir, pack_type=pack_type)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _locked_webview_engine(pack_type: str, compat: dict[str, Any]) -> str:
    """Native shells lock webviewEngine from pack_type (no random engine flip)."""
    locked = expected_webview_engine(pack_type)
    if locked:
        return locked
    mapping = compat.get("packTypeEngine") or {}
    if isinstance(mapping, dict):
        return str(mapping.get(pack_type) or "").strip()
    return ""


def load_h5_bridge_pools(project_dir: Path, *, pack_type: str = "") -> dict[str, list[str]]:
    deck_path = h5_shell_deck_path(project_dir, pack_type=pack_type)
    deck = load_deck(deck_path)
    dims = deck.get("dimensions") or {}
    pools: dict[str, list[str]] = {}
    if not isinstance(dims, dict):
        raise ValueError(f"{deck_path.name} dimensions 无效")
    for deck_dim, csv_col in H5_SHELL_BRIDGE_DIM_TO_CSV.items():
        spec = dims.get(deck_dim) or {}
        cards = spec.get("cards") if isinstance(spec, dict) else []
        pools[csv_col] = [str(c) for c in (cards or []) if c]
    missing = [c for c in H5_SHELL_BRIDGE_COLUMNS if not pools.get(c)]
    if missing:
        raise ValueError(f"{deck_path.name} 牌池缺少列: {', '.join(missing)}")

    if is_native_ios_runtime(pack_type):
        compat = load_compat_matrix(project_dir, pack_type=pack_type)
        locked = _locked_webview_engine(pack_type, compat)
        if locked:
            pools[COL_WEBVIEW_ENGINE] = [locked]
    return pools


def filter_bridge_cards(
    csv_col: str,
    cards: list[str],
    selections: dict[str, str],
    compat: dict[str, Any],
) -> list[str]:
    """Return cards compatible with already-picked bridge dims."""
    engine = selections.get(COL_WEBVIEW_ENGINE, "")
    engine_excludes = compat.get("engineExcludes") or {}
    card_requires = compat.get("cardRequiresEngine") or {}

    excluded: set[str] = set()
    if engine and isinstance(engine_excludes, dict):
        block = engine_excludes.get(engine) or {}
        if isinstance(block, dict):
            for col, vals in block.items():
                mapped = H5_SHELL_BRIDGE_DIM_TO_CSV.get(col) or col
                if mapped == csv_col and isinstance(vals, list):
                    excluded.update(str(v) for v in vals)

    result: list[str] = []
    for card in cards:
        if card in excluded:
            continue
        required = card_requires.get(card) if isinstance(card_requires, dict) else None
        if required and engine and required != engine:
            continue
        result.append(card)
    return result or list(cards)


def _bridge_combo_hash(dims: dict[str, str], *, shell_runtime: str = "") -> str:
    parts = [f"runtime={shell_runtime or 'flutter'}"] + [
        f"{col}={dims.get(col, '')}" for col in H5_SHELL_BRIDGE_COLUMNS
    ]
    joined = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(joined).hexdigest()[:16]


def _load_bridge_ledger(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"apps": {}, "hashes": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"apps": {}, "hashes": {}}
    data.setdefault("apps", {})
    data.setdefault("hashes", {})
    return data


def _save_bridge_ledger(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pick_h5_bridge_dims(
    *,
    pools: dict[str, list[str]],
    compat: dict[str, Any],
    batch_id: str,
    app_name: str,
    pack_type: str,
    used_hashes: set[str],
    cooldown_values: dict[str, set[str]],
) -> dict[str, str]:
    """Pick 7 bridge columns; webviewEngine first (locked for native shells)."""
    selections: dict[str, str] = {}
    used_in_pick: set[str] = set()
    runtime = h5_shell_runtime(pack_type)
    locked_engine = _locked_webview_engine(pack_type, compat)

    for deck_dim in H5_SHELL_BRIDGE_PICK_ORDER:
        csv_col = H5_SHELL_BRIDGE_DIM_TO_CSV[deck_dim]
        all_cards = pools.get(csv_col) or []
        if deck_dim == "webviewEngine" and locked_engine:
            selections[csv_col] = locked_engine
            used_in_pick.add(locked_engine)
            continue

        cards = filter_bridge_cards(csv_col, all_cards, selections, compat)
        if not cards:
            raise RuntimeError(f"{app_name} 的 {csv_col} 无兼容可选卡")

        cool = cooldown_values.get(csv_col, set())
        ordered = ordered_cards_for_dim(
            cards,
            {},
            batch_id=batch_id,
            app_name=app_name,
            csv_col=csv_col,
        )
        chosen = ""
        for card in ordered:
            if card in used_in_pick or card in cool:
                continue
            trial = {**selections, csv_col: card}
            h = _bridge_combo_hash(trial, shell_runtime=runtime)
            if h in used_hashes:
                continue
            chosen = card
            break
        if not chosen:
            for card in ordered:
                if card not in used_in_pick:
                    chosen = card
                    break
        if not chosen:
            raise RuntimeError(f"无法为 {app_name} 分配 {csv_col}")
        selections[csv_col] = chosen
        used_in_pick.add(chosen)

    h = _bridge_combo_hash(selections, shell_runtime=runtime)
    if h in used_hashes:
        raise RuntimeError(f"{app_name} Bridge 七维组合与 ledger/本批重复")
    used_hashes.add(h)
    return selections


def _bridge_dims_from_raw(raw: dict[str, str]) -> dict[str, str]:
    return {col: (raw.get(col) or "").strip() for col in H5_SHELL_BRIDGE_COLUMNS}


def _register_bridge_in_ledger(
    ledger: dict[str, Any],
    *,
    app: str,
    batch_id: str,
    pack_type: str,
    bridge_dims: dict[str, str],
    used_hashes: set[str],
) -> str:
    runtime = h5_shell_runtime(pack_type)
    h = _bridge_combo_hash(bridge_dims, shell_runtime=runtime)
    stale = [k for k, v in (ledger.get("hashes") or {}).items() if v == app and k != h]
    for k in stale:
        ledger.setdefault("hashes", {}).pop(k, None)
        used_hashes.discard(k)
    ledger.setdefault("apps", {})[app] = {
        "batchId": batch_id,
        "hash": h,
        "shellRuntime": runtime,
        "packType": pack_type,
        "bridge": bridge_dims,
    }
    ledger.setdefault("hashes", {})[h] = app
    used_hashes.add(h)
    return h


def draw_h5_shell_to_csv(
    csv_path: Path,
    project_dir: Path,
    *,
    batch_id: str,
    force: bool = False,
    apps: list[str] | None = None,
) -> dict[str, Any]:
    from batch.csv_tasks import load_task_csv_raw, write_task_csv_rows

    led_path = h5_shell_ledger_path(project_dir)
    ledger = _load_bridge_ledger(led_path)

    meta, rows_raw, fieldnames = load_task_csv_raw(csv_path)
    bid = batch_id or meta.batch_id or "default"
    only = {a.strip() for a in (apps or []) if a.strip()}

    used_hashes: set[str] = set(ledger.get("hashes") or {})
    cooldown: dict[str, set[str]] = {col: set() for col in H5_SHELL_BRIDGE_COLUMNS}

    drawn: list[str] = []
    skipped: list[str] = []
    synced: list[str] = []

    for raw in rows_raw:
        app = (raw.get(COL_NAME) or "").strip()
        if not app:
            continue
        if only and app not in only:
            continue
        pack = (raw.get(COL_PACK_TYPE) or "").strip()
        if not is_h5_shell(pack):
            continue

        pools = load_h5_bridge_pools(project_dir, pack_type=pack)
        compat = load_compat_matrix(project_dir, pack_type=pack)
        runtime = h5_shell_runtime(pack)

        bridge_full = all((raw.get(col) or "").strip() for col in H5_SHELL_BRIDGE_COLUMNS)

        if bridge_full and not force:
            bridge_dims = _bridge_dims_from_raw(raw)
            if all(bridge_dims.values()):
                existing = (ledger.get("apps") or {}).get(app) or {}
                h = _bridge_combo_hash(bridge_dims, shell_runtime=runtime)
                if existing.get("hash") != h or existing.get("shellRuntime") != runtime:
                    _register_bridge_in_ledger(
                        ledger,
                        app=app,
                        batch_id=bid,
                        pack_type=pack,
                        bridge_dims=bridge_dims,
                        used_hashes=used_hashes,
                    )
                    synced.append(app)
            skipped.append(app)
            continue

        if ledger.get("apps", {}).get(app) and force:
            old_h = ledger["apps"][app].get("hash")
            if old_h and old_h in used_hashes:
                used_hashes.discard(old_h)

        bridge_dims = pick_h5_bridge_dims(
            pools=pools,
            compat=compat,
            batch_id=bid,
            app_name=app,
            pack_type=pack,
            used_hashes=used_hashes,
            cooldown_values=cooldown,
        )
        for col, val in bridge_dims.items():
            raw[col] = val

        _register_bridge_in_ledger(
            ledger,
            app=app,
            batch_id=bid,
            pack_type=pack,
            bridge_dims=bridge_dims,
            used_hashes=used_hashes,
        )
        drawn.append(app)

    write_task_csv_rows(csv_path, meta, rows_raw, fieldnames)
    _save_bridge_ledger(led_path, ledger)

    return {
        "drawn": drawn,
        "skipped": skipped,
        "synced": synced,
        "dimensions": len(H5_SHELL_BRIDGE_COLUMNS),
    }


def format_h5_shell_bridge_block(row: object) -> str:
    from batch.csv_tasks import CsvTaskRow

    if not isinstance(row, CsvTaskRow):
        return ""
    runtime = h5_shell_runtime(row.pack_type)
    deck_label = "Flutter" if is_flutter_runtime(row.pack_type) else "Native"
    lines = [
        f"[H5 Shell Bridge Deck — {deck_label} runtime, from task.csv, MANDATORY]",
        f"- shellRuntime: {runtime}",
        f"- packType: {row.pack_type}",
    ]
    for col in H5_SHELL_BRIDGE_COLUMNS:
        val = getattr(row, _bridge_attr(col), "")
        if val:
            lines.append(f"- {col}: {val}")
    if is_native_ios_runtime(row.pack_type):
        lines.append(
            "Implement WKWebView + WKScriptMessageHandler Bridge exactly per these draws "
            "and H5-Bridge协议.md (native host section)."
        )
    else:
        lines.append("Implement Bridge exactly per these draws and H5-Bridge协议.md.")
    return "\n".join(lines)


def bridge_deck_selections_from_row(row: object) -> dict[str, str]:
    """Build bridgeDeckSelections dict for 本包登记信息.json."""
    from batch.csv_tasks import CsvTaskRow

    if not isinstance(row, CsvTaskRow):
        return {}
    out: dict[str, str] = {}
    for col in H5_SHELL_BRIDGE_COLUMNS:
        val = getattr(row, _bridge_attr(col), "")
        if val:
            out[col] = val
    return out


def _bridge_attr(col: str) -> str:
    mapping = {
        COL_WEBVIEW_ENGINE: "webview_engine",
        COL_BRIDGE_CALL_STYLE: "bridge_call_style",
        COL_BRIDGE_CALLBACK_STYLE: "bridge_callback_style",
        COL_BRIDGE_ENVELOPE: "bridge_envelope",
        COL_MEDIA_SERVE: "media_serve",
        COL_BRIDGE_ERROR_CODE: "bridge_error_code",
        COL_BRIDGE_INJECT_TIMING: "bridge_inject_timing",
    }
    return mapping[col]
