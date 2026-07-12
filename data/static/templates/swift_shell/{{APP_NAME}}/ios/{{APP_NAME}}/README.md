# 基础夹板 — iOS 原生侧

本目录是 `h5_swift_shell` 的**可构建**基础夹板，包含完整 Swift 源文件与占位资源。场包时 `apply.py` 会替换所有占位符并生成可直接进入 Xcode 的工程结构。

## 本目录已包含（直接可用）

- `Assets.xcassets/` — App 图标、启动背景、占位图
- `Info.plist` — Bundle 配置与权限描述模板
- `{{APP_NAME}}.html` — H5 入口占位（含锁定 Bridge 的 JS bootstrap）
- `{{APP_NAME}}App.swift` — App 入口
- `Bridge/` — WebView、Bridge Handler、Permission、IAP、录音、相册等集中式实现
- `{{PREFIX}}_*_*/{{PREFIX}}_*_*_leaf/` — 业务模块（WebContent / WebShell / WebView）

## 占位符

| 占位符 | 说明 |
|--------|------|
| `{{APP_NAME}}` | App 显示名（PascalCase） |
| `{{APP_NAME_LOWER}}` | App 小写标识（用于 JS bridge 对象） |
| `{{PREFIX}}` | 命名混淆前缀 |
| `{{APP_SLUG}}` | URL slug |
| `{{H5_HOST}}` | H5 生产域名 |
| `{{BUNDLE_ID}}` | iOS Bundle ID |
| `{{TEAM_ID}}` | Apple Team ID |
| `{{ASSET_SCHEME}}` | 本地资源自定义 scheme |

## 编程风格

当前基础夹板采用**标准英文命名**结构。如需德国 persona 的 `nested_role_leaf` 分散布局，可在 `apply.py` 中扩展 `--style german_persona`（默认 `standard`）。
