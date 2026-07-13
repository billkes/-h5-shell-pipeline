"""Scaffold a reference demo_mock bundle inside a generated Flutter tool-pack project.

The generated files are intentionally a starting template: each project has
different JSON vault / media field names, so the developer must customize
manifest.json and the json/*.json files before running generate_media.py / import_demo.py.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

USER_MEDIA_MARKERS = (
    "user_media",
    "ImagePicker",
    "pickImage",
    "documentPaths",
    "PhotoPath",
    "resolveMedia",
    "resolveFeMedia",
    "resolveFile",
)

REQUIRED_SCRIPTS = (
    "audit_demo_mock.py",
    "generate_media.py",
    "import_demo.py",
)


def _flutter_project_uses_user_media(project_dir: Path) -> bool:
    lib_dir = project_dir / "lib"
    if not lib_dir.is_dir():
        return False
    for dart_file in lib_dir.rglob("*.dart"):
        try:
            text = dart_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lowered = text.lower()
        if any(marker.lower() in lowered for marker in USER_MEDIA_MARKERS):
            return True
    return False


def _read_bundle_id(project_dir: Path) -> str | None:
    pbxproj_paths = list((project_dir / "ios" / "Runner.xcodeproj").rglob("project.pbxproj"))
    if not pbxproj_paths:
        return None
    try:
        text = pbxproj_paths[0].read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    match = re.search(r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*"([^"]+)"', text)
    if match:
        return match.group(1)
    match = re.search(r"PRODUCT_BUNDLE_IDENTIFIER\s*=\s*'([^']+)'", text)
    if match:
        return match.group(1)
    match = re.search(
        r"PRODUCT_BUNDLE_IDENTIFIER\s*=\s*([a-zA-Z0-9._-]+)\s*;",
        text,
    )
    if match and "RunnerTests" not in match.group(1):
        return match.group(1)
    return None


def _copy_demo_mock_scripts(dest_root: Path, scripts_src: Path) -> None:
    for script_name in REQUIRED_SCRIPTS:
        src = scripts_src / script_name
        dest = dest_root / script_name
        if src.is_file():
            shutil.copy2(src, dest)
        else:
            dest.write_text(f"# Placeholder: {script_name} not found in {scripts_src}\n", encoding="utf-8")


def _write_manifest(dest_root: Path, app_name: str, bundle_id: str | None) -> None:
    safe_bundle = bundle_id or f"com.example.{re.sub(r'[^a-zA-Z0-9.]+', '-', app_name).strip('-').lower()}"
    manifest = {
        "_comment": "这是 demo_mock 模板。请根据本项目 Entity / JsonStore 实际字段名修改 sharedPreferences、json/*.json、copy 与 placeholders。",
        "appName": app_name,
        "bundleId": safe_bundle,
        "preferencesKeyPrefix": "flutter.",
        "sharedPreferences": {
            "welcomeAccepted": True,
            "free_remaining_v1": 2,
            "coin_balance": 25,
        },
        "copy": [],
        "removeOnClear": ["user_media"],
        "clearPreferences": [
            "welcomeAccepted",
            "free_remaining_v1",
            "coin_balance",
        ],
        "placeholders": []
    }
    (dest_root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_json_readme(dest_root: Path) -> None:
    text = """# json/ — vault 演示数据

- 字段名必须与 `lib/` 里对应 Entity 的 `fromJson` 一致。
- **列表类 vault 须 3–5 条**（Silk Folio / Gather Ledger / 日志流等截图页）。
- manifest 中引用：`"your_vault_key_v1": "{{FILE:json/your_vault.json}}"`
- JSON 内可用日期占位：`{{TODAY}}` / `{{YESTERDAY}}` / `{{DAYS_AGO:N}}`（import 时替换）
"""
    (dest_root / "json" / "README.md").write_text(text, encoding="utf-8")


def _write_readme(dest_root: Path) -> None:
    readme = """# demo_mock 演示数据包

此目录为脚手架模板，**必须根据本项目实际数据结构修改**后方可使用。

## 文件说明

- `manifest.json` — bundleId、SharedPreferences、`{{FILE:}}` 引用、copy 清单、placeholders。
- `json/*.json` — vault JSON；**列表 3–5 条**；字段对齐 Entity `fromJson`。
- `media/user_media/photos/` — ERROR BUILD 水印占位图（勿从 `assets/` 拷真图）。
- `generate_media.py` / `import_demo.py` / `audit_demo_mock.py` — 生成、导入、校验。

## 快速使用

```bash
cd <本项目>

# 1. 按 Entity 填写 json/*.json 与 manifest.json（含 preferencesKeyPrefix: "flutter."）
# 2. 生成占位图
python3 demo_mock/generate_media.py

# 3. 导入（脚本会自动 terminate App + flush cfprefsd）
python3 demo_mock/import_demo.py list
python3 demo_mock/import_demo.py clear --udid <UDID>   # 可选：截前先清
python3 demo_mock/import_demo.py import --udid <UDID>

# 4. 从 Simulator 主屏幕点 App 图标冷启动（勿 Hot Restart / 勿再 flutter run）
```

## import 后仍空态？

| 现象 | 处理 |
|------|------|
| prefs 写成功但 App 仍欢迎页/空列表 | 确认 `preferencesKeyPrefix: "flutter."`；用 canonical `import_demo.py` |
| import 后有 vault 键、冷启动后只剩 welcomeAccepted | App 前台 import 或 `flutter run` 附着 → 内存 prefs 回写；须 **terminate + cfprefsd + 图标冷启动** |
| 列表只有 1–2 条 | json 补到 **3–5 条** |

排查 plist：

```bash
plutil -p "$(xcrun simctl get_app_container <UDID> <bundleId> data)/Library/Preferences/<bundleId>.plist" | rg 'flutter\\.'
```

## 截图金额惯例（非 IAP catalog）

| pref key | 建议值 |
|----------|--------|
| `coin_balance` | 25 |
| `free_remaining_v1` | 2（免费档总数 3 时展示已用 1 次） |

## 校验

```bash
python3 demo_mock/audit_demo_mock.py .
```
"""
    (dest_root / "README.md").write_text(readme, encoding="utf-8")


def scaffold_demo_mock(
    project_dir: Path,
    scripts_src: Path,
    app_name: str,
    *,
    required: bool = False,
) -> str:
    """Create a reference demo_mock bundle. Returns a short status message."""
    if not required and not _flutter_project_uses_user_media(project_dir):
        return "N/A（未发现 user_media / ImagePicker 等媒体能力）"

    demo_root = project_dir / "demo_mock"
    demo_root.mkdir(parents=True, exist_ok=True)
    (demo_root / "json").mkdir(exist_ok=True)
    (demo_root / "media" / "user_media" / "photos").mkdir(parents=True, exist_ok=True)

    _copy_demo_mock_scripts(demo_root, scripts_src)
    bundle_id = _read_bundle_id(project_dir)
    _write_manifest(demo_root, app_name, bundle_id)
    _write_json_readme(demo_root)
    _write_readme(demo_root)

    return f"已创建 {demo_root.relative_to(project_dir)}（bundleId={bundle_id or '未识别'}）"


def scaffold_demo_mock_for_output(
    output_base: Path,
    scripts_src: Path,
    *,
    required: bool = False,
) -> list[str]:
    """Scan output for Flutter projects and scaffold demo_mock for each tool-pack."""
    results: list[str] = []
    if not output_base.is_dir():
        return results

    for pubspec in output_base.rglob("pubspec.yaml"):
        project_dir = pubspec.parent
        app_name = project_dir.name
        status = scaffold_demo_mock(
            project_dir, scripts_src, app_name, required=required
        )
        results.append(f"{app_name}: {status}")
    return results


def demo_mock_scaffold_complete(project_dir: Path) -> bool:
    """Return True when the mandatory demo_mock bundle files exist."""
    demo_root = project_dir / "demo_mock"
    return (
        (demo_root / "manifest.json").is_file()
        and (demo_root / "import_demo.py").is_file()
        and (demo_root / "generate_media.py").is_file()
    )
