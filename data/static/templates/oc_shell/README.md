# OC H5 Shell 目录结构模板

标准 Objective-C H5 壳目录结构，与 `swift_shell/standard/` 在职责划分上一致，但使用 OC 文件组织。

## 适用条件

- `task.csv` 中 **pack_type** = `h5_oc_shell`
- `task.csv` 中 **webviewEngine** = `wkwebview_oc`

## 目录结构

```
{app_name}/
└── ios/
    └── {app_name}/
        ├── AppDelegate.h
        ├── AppDelegate.m
        ├── {app_name}.html
        ├── Info.plist
        ├── Assets.xcassets/
        ├── Bridge/                              # 集中式桥接层
        │   ├── WebBridgeHandler.h
        │   ├── WebBridgeHandler.m
        │   ├── {app_name}WebViewDeflavor.h
        │   ├── {app_name}WebViewDeflavor.m
        │   ├── {app_name}ShellConfig.h
        │   ├── {app_name}ShellConfig.m
        │   └── PermissionManager.h/m
        └── Modules/                             # 按职责分模块
            ├── WebContent/
            │   ├── WebContentResolver.h
            │   └── WebContentResolver.m
            ├── WebShell/
            │   ├── WebShellViewModel.h
            │   └── WebShellViewModel.m
            └── WebView/
                ├── WebViewController.h
                └── WebViewController.m
```

## 命名约定

- 目录：语义化小写，如 `Bridge/`、`Modules/WebContent/`
- OC 文件：每个类一对 `.h` / `.m`
- 类名：大驼峰，直接表达职责，如 `WebBridgeHandler`
