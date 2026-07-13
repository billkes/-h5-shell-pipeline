# german_persona Swift H5 Shell 风格示例

对应 `Mockoo-Swift` 风格：德国 persona 下的混淆前缀、`nested_role_leaf` 分散模块。

## 适用条件

- `task.csv` 中 **命名混淆规则** = **辅音核心策略** / **倒序声母策略** / **单声母三随机策略** / **双随机镜像策略**（dynamic key v2 主推四条）
- `task.csv` 中 **编程风格** = 德国人 / 法国人 / 俄罗斯人
- 需要非语义化前缀以隐藏业务意图

## 目录结构

```
{app_name}/
└── ios/
    └── {app_name}/
        ├── {app_name}App.swift
        ├── {app_name}.html
        ├── Info.plist
        ├── Assets.xcassets/
        ├── {prefix}_shell/                          # 壳核心（取代 Bridge/）
        │   └── {Prefix}ShellLedger.swift
        ├── {prefix}_module_a/                       # 业务模块 A
        │   └── {prefix}_module_a_bay/
        │       └── {Prefix}ModuleAPortAnchorPresenter.swift
        ├── {prefix}_module_b/                       # 业务模块 B
        │   └── {prefix}_module_b_bay/
        │       └── {Prefix}ModuleBWebViewDeflavor.swift
        └── {prefix}_module_c/                       # 业务模块 C
            └── {prefix}_module_c_bay/
                └── {Prefix}ModuleCPrismStripAnchorRouter.swift
```

## 命名约定

- 前缀：`{prefix}` 由命名混淆规则生成（`packageSeed` / `dartCodePrefix`），如 `xucfw`、`erbpv`
- 标识符缀 key **按 semantic 动态派生**（前缀/后缀/中缀/镜像），长度在规则 `lengthRange` 内变化
- 模块目录：`{prefix}_{module_name}/`（父目录），`{prefix}_{module_name}_bay/`（叶目录）
  - 对应德国 persona 的 `nested_role_leaf` 布局
- Swift 文件/类名：大驼峰，前缀首字母大写，嵌入角色隐喻词：
  - `PortAnchorPresenter`（入口锚点）
  - `WebViewDeflavor`（去风味 WebView）
  - `PrismStripAnchorRouter`（棱镜条锚点路由）
  - `ShellLedger`（壳账本）

## 说明

本目录仅保存风格文档与空骨架示例，不含完整 Swift 实现。场包时 Programmer Agent 应依据命名规则生成对应目录名与类名。
