# H5 壳 Flutter 版产品要求

用于批量生成 **`h5_shell`** 类 iOS 应用（Flutter 薄壳 + **远程在线 H5**）时的约束。Flutter **仅作桥 + 本地静态资产宿主**；业务 UI、路由、数据、IAP 界面均在 **部署后的 H5 站点**。

配套文档：

- 《H5-Bridge协议.md》— 能力签名与错误码
- 《H5壳业务流程文字版.md》— Bridge 级逐步菜谱
- 《H5壳广场页规范.md》— 隐藏 Bridge 验权页
- 《H5去风味规范.md》— 去网页味体验清单
- 《H5壳IAP协议.md》— H5 UI + 原生 StoreKit 桥
- 《H5壳Flutter交付自检清单.md》— 上架前自检
- 《**H5壳功能文档深度标准.md**》— 功能完整度 / 业务深度 / 专业性（plan.gate）

高差异化实现目标与资源命名约定见 **《Flutter差异化开发规则.md》**；壳侧仍生成 `.cursor/rules/*.mdc`（命名 / 架构 / 状态 / 编程风格四维度）。

---

## 1. 产品形态

| 层 | 职责 |
|----|------|
| **Flutter 壳** | 单全屏 WebView 容器、JS Bridge、本地 raster 资产（mediaServe）、LaunchScreen 占位图、加载失败兜底 |
| **H5（远程站点）** | Splash、Welcome 门闸、协议弹窗/页、全部业务 UI、路由、内购商店 UI、数据、**隐藏广场页** |

**禁止**：Flutter 实现 3 Tab 工具页、Feed、Profile、与 H5 重复的底栏/导航、假工具再切 H5。

---

## 2. H5 部署（远程 URL · 人工上线）

| 项 | 约定 |
|----|------|
| **业务 H5** | **不**打进 Flutter `pubspec` assets；Implementer 产出可部署静态站，默认目录 `h5_site/` |
| **壳首屏 URL** | 从 `本包登记信息.json` 读 **`h5EntryUrl`**（开发期 `h5EntryUrlDev`，上线前切 `h5EntryUrlProd`） |
| **线上路径** | `https://test.darin.beauty/{appSlug}/` — `appSlug` = 应用名全小写 |
| **开发路径** | 局域网静态服，如 `http://127.0.0.1:8080/` |
| **离线** | **非产品目标**；无网时壳显示英文 Retry |

### 2.1 H5 站点文件（Implementer）

- 站点根：`h5SiteRoot`（默认 `h5_site/`）
- 入口：`h5SiteEntry`（固定 `index.html`，位于 `h5_site/{appSlug}/`）
- 结构按 **`h5VaultPattern`**
- **禁止**路径片段：`h5`、`index`、`web`、`bridge`、`webview`

### 2.2 壳内资产（仍打进包）

- Export frame、panel 位图等 raster 留在 Flutter `pubspec` 的 `assetRoots`
- H5 经 Bridge **`mediaServe`** 引用 — **禁止 base64 大图**

---

## 3. 必须满足（壳侧）

| 项 | 要求 |
|----|------|
| **主 WebView** | 冷启动 `loadRequest(h5EntryUrl)`；无地址栏 |
| **LaunchScreen** | **1125×2436** 占位图；真实启动页不在本流水线范围 |
| **LaunchVeil** | 同图续接直至 H5 `shellReady` |
| **可见 UI** | **禁止** Flutter Splash/Welcome/Legal |
| **协议** | H5 弹窗/页展示英文协议；**禁止**外链 HTTPS |
| **Bridge** | task.csv 七维组合 |
| **媒体** | **禁止 base64**；按 `mediaServe` 维度 |
| **隐私** | 若 Screen Inventory 含 Welcome/Settings，提供协议只读入口 |
| **差异化** | `dartCodePrefix`、架构文件夹、命名混淆、编程人设 |

---

## 4. Phase 1 输出（本类型专用）

### 4.1 功能文档深度（MANDATORY · 见《H5壳功能文档深度标准.md》）

PM 在 `功能文档.md` 须达到 **businessDepthTier**（默认 L2）：

- **Domain Model & Data Contract** — 实体表 + 校验 + 持久化 key
- **Business Rules Engine** — BR-01… 可执行规则
- **Primary Workflow** — 逐步主流程（含数据变更与反馈）
- **Secondary Workflows** — 辅流程 ×2（L2）
- **State & Empty Matrix** — 全边界态文案
- **Professional Surface** — Domain Glossary + Metrics & Reports + signature interaction（绑定业务步骤）
- **4.2 Native Offset** — ≥3 项，映射主流程步骤
- **Bridge Capability Matrix** — 与业务流程编号对齐

**禁止**：optional / may / 可选项；写了即 MUST implement。

### 4.2 其它 PM 产出

- **功能文档.md**：Screen Inventory（**PM 决定的 H5 路由全集**）、Export/Save、IAP & Free Tier、§H5 Architecture、App Store 英文文案
- **本包登记信息.json**：`themeAngle`、`appSlug`、`h5EntryUrl*`、`h5SiteRoot/Entry`、`h5VaultPattern/Layout`、`bridgeCapabilities`、`bridgeDeckSelections`、`kitDeckSelections`、`codeAntiCorrelation`
- **产包计划.md**：P2-Shell → P2-H5 → **人工部署门**
- **不强制**：`tab1Name`/`tab2Name`/`tab3Name`；**不生成** `默认内容列表.json`
- **须抽卡**：PM 六维 + Designer 七维 + Bridge 七维 + Kit 十一维

---

## 5. Bridge 七维（task.csv 抽卡）

| CSV 列 | 说明 |
|--------|------|
| `webviewEngine` | WebView 底座 |
| `bridgeCallStyle` | H5 → Native 调用 |
| `bridgeCallbackStyle` | Native → H5 回调 |
| `bridgeEnvelope` | 消息封装 |
| `mediaServe` | 媒体回显（禁 base64） |
| `bridgeErrorCode` | 错误码风格 |
| `bridgeInjectTiming` | Bridge 注入时机 |

### 5.5 H5 Kit 十一维

| CSV 列 | 说明 |
|--------|------|
| `kitAtomSet` … `kitMotionApproach` | 微组件库 8 维 |
| `h5StateModel` / `h5RouterPattern` / `h5ScreenPattern` | H5 业务架构 |

CSV `状态管理` / `架构模式` 仅约束 **壳**；H5 以 Kit 三维为准。

---

## 6. 技术栈与依赖

- **WebView**：`webview_flutter` 或 `flutter_inappwebview`
- **媒体**：按 `mediaServe` 可能需 `shelf` + `shelf_static`
- **权限**：`permission_handler`、`image_picker` 等 — 仅 Bridge 白名单
- **IAP**：`in_app_purchase` — H5 调 `purchase` Bridge；UI 在 H5

---

## 7. App 生命周期路由

```
冷启动 → LaunchScreen → LaunchVeil → loadRequest(h5EntryUrl)
      → H5 首屏（由 Screen Inventory 决定，常见：Splash → Welcome → 业务 SPA）
      → shellReady → 撤 Veil
```

主 WebView 导航 **全部由 H5 负责**。

---

## 8. 与 tool_flutter 的差异

| 项 | tool_flutter | h5_shell |
|----|--------------|----------|
| offline-first PM | 强制 | **不适用**（远程 URL） |
| 功能文档深度 | Main Tool Flow + 2 内容种子 | **Domain Model + BR + Workflow 矩阵**（深度标准） |
| Bridge 七维 | 无 | **必填** |
| 3 Tab 要求 | 强制 | **不适用** |

---

## 9. 审核路径（A 面）

审核员可见：商店元数据 + **Screen Inventory 中声明的合规入口**（常见 Welcome）+ **在线 H5 首屏**。B 面叙事写在 H5 内，不在 Flutter 功能文档展开。

- **Welcome Gate Canon**：仅当 Screen Inventory 含 `#/welcome`（视觉蓝图 + welcomeSpec）
- **Bridge 广场页**：仅当 Screen Inventory 含 `#/plaza`（Settings 长按版本 3s → `#/plaza`）

---

## 10. H5 去风味与过审

- AppBar `position: fixed`
- 4.2：去风味 + Native Offset ≥3
- 4.3：壳侧差异化；H5 视觉可不差异化；**signature interaction 须有业务语义**

---

## 11. P2 分工

| 子步骤 | Agent | 产出 |
|--------|-------|------|
| P2-Shell | Shell Programmer | WebView + Bridge + analyze 0 error |
| P2-H5 | H5 Implementer | 可部署 H5 站点（Screen Inventory 声明的路由） |
| 人工部署 | 人工 | 上传 → `h5EntryUrlProd` |

Implementer **必须**按 `功能文档.md` 的 BR-xx 与 Primary Workflow 步骤实现，不得省略 State & Empty Matrix 中的态。
