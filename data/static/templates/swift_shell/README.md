# H5 Swift Shell 厂包夹板

> 本目录是 `h5_swift_shell` 技术站的锁定模板。**基础夹板只提供不受编程风格与命名规则影响的稳定资产**；Swift 源文件由场包 Programmer Agent 根据 `task.csv` 风格与命名规则生成后覆盖到本模板。

## 锁定技术站

| 维度 | 锁定值 |
|------|--------|
| `webviewEngine` | `wkwebview_swift` |
| `bridgeCallStyle` | `WKScriptMessageHandler.postMessage(JSON)` |
| `bridgeCallbackStyle` | `evaluateJavaScript(callbackId(data))` |
| `bridgeEnvelope` | `{action,data} minimal` |
| `mediaServe` | `WKURLSchemeHandler local vault` |
| `bridgeErrorCode` | `string enum (PERMISSION_DENIED)` |
| `bridgeInjectTiming` | `WKUserScript atDocumentStart` |

## 目录结构

```
swift_shell/
├── template.json              # 模板元数据
├── apply.py                   # 占位符替换脚本
├── README.md                  # 本文件
├── examples/                  # 风格示例（非基础模板）
│   ├── standard/              # Prepoo 风格参考实现
│   └── german_persona/        # Mockoo 风格文档
└── {{APP_NAME}}/              # 场包时拷贝并重命名该目录
    ├── 本包登记信息.json        # 登记信息占位
    ├── ios/
    │   └── {{APP_NAME}}/
    │       ├── {{APP_NAME}}.html          # H5 入口占位（含锁定 Bridge JS）
    │       ├── Info.plist                 # Bundle 与权限配置模板
    │       ├── Assets.xcassets/           # 图标、启动背景、占位图
    │       └── README.md                  # 说明：Swift 文件由场包生成
    └── h5/
        └── README.md          # H5 业务包接入说明
```

## 占位符清单

| 占位符 | 含义 | 示例 |
|--------|------|------|
| `{{APP_NAME}}` | App 显示名（PascalCase） | `Prepoo` |
| `{{APP_NAME_LOWER}}` | App 小写标识 | `prepoo` |
| `{{PREFIX}}` | 壳代码混淆前缀 | `erbpv` |
| `{{APP_SLUG}}` | H5 远程路径 slug | `prepoo` |
| `{{H5_HOST}}` | H5 生产域名 | `test.darin.beauty` |
| `{{BUNDLE_ID}}` | iOS Bundle Identifier | `com.example.prepoo` |
| `{{TEAM_ID}}` | Apple Development Team ID | `XXXXXXXXXX` |
| `{{ASSET_SCHEME}}` | 本地资源自定义 Scheme | `prepoo-asset` |

## 场包流程

1. 流水线脚本将 `swift_shell/{{APP_NAME}}` 复制到目标业务包目录。
2. 调用 `apply.py` 或等效替换逻辑填充占位符（仅影响稳定资产中的占位文本）。
3. Programmer Agent 根据 `task.csv` 的 **编程风格** 与 **命名规则** 生成本包 Swift 源文件（App.swift、Bridge/ViewModel/Controller 等），覆盖到 `ios/{{APP_NAME}}/` 下。
4. 将业务包已有的 `h5/` 构建产物覆盖到模板中的 `h5/` 目录，最终由壳加载远程或本地 H5 入口。

## 约束

- 禁止在 Swift 侧实现可见业务 UI（Welcome、TabBar、Shop 等），所有可见界面由 H5 承担。
- 禁止出现 `index.html`、`assets/h5/` 等含 `h5`/`web`/`bridge`/`webview` 的公共符号。
- LaunchScreen 必须为纯色，颜色与 H5 首帧背景一致。
- 协议与 Legal 内容优先使用 H5 vault 内置文本，禁止外链作为主路径。
- `shellReady` 为固定能力，H5 首帧绘制后上报，原生撤 LaunchVeil。

## 风格示例

- `examples/standard/` — 标准英文命名、集中式 `Bridge/`（对应 `Prepoo-Swift`）
- `examples/german_persona/` — 德国 persona 混淆前缀、`nested_role_leaf` 分散模块（对应 `Mockoo-Swift`）

## 导航

- 上级：[[data/static/templates/]]
