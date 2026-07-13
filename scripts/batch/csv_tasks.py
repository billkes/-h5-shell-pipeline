"""Parse root ``task.csv`` — single source of truth for batch production."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from batch.pack_type import is_h5_shell
from batch.prod_a_registry import load_prod_a_registry, validate_batch_against_registry
from batch.queue import VALID_TYPES, QueueTask, load_queue
from batch.task_schema import (
    COL_ARCHITECTURE,
    COL_AUDIENCE,
    COL_CORE_SCENE,
    COL_FIRST_PRODUCT_CODE,
    COL_FULL_NAME,
    COL_GIT_URL,
    COL_LOCAL_FEATURE,
    COL_NAME,
    COL_NAMING_RULE,
    COL_PACK_TYPE,
    COL_PRIVACY_FILE,
    COL_PRIVACY_STYLE,
    COL_PRODUCT_FLOW,
    COL_PROGRAMMING_STYLE,
    COL_STATE_MANAGEMENT,
    COL_THEME_CN,
    COL_THEME_CODE,
    COL_TRACK,
    LEGACY_COLUMNS,
    H5_SHELL_BRIDGE_COLUMNS,
    H5_KIT_COLUMNS,
    COL_WEBVIEW_ENGINE,
    COL_BRIDGE_CALL_STYLE,
    COL_BRIDGE_CALLBACK_STYLE,
    COL_BRIDGE_ENVELOPE,
    COL_MEDIA_SERVE,
    COL_BRIDGE_ERROR_CODE,
    COL_BRIDGE_INJECT_TIMING,
    COL_KIT_ATOM_SET,
    COL_KIT_CSS_METHODOLOGY,
    COL_KIT_ATOM_GRANULARITY,
    COL_KIT_DOM_SHAPE,
    COL_KIT_JS_PATTERN,
    COL_KIT_JS_NAMESPACE,
    COL_KIT_STORAGE_ADAPTER,
    COL_KIT_MOTION_APPROACH,
    COL_H5_STATE_MODEL,
    COL_H5_ROUTER_PATTERN,
    COL_H5_SCREEN_PATTERN,
    STANDARD_COLUMNS,
    TaskCsvMeta,
    format_task_csv_header,
    parse_task_csv_meta,
)
from batch.theme_fields import format_theme_angle, parse_legacy_theme_angle, theme_task_description
from batch.xcode_delivery import parse_privacy_file_index

REQUIRED_COLUMNS = LEGACY_COLUMNS

STATE_MANAGEMENT_LABELS: tuple[str, ...] = (
    "GETX",
    "SetState",
    "Bloc",
    "Provider",
    "MobX",
    "Redux",
    "GetX",
)

ARCHITECTURE_PATTERN_LABELS: tuple[str, ...] = (
    "MVC",
    "MVP",
    "MVVM",
    "VIPER",
    "简单 MV",
)

_PATTERN_KEY_BY_LABEL: dict[str, str] = {
    "MVC": "mvc",
    "MVP": "mvp",
    "MVVM": "mvvm",
    "VIPER": "viper",
    "简单 MV": "simple_mv",
}

_ALLOWED_STATE_PATTERN: frozenset[tuple[str, str]] = frozenset(
    {
        ("getx", "mvc"),
        ("getx", "mvp"),
        ("getx", "mvvm"),
        ("getx", "viper"),
        ("getx", "simple_mv"),
        ("setstate", "mvc"),
        ("setstate", "mvp"),
        ("setstate", "viper"),
        ("setstate", "simple_mv"),
        ("bloc", "mvc"),
        ("bloc", "mvp"),
        ("bloc", "viper"),
        ("provider", "mvc"),
        ("provider", "mvp"),
        ("provider", "viper"),
        ("provider", "simple_mv"),
        ("mobx", "mvc"),
        ("mobx", "mvvm"),
        ("mobx", "viper"),
        ("redux", "mvp"),
    }
)

_STATE_KEY_BY_LABEL: dict[str, str] = {
    "getx": "getx",
    "setstate": "setstate",
    "bloc": "bloc",
    "provider": "provider",
    "mobx": "mobx",
    "redux": "redux",
}

NAMING_OBFUSCATION_RULES: tuple[str, ...] = (
    "双随机首段策略",
    "辅音核心策略",
    "倒序声母策略",
    "元音桥接策略",
    "批次声母嵌入策略",
    "双随机镜像策略",
    "单声母三随机策略",
    "元辅伪词策略",
    "应用名分段插入策略",
    "哈希域伪装策略",
)

PROGRAMMING_STYLES: tuple[str, ...] = (
    "美国人",
    "英国人",
    "德国人",
    "法国人",
    "俄罗斯人",
    "日本人",
    "中国人",
)

_PRIVACY_STYLE_RE = re.compile(r"风格\s*(\d+)", re.IGNORECASE)

@dataclass(frozen=True)
class CsvTaskRow:
    """One row from root ``task.csv`` (flat theme-library schema)."""

    name: str
    full_name: str
    state_management: str
    architecture_pattern: str
    naming_obfuscation_rule: str
    privacy_style: str
    privacy_file: str
    git_url: str
    first_product_code: str
    programming_style: str
    pack_type: str = ""
    theme_code: str = ""
    theme_cn: str = ""
    track: str = ""
    audience: str = ""
    core_scene: str = ""
    local_feature: str = ""
    product_flow: str = ""
    webview_engine: str = ""
    bridge_call_style: str = ""
    bridge_callback_style: str = ""
    bridge_envelope: str = ""
    media_serve: str = ""
    bridge_error_code: str = ""
    bridge_inject_timing: str = ""
    kit_atom_set: str = ""
    kit_css_methodology: str = ""
    kit_atom_granularity: str = ""
    kit_dom_shape: str = ""
    kit_js_pattern: str = ""
    kit_js_namespace: str = ""
    kit_storage_adapter: str = ""
    kit_motion_approach: str = ""
    h5_state_model: str = ""
    h5_router_pattern: str = ""
    h5_screen_pattern: str = ""

    @property
    def theme_angle(self) -> str:
        """English prompt block built from flat theme-library columns."""
        return format_theme_angle(self)


def _cell(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def normalize_state_management(raw: str) -> str:
    stripped = (raw or "").strip()
    if not stripped:
        return ""
    if stripped in STATE_MANAGEMENT_LABELS:
        return stripped
    compact = re.sub(r"\s+", "", stripped.lower())
    matches = [
        label
        for label in STATE_MANAGEMENT_LABELS
        if re.sub(r"\s+", "", label.lower()) == compact
    ]
    if not matches:
        return ""
    if len(matches) == 1:
        return matches[0]
    if compact == "getx":
        return "GetX" if stripped == "GetX" else "GETX"
    return matches[0]


def normalize_architecture_pattern(raw: str) -> str:
    stripped = (raw or "").strip()
    if not stripped:
        return ""
    if stripped in ARCHITECTURE_PATTERN_LABELS:
        return stripped
    upper = stripped.upper()
    for label in ARCHITECTURE_PATTERN_LABELS:
        if label.upper() == upper:
            return label
    compact = re.sub(r"\s+", "", stripped.lower())
    if compact in ("简单mv", "simplemv"):
        return "简单 MV"
    return ""


def architecture_pattern_key(label: str) -> str:
    return _PATTERN_KEY_BY_LABEL.get(label, "")


def state_management_key(label: str) -> str:
    return _STATE_KEY_BY_LABEL.get(re.sub(r"\s+", "", label.lower()), "")


def is_allowed_state_pattern(state_label: str, pattern_label: str) -> bool:
    state_key = state_management_key(state_label)
    pattern_key = architecture_pattern_key(pattern_label)
    return bool(state_key and pattern_key) and (
        state_key,
        pattern_key,
    ) in _ALLOWED_STATE_PATTERN


def normalize_naming_obfuscation_rule(raw: str) -> str:
    value = (raw or "").strip()
    return value if value in NAMING_OBFUSCATION_RULES else ""


def normalize_programming_style(raw: str) -> str:
    value = (raw or "").strip()
    return value if value in PROGRAMMING_STYLES else ""


def normalize_pack_type(raw: str, default: str = "tool_flutter") -> str:
    value = (raw or "").strip()
    return value if value in VALID_TYPES else default


def parse_privacy_style_number(raw: str) -> int | None:
    match = _PRIVACY_STYLE_RE.search((raw or "").strip())
    if not match:
        return None
    num = int(match.group(1))
    if 1 <= num <= 3:
        return num
    return None


def repo_dir_name_from_git_url(git_url: str) -> str:
    raw = (git_url or "").strip()
    if not raw:
        return ""
    if "://" not in raw and ":" in raw and "@" in raw:
        path = raw.rsplit(":", 1)[-1]
    else:
        path = urlparse(raw).path
    path = path.rsplit("/", 1)[-1]
    if path.endswith(".git"):
        return path[:-4]
    return path


from batch.pack_type import H5_FLUTTER_SHELL, H5_SHELL, h5_shell_runtime, is_h5_shell

# Output container suffixes: Mockoo-Swift, Hathoo-OC, Pawioo-Flutter
OUTPUT_CONTAINER_SUFFIXES: tuple[str, ...] = ("-Swift", "-OC", "-Flutter")


def shell_runtime_container_suffix(pack_type: str) -> str:
    """Map pack_type → container suffix (Swift / OC / Flutter)."""
    pt = (pack_type or "").strip()
    if not is_h5_shell(pt):
        return "Flutter"
    return {"swift": "Swift", "oc": "OC", "flutter": "Flutter"}[h5_shell_runtime(pt)]


def repo_container_name(
    app_name: str,
    git_url: str = "",
    *,
    pack_type: str = "",
) -> str:
    """Output container dir under ``output/`` (e.g. ``Buildioo-Swift``).

    H5 shell pipeline convention (aligned with Mockoo-Swift / Hathoo-OC):
    - ``h5_swift_shell`` → ``{AppName}-Swift``
    - ``h5_oc_shell`` → ``{AppName}-OC``
    - ``h5_shell`` / ``h5_flutter_shell`` → ``{AppName}-Flutter``

    ``git_url`` basename is used only when it already ends with a known suffix.
    """
    from_git = repo_dir_name_from_git_url(git_url)
    if any(from_git.endswith(suffix) for suffix in OUTPUT_CONTAINER_SUFFIXES):
        return from_git

    pt = (pack_type or "").strip()
    if is_h5_shell(pt):
        return f"{app_name}-{shell_runtime_container_suffix(pt)}"
    if pt in (H5_SHELL, H5_FLUTTER_SHELL):
        return f"{app_name}-Flutter"
    if from_git:
        return from_git
    return f"{app_name}-Flutter"


def app_workspace(output_dir: Path, repo_name: str, app_name: str) -> Path:
    container = repo_name or f"{app_name}-Flutter"
    return output_dir / container / app_name


def resolve_app_workspace(
    output_dir: Path,
    *,
    name: str,
    pack_type: str,
    git_url: str = "",
) -> Path:
    """Canonical Agent workspace: ``output/{App}-Swift|OC|Flutter/{App}/``."""
    from batch.config import safe_dir_name

    container = repo_container_name(name, git_url, pack_type=pack_type)
    return app_workspace(output_dir, container, safe_dir_name(name))


def output_workspace_exists(output_dir: Path, row: CsvTaskRow) -> bool:
    """True when this app's workspace dir already exists under ``output/``."""
    pack_type = (row.pack_type or "").strip() or "h5_swift_shell"
    return resolve_app_workspace(
        output_dir,
        name=row.name,
        pack_type=pack_type,
        git_url=row.git_url or "",
    ).is_dir()


def app_workspace_registry_entry(
    output_dir: Path,
    *,
    name: str,
    pack_type: str,
    git_url: str = "",
) -> dict[str, str]:
    """Serializable workspace record for ``batch-runs.json``."""
    container = repo_container_name(name, git_url, pack_type=pack_type)
    ws = resolve_app_workspace(
        output_dir, name=name, pack_type=pack_type, git_url=git_url
    )
    return {
        "name": name,
        "packType": pack_type,
        "container": container,
        "workspace": str(ws.resolve()),
    }


def _validate_headers(fieldnames: list[str] | None) -> None:
    if not fieldnames:
        raise ValueError("CSV 缺少表头")
    got = set(fieldnames)
    expected = set(STANDARD_COLUMNS)
    if got != expected:
        missing = expected - got
        extra = got - expected
        parts: list[str] = []
        if missing:
            parts.append("缺少列: " + ", ".join(sorted(missing)))
        if extra:
            parts.append("多余列: " + ", ".join(sorted(extra)))
        raise ValueError(
            "task.csv 列必须与标准 schema 完全一致（" + "；".join(parts) + "）"
        )


def _row_from_raw(raw: dict[str, str], name: str) -> CsvTaskRow:
    return CsvTaskRow(
        name=name,
        full_name=_cell(raw, COL_FULL_NAME),
        state_management=_cell(raw, COL_STATE_MANAGEMENT),
        architecture_pattern=_cell(raw, COL_ARCHITECTURE),
        naming_obfuscation_rule=_cell(raw, COL_NAMING_RULE),
        privacy_style=_cell(raw, COL_PRIVACY_STYLE),
        privacy_file=_cell(raw, COL_PRIVACY_FILE),
        git_url=_cell(raw, COL_GIT_URL),
        first_product_code=_cell(raw, COL_FIRST_PRODUCT_CODE),
        programming_style=_cell(raw, COL_PROGRAMMING_STYLE),
        pack_type=_cell(raw, COL_PACK_TYPE),
        theme_code=_cell(raw, COL_THEME_CODE),
        theme_cn=_cell(raw, COL_THEME_CN),
        track=_cell(raw, COL_TRACK),
        audience=_cell(raw, COL_AUDIENCE),
        core_scene=_cell(raw, COL_CORE_SCENE),
        local_feature=_cell(raw, COL_LOCAL_FEATURE),
        product_flow=_cell(raw, COL_PRODUCT_FLOW),
        webview_engine=_cell(raw, COL_WEBVIEW_ENGINE),
        bridge_call_style=_cell(raw, COL_BRIDGE_CALL_STYLE),
        bridge_callback_style=_cell(raw, COL_BRIDGE_CALLBACK_STYLE),
        bridge_envelope=_cell(raw, COL_BRIDGE_ENVELOPE),
        media_serve=_cell(raw, COL_MEDIA_SERVE),
        bridge_error_code=_cell(raw, COL_BRIDGE_ERROR_CODE),
        bridge_inject_timing=_cell(raw, COL_BRIDGE_INJECT_TIMING),
        kit_atom_set=_cell(raw, COL_KIT_ATOM_SET),
        kit_css_methodology=_cell(raw, COL_KIT_CSS_METHODOLOGY),
        kit_atom_granularity=_cell(raw, COL_KIT_ATOM_GRANULARITY),
        kit_dom_shape=_cell(raw, COL_KIT_DOM_SHAPE),
        kit_js_pattern=_cell(raw, COL_KIT_JS_PATTERN),
        kit_js_namespace=_cell(raw, COL_KIT_JS_NAMESPACE),
        kit_storage_adapter=_cell(raw, COL_KIT_STORAGE_ADAPTER),
        kit_motion_approach=_cell(raw, COL_KIT_MOTION_APPROACH),
        h5_state_model=_cell(raw, COL_H5_STATE_MODEL),
        h5_router_pattern=_cell(raw, COL_H5_ROUTER_PATTERN),
        h5_screen_pattern=_cell(raw, COL_H5_SCREEN_PATTERN),
    )


MANUAL_PREP_COLUMNS: tuple[str, ...] = (
    COL_PRIVACY_STYLE,
    COL_PRIVACY_FILE,
    COL_GIT_URL,
)


def _h5_kit_attr(col: str) -> str:
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


def _h5_bridge_attr(col: str) -> str:
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


def _validate_row_fields(
    row: CsvTaskRow,
    *,
    line_hint: str,
    strict_extended: bool = False,
    allow_pending_manual_fields: bool = False,
    project_dir: Path | None = None,
) -> None:
    missing: list[str] = []
    required: list[tuple[str, str]] = [
        (COL_NAME, row.name),
        (COL_FULL_NAME, row.full_name),
        (COL_STATE_MANAGEMENT, row.state_management),
        (COL_ARCHITECTURE, row.architecture_pattern),
        (COL_NAMING_RULE, row.naming_obfuscation_rule),
        (COL_FIRST_PRODUCT_CODE, row.first_product_code),
        (COL_PROGRAMMING_STYLE, row.programming_style),
    ]
    if not allow_pending_manual_fields:
        required.extend(
            (
                (COL_PRIVACY_STYLE, row.privacy_style),
                (COL_PRIVACY_FILE, row.privacy_file),
                (COL_GIT_URL, row.git_url),
            )
        )
    for col, val in required:
        if not val:
            missing.append(col)
    if missing:
        raise ValueError(f"{line_hint} 列不能为空: {', '.join(missing)}")

    state = normalize_state_management(row.state_management)
    if not state:
        raise ValueError(f"{line_hint} 状态管理无效: {row.state_management!r}")

    pattern = normalize_architecture_pattern(row.architecture_pattern)
    if not pattern:
        raise ValueError(f"{line_hint} 架构模式无效: {row.architecture_pattern!r}")

    if not is_allowed_state_pattern(state, pattern):
        raise ValueError(f"{line_hint} 状态管理/架构模式组合不在允许列表内")

    if not normalize_naming_obfuscation_rule(row.naming_obfuscation_rule):
        raise ValueError(f"{line_hint} 命名混淆规则无效")

    if not normalize_programming_style(row.programming_style):
        raise ValueError(f"{line_hint} 编程风格无效")

    if not allow_pending_manual_fields:
        if parse_privacy_style_number(row.privacy_style) is None:
            raise ValueError(f"{line_hint} 协议风格无效")
        if parse_privacy_file_index(row.privacy_file) is None:
            raise ValueError(f"{line_hint} 隐私文件无效")
    else:
        if row.privacy_style and parse_privacy_style_number(row.privacy_style) is None:
            raise ValueError(f"{line_hint} 协议风格无效")
        if row.privacy_file and parse_privacy_file_index(row.privacy_file) is None:
            raise ValueError(f"{line_hint} 隐私文件无效")

    if strict_extended:
        ext_missing: list[str] = []
        if not row.pack_type:
            ext_missing.append(COL_PACK_TYPE)
        for col, val in (
            (COL_THEME_CN, row.theme_cn),
            (COL_TRACK, row.track),
            (COL_AUDIENCE, row.audience),
            (COL_CORE_SCENE, row.core_scene),
            (COL_LOCAL_FEATURE, row.local_feature),
        ):
            if not val:
                ext_missing.append(col)
        h5 = is_h5_shell(row.pack_type)
        if h5:
            from batch.h5_shell_deck import load_h5_bridge_pools

            pools = load_h5_bridge_pools(project_dir or Path("."), pack_type=row.pack_type)
            for col in H5_SHELL_BRIDGE_COLUMNS:
                val = getattr(row, _h5_bridge_attr(col), "")
                if not val:
                    ext_missing.append(col)
                else:
                    pool = pools.get(col) or []
                    if pool and val not in pool:
                        raise ValueError(
                            f"{line_hint} {col}={val!r} 不在 h5-shell-deck 牌池"
                        )
            from batch.h5_kit_deck import load_h5_kit_pools

            kit_pools = load_h5_kit_pools(project_dir or Path("."))
            for col in H5_KIT_COLUMNS:
                val = getattr(row, _h5_kit_attr(col), "")
                if not val:
                    ext_missing.append(col)
                else:
                    pool = kit_pools.get(col) or []
                    if pool and val not in pool:
                        raise ValueError(
                            f"{line_hint} {col}={val!r} 不在 h5-kit-deck 牌池"
                        )
        if ext_missing:
            raise ValueError(
                f"{line_hint} 产包前必填列不能为空: {', '.join(ext_missing)}"
            )


def load_task_csv_raw(path: Path) -> tuple[TaskCsvMeta, list[dict[str, str]], list[str]]:
    text = path.read_text(encoding="utf-8-sig")
    meta = parse_task_csv_meta(text)
    data_lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    if not data_lines:
        raise ValueError(f"task.csv 无数据: {path}")
    reader = csv.DictReader(data_lines)
    fieldnames = list(reader.fieldnames or [])
    _validate_headers(fieldnames)
    rows = [{k: (v or "") for k, v in raw.items()} for raw in reader]
    return meta, rows, fieldnames


def write_task_csv_rows(
    path: Path,
    meta: TaskCsvMeta,
    rows: list[dict[str, str]],
    fieldnames: list[str] | None = None,
) -> None:
    cols = fieldnames or list(STANDARD_COLUMNS)
    prefix = "\n".join(meta.comment_lines) if meta.comment_lines else f"# batchId: {meta.batch_id or 'unknown'}"
    sio = io.StringIO()
    writer = csv.DictWriter(sio, fieldnames=cols, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in cols})
    path.write_text(prefix + "\n" + sio.getvalue(), encoding="utf-8")


def load_csv_tasks(
    path: Path,
    *,
    strict_extended: bool = False,
    allow_pending_manual_fields: bool = False,
    project_dir: Path | None = None,
) -> list[CsvTaskRow]:
    if not path.is_file():
        raise FileNotFoundError(f"任务 CSV 不存在: {path}")

    _, raw_rows, _ = load_task_csv_raw(path)
    rows: list[CsvTaskRow] = []
    for line_no, raw in enumerate(raw_rows, start=2):
        name = _cell(raw, COL_NAME)
        if not name:
            continue
        row = _row_from_raw(raw, name)
        _validate_row_fields(
            row,
            line_hint=f"第 {line_no} 行「{name}」",
            strict_extended=strict_extended,
            allow_pending_manual_fields=allow_pending_manual_fields,
            project_dir=project_dir,
        )
        rows.append(
            CsvTaskRow(
                name=row.name,
                full_name=row.full_name,
                state_management=normalize_state_management(row.state_management),
                architecture_pattern=normalize_architecture_pattern(
                    row.architecture_pattern
                ),
                naming_obfuscation_rule=row.naming_obfuscation_rule,
                privacy_style=row.privacy_style,
                privacy_file=row.privacy_file,
                git_url=row.git_url,
                first_product_code=row.first_product_code,
                programming_style=row.programming_style,
                pack_type=row.pack_type,
                theme_code=row.theme_code,
                theme_cn=row.theme_cn,
                track=row.track,
                audience=row.audience,
                core_scene=row.core_scene,
                local_feature=row.local_feature,
                product_flow=row.product_flow,
                webview_engine=row.webview_engine,
                bridge_call_style=row.bridge_call_style,
                bridge_callback_style=row.bridge_callback_style,
                bridge_envelope=row.bridge_envelope,
                media_serve=row.media_serve,
                bridge_error_code=row.bridge_error_code,
                bridge_inject_timing=row.bridge_inject_timing,
                kit_atom_set=row.kit_atom_set,
                kit_css_methodology=row.kit_css_methodology,
                kit_atom_granularity=row.kit_atom_granularity,
                kit_dom_shape=row.kit_dom_shape,
                kit_js_pattern=row.kit_js_pattern,
                kit_js_namespace=row.kit_js_namespace,
                kit_storage_adapter=row.kit_storage_adapter,
                kit_motion_approach=row.kit_motion_approach,
                h5_state_model=row.h5_state_model,
                h5_router_pattern=row.h5_router_pattern,
                h5_screen_pattern=row.h5_screen_pattern,
            )
        )

    if not rows:
        raise ValueError(f"CSV 无有效数据行: {path}")
    return rows


def load_task_csv_meta(path: Path) -> TaskCsvMeta:
    return parse_task_csv_meta(path.read_text(encoding="utf-8-sig"))


def validate_task_csv(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"task.csv 不存在: {path}")
    load_csv_tasks(resolved)
    return resolved


def validate_task_inputs(csv_path: Path) -> Path:
    return validate_task_csv(csv_path)


def _assert_unique_names(names: list[str], *, label: str) -> None:
    seen: set[str] = set()
    dupes: list[str] = []
    for name in names:
        if name in seen and name not in dupes:
            dupes.append(name)
        seen.add(name)
    if dupes:
        raise ValueError(f"{label}中应用主名称重复: {', '.join(dupes)}")


def _validate_repo_urls(rows: list[CsvTaskRow]) -> None:
    missing = [r.name for r in rows if not r.git_url]
    if missing:
        raise ValueError("CSV 仓库地址不能为空，缺失: " + ", ".join(missing[:8]))
    bad = [r.name for r in rows if not repo_dir_name_from_git_url(r.git_url)]
    if bad:
        raise ValueError("CSV 仓库地址无法解析，应用: " + ", ".join(bad[:8]))


def tasks_from_csv_rows(csv_rows: list[CsvTaskRow], default_type: str) -> list[QueueTask]:
    return [
        QueueTask(
            normalize_pack_type(row.pack_type, default_type),
            row.name,
            theme_task_description(row, fallback=row.full_name or row.name),
        )
        for row in csv_rows
    ]


def merge_csv_with_queue(
    csv_rows: list[CsvTaskRow],
    queue_path: Path | None,
    default_type: str,
    *,
    strict: bool = False,
) -> tuple[list[QueueTask], list[str]]:
    if queue_path is None or not queue_path.is_file():
        return tasks_from_csv_rows(csv_rows, default_type), []

    queue_tasks = load_queue(queue_path, default_type)
    queue_by_name = {t.name: t for t in queue_tasks}
    warnings: list[str] = []
    tasks: list[QueueTask] = []
    for row in csv_rows:
        if row.name in queue_by_name:
            qt = queue_by_name[row.name]
            pack = normalize_pack_type(row.pack_type or qt.pack_type, default_type)
            desc = theme_task_description(row, fallback=qt.desc)
            tasks.append(QueueTask(pack, row.name, desc))
        else:
            tasks.append(
                QueueTask(
                    normalize_pack_type(row.pack_type, default_type),
                    row.name,
                    theme_task_description(row, fallback=row.full_name or row.name),
                )
            )
            if strict:
                raise ValueError(f"CSV「{row.name}」在队列中无匹配")
            warnings.append(f"CSV「{row.name}」无队列行，使用 CSV 字段")
    return tasks, warnings


def load_tasks_for_run(
    csv_path: Path,
    default_type: str,
    *,
    project_dir: Path | None = None,
) -> tuple[list[QueueTask], list[CsvTaskRow]]:
    """Load task.csv for ``./run.sh`` — parse only, no audits (trust ``task ready``)."""
    from batch.config import _project_root

    root = project_dir or _project_root()
    csv_rows = load_csv_tasks(csv_path, project_dir=root)
    tasks = tasks_from_csv_rows(csv_rows, default_type)
    return tasks, csv_rows


def load_tasks_from_task_csv(
    csv_path: Path,
    default_type: str,
    *,
    strict: bool = False,
    strict_extended: bool = False,
    project_dir: Path | None = None,
) -> tuple[list[QueueTask], list[CsvTaskRow], list[str]]:
    from batch.config import _project_root

    root = project_dir or _project_root()
    csv_rows = load_csv_tasks(
        csv_path, strict_extended=strict_extended, project_dir=root
    )
    _assert_unique_names([r.name for r in csv_rows], label="CSV")
    _validate_repo_urls(csv_rows)
    tasks, warnings = merge_csv_with_queue(csv_rows, None, default_type, strict=strict)
    try:
        registry = load_prod_a_registry(root)
    except (OSError, ValueError, RuntimeError) as exc:
        warnings.append(f"警告: 产A 总库在线拉取失败 ({exc})，跳过全局查重")
    else:
        warnings.extend(validate_batch_against_registry(csv_rows, registry))
    return tasks, csv_rows, warnings


def load_tasks_from_csv_and_queue(
    csv_path: Path,
    queue_path: Path,
    default_type: str,
    *,
    strict: bool = False,
    project_dir: Path | None = None,
) -> tuple[list[QueueTask], list[CsvTaskRow], list[str]]:
    from batch.config import _project_root

    root = project_dir or _project_root()
    csv_rows = load_csv_tasks(csv_path, project_dir=root)
    _assert_unique_names([r.name for r in csv_rows], label="CSV")
    _validate_repo_urls(csv_rows)
    tasks, warnings = merge_csv_with_queue(
        csv_rows, queue_path, default_type, strict=strict
    )
    try:
        registry = load_prod_a_registry(root)
    except (OSError, ValueError, RuntimeError) as exc:
        warnings.append(f"警告: 产A 总库在线拉取失败 ({exc})，跳过全局查重")
    else:
        warnings.extend(validate_batch_against_registry(csv_rows, registry))
    return tasks, csv_rows, warnings


def init_empty_task_csv(path: Path, *, batch_id: str, row_count: int) -> None:
    header = format_task_csv_header(batch_id=batch_id)
    meta = parse_task_csv_meta(header)
    rows = [{c: "" for c in STANDARD_COLUMNS} for _ in range(max(0, row_count))]
    write_task_csv_rows(path, meta, rows)


def fill_product_flow_to_csv(csv_path: Path) -> list[str]:
    """Fill empty productFlow cells from theme fields."""
    from batch.theme_fields import generate_product_flow

    meta, rows_raw, fieldnames = load_task_csv_raw(csv_path)
    filled: list[str] = []
    for raw in rows_raw:
        name = (raw.get(COL_NAME) or "").strip()
        if not name:
            continue
        if (raw.get(COL_PRODUCT_FLOW) or "").strip():
            continue
        audience = (raw.get(COL_AUDIENCE) or "").strip()
        scene = (raw.get(COL_CORE_SCENE) or "").strip()
        feature = (raw.get(COL_LOCAL_FEATURE) or "").strip()
        if not (audience or scene or feature):
            continue
        row = _row_from_raw(raw, name)
        raw[COL_PRODUCT_FLOW] = generate_product_flow(row)
        filled.append(name)
    if filled:
        write_task_csv_rows(csv_path, meta, rows_raw, fieldnames=fieldnames)
    return filled
