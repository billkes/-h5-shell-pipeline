# standard Swift H5 Shell 风格示例

对应 `Prepoo-Swift` 风格：标准英文命名、集中式 `Bridge/`。

## 适用条件

- `task.csv` 中 **命名混淆规则** = 无 / 标准策略
- `task.csv` 中 **编程风格** = 美国人 / 英国人 / 中国人
- 偏好语义化、可直接阅读的 Swift 类名

## 目录结构

```
{app_name}/
└── ios/
    └── {app_name}/
        ├── {app_name}App.swift
        ├── {app_name}.html
        ├── Info.plist
        ├── Assets.xcassets/
        ├── Bridge/                              # 集中式桥接层
        │   ├── WebBridgeHandler.swift
        │   ├── {app_name}WebViewDeflavor.swift
        │   ├── {app_name}ShellConfig.swift
        │   ├── {app_name}SeedAssets.swift
        │   ├── {app_name}FileVault.swift
        │   ├── {app_name}AssetScheme.swift
        │   └── PermissionManager.swift
        └── Modules/                             # 按职责分模块
            ├── WebContent/
            │   └── WebContentResolver.swift
            ├── WebShell/
            │   └── WebShellViewModel.swift
            └── WebView/
                └── WebViewController.swift
```

## 命名约定

- 目录：语义化小写，如 `Bridge/`、`Modules/WebContent/`
- Swift 文件：大驼峰，直接表达职责，如 `WebBridgeHandler.swift`
- 类名：与文件名一致

## 参考实现

本目录下的 `ios/{{APP_NAME}}/` 是从真实 `Prepoo-Swift` 工程抽象出的**完整参考实现**，包含 Bridge、ViewModel、WebViewController 等。场包时 Programmer Agent 应根据 task.csv 风格选择是否采用此结构，但不应将其直接作为基础夹板拷贝。
