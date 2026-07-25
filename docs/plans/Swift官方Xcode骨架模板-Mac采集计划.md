# Swift 官方 Xcode 骨架模板 · Mac 采集计划

> 目的：在 **Mac + Xcode（GUI）** 上用 Apple 官方 New Project 生成一份空 iOS App 工程，固化进 `h5-shell-pipeline` 仓库，供 **Windows 产包机只拷贝、不跑 xcodegen**。  
> 对话可能跨设备中断：本文件为唯一交接说明。  
> 状态：待 Mac 执行 · 与「壳模板」`swift_shell` 分开

---

## 1. 背景与目标

| 问题 | 说明 |
|------|------|
| Windows 无 Xcode / 无可靠 xcodegen | 不能在产包机「创建」`.xcodeproj` |
| 壳模板 ≠ 官方模板 | `data/static/templates/swift_shell/` 是 **壳模板**（Bridge/WKWebView 夹板） |
| 官方模板 | **Xcode → File → New → Project → iOS App** 生成的空工程骨架 |
| OC 夹板 | 维护滞后，**不要**以 OC 为母版 |

**目标流水线顺序（落地后）：**

1. 拷贝仓内 **官方骨架**（本计划产物）→ 占位符替换  
2. 再套 **壳模板** `swift_shell`（apply）  
3. 再走正常步骤（Agent / H5…）

本计划 **只做第 0 步：采集并检入官方骨架**；流水线改接线可另开任务。

---

## 2. 环境要求（Mac）

- [ ] macOS + 已安装 Xcode（建议与团队上架用的主版本一致，记下版本）
- [ ] 本地已 clone：`h5-shell-pipeline`（可推送到 remote 的分支）
- [ ] **不要用** `xcodegen` / `tuist` 生成此骨架（必须走 Xcode GUI 官方模板）

记录到本文件末尾「采集记录」：

- Xcode 版本：`xcodebuild -version` 输出  
- macOS 版本  

---

## 3. 用官方模板创建空工程（GUI）

1. 打开 Xcode → **File → New → Project…**
2. 选 **iOS → App** → Next  
3. 建议选项（与当前 Swift 壳一致则优先）：

| 选项 | 建议值 | 备注 |
|------|--------|------|
| Product Name | `AppSkeleton` | 检入前再改成占位符 |
| Team | None | 仓内不绑团队 |
| Organization Identifier | `com.example` | 占位即可 |
| Interface | **SwiftUI** 或 **Storyboard** | **必须与壳模板约定一致**；当前夹板偏 SwiftUI App 入口则选 SwiftUI |
| Language | **Swift** | |
| Storage | None | 勿勾 Core Data |
| 测试 | 可不勾 Unit/UI Test | 骨架越瘦越好 |

4. 保存到临时目录（**不要**直接保存在 `output/`）  
5. 用 Xcode **打开一次**，确认能列出 Target、无立即报错即可（不必真机跑）  
6. 关闭 Xcode，避免锁文件

---

## 4. 固化进仓库的目录约定

建议新增（与壳模板并列）：

```text
data/static/templates/ios_app_skeleton/
├── README.md                 # 来源、Xcode 版本、如何刷新
├── template.json             # 元数据 + 占位符表
├── apply.py                  # 可选：与 swift_shell 同类的占位符替换（或复用脚本）
└── {{APP_NAME}}/
    ├── {{APP_NAME}}.xcodeproj/
    │   ├── project.pbxproj
    │   └── xcshareddata/xcschemes/{{APP_NAME}}.xcscheme   # 若有
    └── {{APP_NAME}}/           # 或 Sources/ 等官方默认布局——保持 New Project 原样再占位符化
        ├── {{APP_NAME}}App.swift   # 名称以实际为准
        ├── ContentView.swift       # 若有；壳阶段可再替换
        ├── Assets.xcassets/
        └── …
```

**禁止：**

- 把骨架直接合并进 `swift_shell/` 而不加说明（职责混淆）  
- 提交 `xcuserdata/`、`.DS_Store`、DerivedData  
- 提交真实 Team ID / 证书 / 描述文件  

---

## 5. 占位符化步骤（Mac 上做完再提交）

在拷进 `{{APP_NAME}}/` 之前，把工程内硬编码改成占位符（与壳模板对齐）：

| 占位符 | 含义 | 示例 |
|--------|------|------|
| `{{APP_NAME}}` | 产品名 PascalCase | `Lensoo` |
| `{{APP_NAME_LOWER}}` | 小写 | `lensoo` |
| `{{BUNDLE_ID}}` | Bundle ID | `test.duckegg.ios` |
| `{{TEAM_ID}}` | 开发团队（可空字符串） | |

至少替换：

- [ ] 目录名 / `.xcodeproj` 名  
- [ ] `project.pbxproj` 内 PRODUCT_NAME、PRODUCT_BUNDLE_IDENTIFIER、路径引用  
- [ ] scheme 名（若有）  
- [ ] 源码里的 `AppSkeletonApp` 等类型名 → `{{APP_NAME}}App`（按实际入口文件）

自检：

```bash
# 在模板目录内不应再出现采集时的临时名
rg -n "AppSkeleton|com\\.example" data/static/templates/ios_app_skeleton || true
```

---

## 6. README 必写内容（骨架目录内）

- 采集日期、Xcode 版本、Interface（SwiftUI/Storyboard）  
- 「来源 = Xcode New Project iOS App，非 xcodegen、非 GitHub 第三方」  
- 刷新流程：Xcode 大版本升级后如何按本计划重采  
- 与 `swift_shell` 的关系：先骨架、后壳模板  

---

## 7. Git 提交建议（Mac）

```text
分支: feat/ios-app-skeleton-from-xcode
提交信息: add ios_app_skeleton from Xcode New Project for Windows apply-only path
```

勿 force-push；PR 说明附上本计划路径。

---

## 8. 回到 Windows 后的验收（骨架已进仓）

- [ ] 仓内存在 `data/static/templates/ios_app_skeleton/{{APP_NAME}}/**/*.xcodeproj`  
- [ ] 无 `xcodegen` 也能 `apply`/拷贝出带 `project.pbxproj` 的树  
- [ ] （另任务）流水线 `lock.dimensions`：先骨架 → 再 `swift_shell` → rename 容错  
- [ ] Lensoo：清 rename 冲突后重跑 `2–3`，应出现 `网页Agent续跑手册.md`  

> 网页手册缺失与骨架无关，根因是 `lock.dimensions` 失败导致 `sync.distilled` 未跑；骨架落地后应减少「无 pbxproj → 反复套壳 → rename 冲突」。

---

## 9. 明确不做（本计划范围外）

- [ ] 不改 OC 壳、不以 OC 为母版  
- [ ] 不在本计划里改 Agent / ui-ux-pro-max  
- [ ] 不在 Windows 上「下载官方模板」——无此渠道  
- [ ] 不把壳模板误称为官方模板  

---

## 10. 采集记录（Mac 填写）

| 项 | 值 |
|----|-----|
| 日期 | |
| 执行人 | |
| macOS | |
| Xcode | |
| Interface | SwiftUI / Storyboard |
| 本地分支 | |
| PR / commit | |
| 备注 | |
```

已写入：`docs/plans/Swift官方Xcode骨架模板-Mac采集计划.md`。Mac 上打开该文件按清单执行即可。