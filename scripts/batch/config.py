"""Load project paths and environment / YAML configuration."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from batch.queue import VALID_TYPES


def _scripts_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


# ═══════════════════════════════════════════════════════════════════════
# 配置加载优先级：
#   命令行参数 > 环境变量 > config.yaml > config.env > 脚本内置默认值
# ═══════════════════════════════════════════════════════════════════════

# config.yaml 键路径 → 环境变量名映射
# 同步修改时请同时更新 config/config.yaml.example
_YAML_ENV_MAP: dict[tuple[str, ...], str] = {
    ("cursor", "cli"): "CURSOR_CLI",
    ("cursor", "status_timeout"): "CURSOR_STATUS_TIMEOUT",
    ("cursor", "agent_max_retries"): "CURSOR_AGENT_MAX_RETRIES",
    ("cursor", "agent_retry_delay_sec"): "CURSOR_AGENT_RETRY_DELAY_SEC",
    ("cursor", "agent_heartbeat_sec"): "CURSOR_AGENT_HEARTBEAT_SEC",
    ("cursor", "agent_stream"): "CURSOR_AGENT_STREAM",
    ("cursor", "agent_output_format"): "CURSOR_AGENT_OUTPUT_FORMAT",
    ("cursor", "agent_stream_partial"): "CURSOR_AGENT_STREAM_PARTIAL",
    ("cursor", "agent_sandbox"): "CURSOR_AGENT_SANDBOX",
    ("cursor", "agent_phase_timeout_sec"): "CURSOR_AGENT_PHASE_TIMEOUT_SEC",
    ("cursor", "agent_idle_timeout_sec"): "CURSOR_AGENT_IDLE_TIMEOUT_SEC",
    ("agent", "provider"): "AGENT_PROVIDER",
    ("iflow", "url"): "IFLOW_URL",
    ("iflow", "auto_start_process"): "IFLOW_AUTO_START_PROCESS",
    ("iflow", "timeout_sec"): "IFLOW_TIMEOUT_SEC",
    ("iflow", "log_level"): "IFLOW_LOG_LEVEL",
    ("iflow", "approval_mode"): "IFLOW_APPROVAL_MODE",
    ("iflow", "file_access"): "IFLOW_FILE_ACCESS",
    ("iflow", "file_read_only"): "IFLOW_FILE_READ_ONLY",
    ("iflow", "file_max_size"): "IFLOW_FILE_MAX_SIZE",
    ("iflow", "file_allowed_dirs"): "IFLOW_FILE_ALLOWED_DIRS",
    ("iflow", "auth_method_id"): "IFLOW_AUTH_METHOD_ID",
    ("iflow", "auth_method_info"): "IFLOW_AUTH_METHOD_INFO",
    ("iflow", "heartbeat_sec"): "IFLOW_HEARTBEAT_SEC",
    ("iflow", "phase_timeout_sec"): "IFLOW_PHASE_TIMEOUT_SEC",
    ("iflow", "idle_timeout_sec"): "IFLOW_IDLE_TIMEOUT_SEC",
    ("iflow", "max_retries"): "IFLOW_MAX_RETRIES",
    ("iflow", "retry_delay_sec"): "IFLOW_RETRY_DELAY_SEC",
    ("xcode", "bundle_id"): "XCODE_BUNDLE_ID",
    ("xcode", "iap_bundle_prefix"): "IAP_BUNDLE_PREFIX",
    ("build", "pub_get_max_retries"): "PUB_GET_MAX_RETRIES",
    ("build", "max_build_fix_rounds"): "MAX_BUILD_FIX_ROUNDS",
    ("build", "max_test_fix_rounds"): "MAX_TEST_FIX_ROUNDS",
    ("build", "max_analyze_fix_rounds"): "MAX_ANALYZE_FIX_ROUNDS",
    ("runtime", "legacy_pipeline"): "LEGACY_PIPELINE",
    ("build", "flutter_test_timeout_sec"): "FLUTTER_TEST_TIMEOUT_SEC",
    ("build", "flutter_test_per_test_timeout"): "FLUTTER_TEST_PER_TEST_TIMEOUT",
    ("build", "flutter_test_concurrency"): "FLUTTER_TEST_CONCURRENCY",
    ("build", "flutter_test_paths"): "FLUTTER_TEST_PATHS",
    ("build", "build_log_tail_lines"): "BUILD_LOG_TAIL_LINES",
    ("defaults", "pack_type"): "BATCH_PACK_TYPE",
    ("defaults", "task_csv"): "BATCH_TASK_CSV",
    ("defaults", "free_tier"): "FREE_TIER_DEFAULT",
    ("defaults", "free_publish"): "FREE_PUBLISH_DEFAULT",
    ("defaults", "tool_lang"): "TOOL_LANG",
    ("runtime", "phase1_cache"): "PHASE1_CACHE",
    ("runtime", "skip_images"): "SKIP_IMAGES",
    ("screenshots", "enable"): "ENABLE_SCREENSHOT",
    ("screenshots", "device"): "SIMULATOR_DEVICE",
    ("screenshots", "enable_ui_review"): "ENABLE_UI_REVIEW",
    ("api_keys", "unsplash_access_key"): "UNSPLASH_ACCESS_KEY",
    ("api_keys", "pexels_api_key"): "PEXELS_API_KEY",
    ("api_keys", "tinypng_api_key"): "TINYPNG_API_KEY",
    ("api_keys", "logo_api"): "LOGO_API",
    ("api_keys", "openai_api_key"): "OPENAI_API_KEY",
    ("api_keys", "dashscope_api_key"): "DASHSCOPE_API_KEY",
    ("git", "remote_pattern"): "GIT_REMOTE_PATTERN",
    ("git", "default_branch"): "GIT_DEFAULT_BRANCH",
    ("evolution", "cooldown_days"): "COOLDOWN_DAYS",
    ("uupm", "skill_dir"): "UUPM_SKILL_DIR",
}


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def _optional_path(value: str) -> Path | None:
    """Return a Path for non-empty, non-whitespace strings; otherwise None."""
    value = value.strip()
    return Path(value) if value else None


def _parse_comma_list(value: str) -> list[str]:
    """Parse a comma-separated string into a list of stripped non-empty values."""
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_json_dict(value: str) -> dict[str, object]:
    """Parse a JSON string into a dict; return empty dict on empty/invalid input."""
    value = value.strip()
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _to_env_str(value: object) -> str:
    """将 YAML 值转换为环境变量字符串。"""
    if isinstance(value, bool):
        return "1" if value else "0"
    if value is None:
        return ""
    return str(value)


def _load_yaml_config(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"读取 config.yaml 失败: {exc}") from exc
    return data if isinstance(data, dict) else {}


def _apply_yaml_to_environ(data: dict[str, object]) -> None:
    """把 YAML 配置写入环境变量（仅当环境变量尚未设置时）。"""
    for path_keys, env_name in _YAML_ENV_MAP.items():
        if env_name in os.environ:
            continue
        node = data
        for key in path_keys:
            if not isinstance(node, dict) or key not in node:
                break
            node = node[key]
        else:
            os.environ[env_name] = _to_env_str(node)


@dataclass
class BatchConfig:
    """Runtime configuration for batch scripts."""

    project_dir: Path = field(default_factory=_project_root)
    cursor_cli: str = ""
    cursor_status_timeout: int = 15
    cursor_agent_max_retries: int = 1
    cursor_agent_retry_delay_sec: int = 20
    cursor_agent_heartbeat_sec: int = 60
    cursor_agent_stream: bool = True
    cursor_agent_output_format: str = "stream-json"
    cursor_agent_stream_partial: bool = True
    cursor_agent_sandbox: bool = True
    cursor_agent_phase_timeout_sec: int = 1800
    cursor_agent_idle_timeout_sec: int = 300
    agent_provider: str = "cursor"
    iflow_url: str = "ws://localhost:8090/acp"
    iflow_auto_start_process: bool = True
    iflow_timeout_sec: float = 300.0
    iflow_log_level: str = "INFO"
    iflow_approval_mode: str = "YOLO"
    iflow_file_access: bool = True
    iflow_file_allowed_dirs: list[str] = field(default_factory=list)
    iflow_file_read_only: bool = False
    iflow_file_max_size: int = 10 * 1024 * 1024
    iflow_auth_method_id: str = ""
    iflow_auth_method_info: dict[str, object] = field(default_factory=dict)
    iflow_heartbeat_sec: int = 60
    iflow_phase_timeout_sec: int = 1800
    iflow_idle_timeout_sec: int = 300
    iflow_max_retries: int = 1
    iflow_retry_delay_sec: int = 20
    pub_get_max_retries: int = 3
    max_build_fix_rounds: int = 2
    max_test_fix_rounds: int = 3
    max_analyze_fix_rounds: int = 1
    legacy_pipeline: bool = False
    pipeline_step_ids: list[str] | None = None
    pipeline_step_continue: bool = False
    pipeline_step_rerun: bool = False
    flutter_test_timeout_sec: int = 600
    flutter_test_per_test_timeout: str = "30s"
    flutter_test_concurrency: int = 4
    flutter_test_paths: str = "test/flows"
    phase1_cache: bool = True
    skip_images: bool = False
    no_render_images: bool = False
    force_rerun: bool = False
    dry_run: bool = False
    batch_pack_type: str = "h5_shell"
    task_csv_path: Path | None = None
    batch_id: str = ""
    task_csv_by_name: dict[str, object] = field(default_factory=dict)
    unsplash_access_key: str = ""
    pexels_api_key: str = ""
    free_tier_default: int = 3
    free_publish_default: int = 2
    uupm_skill_dir: str = ""
    uupm_integrations: dict[str, object] = field(default_factory=dict)
    design_gemini_api_key: str = ""
    xcode_bundle_id: str = "test.duckegg.ios"
    xcode_development_team: str = ""
    xcode_provisioning_profile: str = "duckeggkaifaProfile"
    iap_bundle_prefix: str = ""

    @property
    def config_dir(self) -> Path:
        return self.project_dir / "config"

    @property
    def data_dir(self) -> Path:
        return self.project_dir / "data"

    @property
    def static_dir(self) -> Path:
        return self.data_dir / "static"

    @property
    def registry_dir(self) -> Path:
        return self.data_dir / "registry"

    @property
    def decks_dir(self) -> Path:
        return self.data_dir / "decks"

    @property
    def imports_dir(self) -> Path:
        return self.data_dir / "imports"

    @property
    def docs_dir(self) -> Path:
        return self.project_dir / "docs"

    @property
    def task_csv(self) -> Path:
        return self.task_csv_path or (self.project_dir / "task.csv")

    @property
    def output_dir(self) -> Path:
        return self.project_dir / "output"

    @property
    def reports_dir(self) -> Path:
        return self.output_dir / "_reports"

    @property
    def prompts_dir(self) -> Path:
        return self.project_dir / "prompts" / "h5_shell"

    @property
    def scripts_dir(self) -> Path:
        return self.project_dir / "scripts"

    @property
    def contentpack_registry(self) -> Path:
        return self.registry_dir / "contentpack-registry.json"

    @classmethod
    def from_env(cls, **overrides: object) -> BatchConfig:
        root = _project_root()
        # 1. YAML 优先于 config.env，但环境变量优先于两者
        _apply_yaml_to_environ(_load_yaml_config(root / "config" / "config.yaml"))
        _load_env_file(root / "config" / "config.env")

        pack_type = os.environ.get("BATCH_PACK_TYPE", "h5_shell")
        if pack_type not in VALID_TYPES:
            pack_type = "h5_shell"

        cfg = cls(
            project_dir=root,
            cursor_cli=os.environ.get("CURSOR_CLI", ""),
            cursor_status_timeout=int(
                os.environ.get("CURSOR_STATUS_TIMEOUT", "15")
            ),
            cursor_agent_max_retries=max(
                1,
                int(os.environ.get("CURSOR_AGENT_MAX_RETRIES", "1")),
            ),
            cursor_agent_retry_delay_sec=max(
                0,
                int(os.environ.get("CURSOR_AGENT_RETRY_DELAY_SEC", "20")),
            ),
            cursor_agent_heartbeat_sec=max(
                0,
                int(os.environ.get("CURSOR_AGENT_HEARTBEAT_SEC", "60")),
            ),
            cursor_agent_stream=os.environ.get("CURSOR_AGENT_STREAM", "1") == "1",
            cursor_agent_output_format=os.environ.get(
                "CURSOR_AGENT_OUTPUT_FORMAT", "stream-json"
            ),
            cursor_agent_stream_partial=os.environ.get(
                "CURSOR_AGENT_STREAM_PARTIAL", "1"
            )
            == "1",
            cursor_agent_sandbox=os.environ.get("CURSOR_AGENT_SANDBOX", "1") == "1",
            cursor_agent_phase_timeout_sec=max(
                0,
                int(os.environ.get("CURSOR_AGENT_PHASE_TIMEOUT_SEC", "600")),
            ),
            cursor_agent_idle_timeout_sec=max(
                0,
                int(os.environ.get("CURSOR_AGENT_IDLE_TIMEOUT_SEC", "300")),
            ),
            agent_provider=os.environ.get("AGENT_PROVIDER", "cursor").lower(),
            iflow_url=os.environ.get("IFLOW_URL", "ws://localhost:8090/acp"),
            iflow_auto_start_process=os.environ.get(
                "IFLOW_AUTO_START_PROCESS", "1"
            )
            == "1",
            iflow_timeout_sec=float(os.environ.get("IFLOW_TIMEOUT_SEC", "300")),
            iflow_log_level=os.environ.get("IFLOW_LOG_LEVEL", "INFO"),
            iflow_approval_mode=os.environ.get("IFLOW_APPROVAL_MODE", "YOLO"),
            iflow_file_access=os.environ.get("IFLOW_FILE_ACCESS", "1") == "1",
            iflow_file_read_only=os.environ.get("IFLOW_FILE_READ_ONLY", "0") == "1",
            iflow_file_max_size=max(
                0,
                int(os.environ.get("IFLOW_FILE_MAX_SIZE", str(10 * 1024 * 1024))),
            ),
            iflow_file_allowed_dirs=_parse_comma_list(
                os.environ.get("IFLOW_FILE_ALLOWED_DIRS", "")
            ),
            iflow_auth_method_id=os.environ.get("IFLOW_AUTH_METHOD_ID", ""),
            iflow_auth_method_info=_parse_json_dict(
                os.environ.get("IFLOW_AUTH_METHOD_INFO", "")
            ),
            iflow_heartbeat_sec=max(
                0,
                int(os.environ.get("IFLOW_HEARTBEAT_SEC", "60")),
            ),
            iflow_phase_timeout_sec=max(
                0,
                int(os.environ.get("IFLOW_PHASE_TIMEOUT_SEC", "600")),
            ),
            iflow_idle_timeout_sec=max(
                0,
                int(os.environ.get("IFLOW_IDLE_TIMEOUT_SEC", "300")),
            ),
            iflow_max_retries=max(
                1,
                int(os.environ.get("IFLOW_MAX_RETRIES", "1")),
            ),
            iflow_retry_delay_sec=max(
                0,
                int(os.environ.get("IFLOW_RETRY_DELAY_SEC", "20")),
            ),
            pub_get_max_retries=max(
                1,
                int(os.environ.get("PUB_GET_MAX_RETRIES", "3")),
            ),
            max_build_fix_rounds=max(
                1,
                int(os.environ.get("MAX_BUILD_FIX_ROUNDS", "2")),
            ),
            max_test_fix_rounds=max(
                1,
                int(os.environ.get("MAX_TEST_FIX_ROUNDS", "3")),
            ),
            max_analyze_fix_rounds=max(
                1,
                int(os.environ.get("MAX_ANALYZE_FIX_ROUNDS", "1")),
            ),
            legacy_pipeline=os.environ.get("LEGACY_PIPELINE", "0") == "1",
            flutter_test_timeout_sec=max(
                0,
                int(os.environ.get("FLUTTER_TEST_TIMEOUT_SEC", "600")),
            ),
            flutter_test_per_test_timeout=os.environ.get(
                "FLUTTER_TEST_PER_TEST_TIMEOUT", "30s"
            ),
            flutter_test_concurrency=max(
                1,
                int(os.environ.get("FLUTTER_TEST_CONCURRENCY", "4")),
            ),
            flutter_test_paths=os.environ.get("FLUTTER_TEST_PATHS", "test/flows"),
            phase1_cache=os.environ.get("PHASE1_CACHE", "1") == "1",
            skip_images=os.environ.get("SKIP_IMAGES", "0") == "1",
            batch_pack_type=pack_type,
            task_csv_path=_optional_path(os.environ.get("BATCH_TASK_CSV", "")),
            unsplash_access_key=os.environ.get("UNSPLASH_ACCESS_KEY", ""),
            pexels_api_key=os.environ.get("PEXELS_API_KEY", ""),
            free_tier_default=max(
                1, int(os.environ.get("FREE_TIER_DEFAULT", "3"))
            ),
            free_publish_default=max(
                1, int(os.environ.get("FREE_PUBLISH_DEFAULT", "2"))
            ),
            uupm_skill_dir=os.environ.get("UUPM_SKILL_DIR", ""),
            design_gemini_api_key=os.environ.get("DESIGN_GEMINI_API_KEY", ""),
            xcode_bundle_id=os.environ.get("XCODE_BUNDLE_ID", "test.duckegg.ios"),
            xcode_development_team=os.environ.get(
                "APPLE_TEAM_ID",
                os.environ.get("XCODE_DEVELOPMENT_TEAM", ""),
            ),
            xcode_provisioning_profile=os.environ.get(
                "XCODE_PROVISIONING_PROFILE",
                "duckeggkaifaProfile",
            ),
            iap_bundle_prefix=os.environ.get("IAP_BUNDLE_PREFIX", ""),
        )
        for key, val in overrides.items():
            if hasattr(cfg, key):
                setattr(cfg, key, val)
        yaml_data = _load_yaml_config(cfg.config_dir / "config.yaml")
        uupm = yaml_data.get("uupm") if isinstance(yaml_data, dict) else None
        if isinstance(uupm, dict):
            integrations = uupm.get("integrations")
            if isinstance(integrations, dict):
                cfg.uupm_integrations = integrations
            design = yaml_data.get("design") if isinstance(yaml_data, dict) else None
            if isinstance(design, dict):
                gemini = str(design.get("gemini_api_key") or "").strip()
                if gemini and not cfg.design_gemini_api_key:
                    cfg.design_gemini_api_key = gemini
        xcode = yaml_data.get("xcode") if isinstance(yaml_data, dict) else None
        if isinstance(xcode, dict):
            bundle_id = str(xcode.get("bundle_id") or "").strip()
            if bundle_id and not os.environ.get("XCODE_BUNDLE_ID"):
                cfg.xcode_bundle_id = bundle_id
            team_id = str(xcode.get("team_id") or "").strip()
            if team_id and not cfg.xcode_development_team:
                cfg.xcode_development_team = team_id
            profile = str(xcode.get("provisioning_profile") or "").strip()
            if profile and not os.environ.get("XCODE_PROVISIONING_PROFILE"):
                cfg.xcode_provisioning_profile = profile
        return cfg


def safe_dir_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


def dart_package_name(name: str) -> str:
    s = re.sub(r"[^a-z0-9]", "_", name.lower())
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "myapp"
