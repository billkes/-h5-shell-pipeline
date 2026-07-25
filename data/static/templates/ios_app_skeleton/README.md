# iOS App 官方骨架（ios_app_skeleton）

> 带可检入 `.xcodeproj` 的空 iOS App 工程骨架。供 **Windows 产包机只拷贝 + 占位符替换**，不依赖本机 `xcodegen`。  
> 与壳模板 `swift_shell/` **并列、职责分离**：先骨架，再套壳。

## 采集信息

| 项 | 值 |
|----|-----|
| 采集日期 | 2026-07-25 |
| macOS | 26.4.1 (25E253) |
| Xcode | 26.4.1 (17E202) |
| Interface | SwiftUI |
| 来源 | Apple template id `com.apple.dt.unit.singleViewApplication`（iOS App / single view） |
| 生成方式 | `create-xcode` CLI（模拟 Xcode New Project；**非** xcodegen / tuist / GitHub 第三方壳） |
| 验收 | `xcodebuild` Simulator Debug **BUILD SUCCEEDED**（采集时） |

> 说明：本机 Agent 无 Accessibility，无法驱动 Xcode GUI；改用 `npx create-xcode` 按同一官方 template id 生成。刷新时优先仍可用 Xcode GUI New Project 重采。

## 与 `swift_shell` 的关系

流水线 `lock.dimensions`（`ensure_native_shell_scaffold`）已接线：

1. 先 apply 本骨架 → 得到根目录 `.xcodeproj`（Windows 不依赖 xcodegen）  
2. 再 apply `swift_shell` → `ios/{APP}/` + `project.yml`  
3. 将骨架 `path` 重定向为 `ios/{APP}`；macOS 若有 xcodegen 则优先用 `project.yml` 全量 regenerate  
4. rename 目标已存在时跳过/清理，不再 `FileExistsError`  

不要把本骨架合并进 `swift_shell/`，以免与厂包夹板职责混淆。

## 目录结构

```
ios_app_skeleton/
├── README.md
├── template.json
├── apply.py
└── {{APP_NAME}}/
    ├── {{APP_NAME}}.xcodeproj/
    │   ├── project.pbxproj
    │   └── xcshareddata/xcschemes/{{APP_NAME}}.xcscheme
    └── {{APP_NAME}}/
        ├── {{APP_NAME}}App.swift
        ├── ContentView.swift
        └── Assets.xcassets/
```

## 占位符

| 占位符 | 含义 | 示例 |
|--------|------|------|
| `{{APP_NAME}}` | 产品名 PascalCase | `Lensoo` |
| `{{APP_NAME_LOWER}}` | 小写 | `lensoo` |
| `{{BUNDLE_ID}}` | Bundle ID | `test.duckegg.ios` |
| `{{TEAM_ID}}` | 开发团队（可空） | |

## 本地 apply 示例

```bash
python3 data/static/templates/ios_app_skeleton/apply.py \
  --src 'data/static/templates/ios_app_skeleton/{{APP_NAME}}' \
  --app-name Lensoo \
  --bundle-id test.duckegg.ios.lensoo \
  --dst /tmp/Lensoo-skeleton-smoke
```

## 刷新流程（Xcode 大版本升级后）

1. 用 Xcode **File → New → Project → iOS → App**（SwiftUI / Swift / 无 Core Data / 无测试），或等价：  
   `npx create-xcode AppSkeleton --org com.example -p ios -t app --storage none --testing none -y`  
2. Simulator 编过一次  
3. 按本仓占位符规则替换后覆盖 `{{APP_NAME}}/`  
4. 更新本 README 采集表与 `docs/plans/Swift官方Xcode骨架模板-Mac采集计划.md` 采集记录  

## 禁止

- 提交 `xcuserdata/`、`.DS_Store`、DerivedData  
- 提交真实 Team ID / 证书 / 描述文件  
- 把壳模板误称为官方模板，或把本骨架误称为 `swift_shell`
