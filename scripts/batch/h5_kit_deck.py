"""H5 kit deck: per-pack micro-UI kit eleven-dimension pick + task.csv fill."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from batch.decks import load_deck, ordered_cards_for_dim
from batch.pack_type import is_h5_shell
from batch.task_schema import (
    COL_H5_ROUTER_PATTERN,
    COL_H5_SCREEN_PATTERN,
    COL_H5_STATE_MODEL,
    COL_KIT_ATOM_GRANULARITY,
    COL_KIT_ATOM_SET,
    COL_KIT_CSS_METHODOLOGY,
    COL_KIT_DOM_SHAPE,
    COL_KIT_JS_NAMESPACE,
    COL_KIT_JS_PATTERN,
    COL_KIT_MOTION_APPROACH,
    COL_KIT_STORAGE_ADAPTER,
    COL_NAME,
    COL_PACK_TYPE,
    H5_KIT_COLUMNS,
    H5_KIT_DIM_TO_CSV,
    H5_KIT_PICK_ORDER,
)

H5_KIT_DECK_NAME = "h5-kit-deck.json"
H5_KIT_COMPAT_NAME = "h5-kit-compat-matrix.json"
H5_KIT_LEDGER_NAME = "h5-kit-combo-ledger.json"


def h5_kit_deck_path(project_dir: Path) -> Path:
    return project_dir / "data" / "decks" / H5_KIT_DECK_NAME


def h5_kit_compat_path(project_dir: Path) -> Path:
    return project_dir / "data" / "decks" / H5_KIT_COMPAT_NAME


def h5_kit_ledger_path(project_dir: Path) -> Path:
    return project_dir / "data" / "registry" / H5_KIT_LEDGER_NAME


def load_kit_compat_matrix(project_dir: Path) -> dict[str, Any]:
    path = h5_kit_compat_path(project_dir)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def load_h5_kit_pools(project_dir: Path) -> dict[str, list[str]]:
    deck = load_deck(h5_kit_deck_path(project_dir))
    dims = deck.get("dimensions") or {}
    pools: dict[str, list[str]] = {}
    if not isinstance(dims, dict):
        raise ValueError("h5-kit-deck dimensions 无效")
    for deck_dim, csv_col in H5_KIT_DIM_TO_CSV.items():
        spec = dims.get(deck_dim) or {}
        cards = spec.get("cards") if isinstance(spec, dict) else []
        pools[csv_col] = [str(c) for c in (cards or []) if c]
    missing = [c for c in H5_KIT_COLUMNS if not pools.get(c)]
    if missing:
        raise ValueError(f"h5-kit 牌池缺少列: {', '.join(missing)}")
    return pools


def _atom_set_has_mark(atom_set: str, compat: dict[str, Any]) -> bool:
    token_map = compat.get("atomSetMarkTokens") or {}
    if isinstance(token_map, dict) and atom_set in token_map:
        return bool(token_map[atom_set])
    return "mark" in atom_set.split("/")


def filter_kit_cards(
    csv_col: str,
    cards: list[str],
    selections: dict[str, str],
    compat: dict[str, Any],
) -> list[str]:
    """Return cards compatible with already-picked kit dims."""
    result = list(cards)

    required_pairs = compat.get("requiredPairs") or {}
    if isinstance(required_pairs, dict):
        for src_col_key, mapping in required_pairs.items():
            src_csv = H5_KIT_DIM_TO_CSV.get(src_col_key) or src_col_key
            src_val = selections.get(src_csv, "")
            if not src_val or not isinstance(mapping, dict):
                continue
            req_for_src = mapping.get(src_val) or {}
            if not isinstance(req_for_src, dict):
                continue
            for tgt_col_key, allowed in req_for_src.items():
                tgt_csv = H5_KIT_DIM_TO_CSV.get(tgt_col_key) or tgt_col_key
                if tgt_csv != csv_col or not isinstance(allowed, list):
                    continue
                allowed_set = {str(v) for v in allowed}
                result = [c for c in result if c in allowed_set]

    dom_rules = compat.get("domShapeRequiresMark") or {}
    dom_shape = selections.get(COL_KIT_DOM_SHAPE, "")
    if csv_col == COL_KIT_ATOM_SET and dom_shape and isinstance(dom_rules, dict):
        rule = dom_rules.get(dom_shape) or {}
        if isinstance(rule, dict) and rule.get("kitAtomSetMustContain") == "mark":
            result = [c for c in result if _atom_set_has_mark(c, compat)]

    if csv_col == COL_KIT_DOM_SHAPE and isinstance(dom_rules, dict):
        atom_set = selections.get(COL_KIT_ATOM_SET, "")
        if atom_set and not _atom_set_has_mark(atom_set, compat):
            blocked = {k for k, v in dom_rules.items() if isinstance(v, dict)}
            result = [c for c in result if c not in blocked]

    return result or list(cards)


def _kit_combo_hash(dims: dict[str, str]) -> str:
    parts = [f"{col}={dims.get(col, '')}" for col in H5_KIT_COLUMNS]
    joined = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(joined).hexdigest()[:16]


def _load_kit_ledger(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"apps": {}, "hashes": {}, "classFingerprints": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"apps": {}, "hashes": {}, "classFingerprints": {}}
    data.setdefault("apps", {})
    data.setdefault("hashes", {})
    data.setdefault("classFingerprints", {})
    return data


def _save_kit_ledger(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pick_h5_kit_dims(
    *,
    pools: dict[str, list[str]],
    compat: dict[str, Any],
    batch_id: str,
    app_name: str,
    used_hashes: set[str],
    cooldown_values: dict[str, set[str]],
) -> dict[str, str]:
    """Pick kit + H5 arch columns in deck pick order."""
    selections: dict[str, str] = {}
    used_in_pick: set[str] = set()

    for deck_dim in H5_KIT_PICK_ORDER:
        csv_col = H5_KIT_DIM_TO_CSV[deck_dim]
        all_cards = pools.get(csv_col) or []
        cards = filter_kit_cards(csv_col, all_cards, selections, compat)
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
            h = _kit_combo_hash(trial)
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

    h = _kit_combo_hash(selections)
    if h in used_hashes:
        raise RuntimeError(f"{app_name} Kit 十一维组合与 ledger/本批重复")
    used_hashes.add(h)
    return selections


def _kit_dims_from_raw(raw: dict[str, str]) -> dict[str, str]:
    return {col: (raw.get(col) or "").strip() for col in H5_KIT_COLUMNS}


def _register_kit_in_ledger(
    ledger: dict[str, Any],
    *,
    app: str,
    batch_id: str,
    kit_dims: dict[str, str],
    used_hashes: set[str],
) -> str:
    h = _kit_combo_hash(kit_dims)
    stale = [k for k, v in (ledger.get("hashes") or {}).items() if v == app and k != h]
    for k in stale:
        ledger.setdefault("hashes", {}).pop(k, None)
        used_hashes.discard(k)
    ledger.setdefault("apps", {})[app] = {
        "batchId": batch_id,
        "hash": h,
        "kit": kit_dims,
    }
    ledger.setdefault("hashes", {})[h] = app
    used_hashes.add(h)
    return h


def draw_h5_kit_to_csv(
    csv_path: Path,
    project_dir: Path,
    *,
    batch_id: str,
    force: bool = False,
    apps: list[str] | None = None,
) -> dict[str, Any]:
    from batch.csv_tasks import load_task_csv_raw, write_task_csv_rows

    pools = load_h5_kit_pools(project_dir)
    compat = load_kit_compat_matrix(project_dir)
    led_path = h5_kit_ledger_path(project_dir)
    ledger = _load_kit_ledger(led_path)

    meta, rows_raw, fieldnames = load_task_csv_raw(csv_path)
    bid = batch_id or meta.batch_id or "default"
    only = {a.strip() for a in (apps or []) if a.strip()}

    used_hashes: set[str] = set(ledger.get("hashes") or {})
    cooldown: dict[str, set[str]] = {col: set() for col in H5_KIT_COLUMNS}

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

        kit_full = all((raw.get(col) or "").strip() for col in H5_KIT_COLUMNS)
        if kit_full and not force:
            kit_dims = _kit_dims_from_raw(raw)
            existing = (ledger.get("apps") or {}).get(app) or {}
            h = _kit_combo_hash(kit_dims)
            if existing.get("hash") != h:
                _register_kit_in_ledger(
                    ledger,
                    app=app,
                    batch_id=bid,
                    kit_dims=kit_dims,
                    used_hashes=used_hashes,
                )
                synced.append(app)
            skipped.append(app)
            continue

        if ledger.get("apps", {}).get(app) and force:
            old_h = ledger["apps"][app].get("hash")
            if old_h and old_h in used_hashes:
                used_hashes.discard(old_h)

        kit_dims = pick_h5_kit_dims(
            pools=pools,
            compat=compat,
            batch_id=bid,
            app_name=app,
            used_hashes=used_hashes,
            cooldown_values=cooldown,
        )
        for col, val in kit_dims.items():
            raw[col] = val

        h = _kit_combo_hash(kit_dims)
        _register_kit_in_ledger(
            ledger,
            app=app,
            batch_id=bid,
            kit_dims=kit_dims,
            used_hashes=used_hashes,
        )
        drawn.append(app)

    write_task_csv_rows(csv_path, meta, rows_raw, fieldnames)
    _save_kit_ledger(led_path, ledger)

    return {
        "drawn": drawn,
        "skipped": skipped,
        "synced": synced,
        "dimensions": len(H5_KIT_COLUMNS),
    }


def format_h5_kit_deck_block(row: object) -> str:
    from batch.csv_tasks import CsvTaskRow

    if not isinstance(row, CsvTaskRow):
        return ""
    lines = ["[H5 Kit Deck — from task.csv, MANDATORY]"]
    for col in H5_KIT_COLUMNS:
        val = getattr(row, _kit_attr(col), "")
        if val:
            lines.append(f"- {col}: {val}")
    lines.append(
        "Build per-pack micro-UI kit + H5 state/router/screen strictly per these 11 dims; "
        "see H5壳Micro-UI Kit约束.md and H5去风味规范.md §1.5–§1.9."
    )
    scope = format_h5_flutter_scope_note(row)
    if scope:
        lines.append("")
        lines.append(scope)
    return "\n".join(lines)


# Soft hint when Agent reads Flutter CSV dims — H5 business uses h5* columns instead.
_FLUTTER_H5_STATE_HINT: dict[str, str] = {
    "GETX": "prefer centralized-store or observable-signals",
    "SetState": "prefer centralized-store or imperative-dom",
    "Bloc": "prefer event-bus-driven",
    "Provider": "prefer per-screen-scope",
    "MobX": "prefer observable-signals",
}

_FLUTTER_H5_ARCH_HINT: dict[str, str] = {
    "MVP": "prefer controller-view",
    "MVVM": "prefer component-instance",
    "MVC": "prefer controller-view",
    "VIPER": "prefer controller-view + per-file roles",
    "简单 MV": "prefer functional-render or template-clone",
}


def format_h5_flutter_scope_note(row: object) -> str:
    from batch.csv_tasks import CsvTaskRow

    if not isinstance(row, CsvTaskRow):
        return ""
    sm = (row.state_management or "").strip()
    arch = (row.architecture_pattern or "").strip()
    state_hint = _FLUTTER_H5_STATE_HINT.get(sm, "")
    arch_hint = _FLUTTER_H5_ARCH_HINT.get(arch, "")
    lines = [
        "[Flutter CSV dims — shell scope only for h5_shell]",
        f"- 状态管理={sm} → Flutter 壳 WebView/Bridge 组织 ONLY; H5 业务状态看 h5StateModel"
        + (f" (soft map: {state_hint})" if state_hint else ""),
        f"- 架构模式={arch} → Flutter 壳目录 ONLY; H5 屏架构看 h5ScreenPattern/h5RouterPattern"
        + (f" (soft map: {arch_hint})" if arch_hint else ""),
        "- Do NOT build full Flutter MVP/MVVM layers; keep shell ≤5 dart files.",
    ]
    return "\n".join(lines)


def _kit_attr(col: str) -> str:
    mapping = {
        COL_KIT_ATOM_SET: "kit_atom_set",
        COL_KIT_CSS_METHODOLOGY: "kit_css_methodology",
        COL_KIT_ATOM_GRANULARITY: "kit_atom_granularity",
        COL_KIT_DOM_SHAPE: "kit_dom_shape",
        COL_KIT_JS_PATTERN: "kit_js_pattern",
        COL_KIT_JS_NAMESPACE: "kit_js_namespace",
        COL_KIT_STORAGE_ADAPTER: "kit_storage_adapter",
        COL_KIT_MOTION_APPROACH: "kit_motion_approach",
        COL_H5_STATE_MODEL: "h5_state_model",
        COL_H5_ROUTER_PATTERN: "h5_router_pattern",
        COL_H5_SCREEN_PATTERN: "h5_screen_pattern",
    }
    return mapping[col]


def kit_atom_roots(atom_set: str) -> list[str]:
    return [p.strip() for p in (atom_set or "").split("/") if p.strip()]
