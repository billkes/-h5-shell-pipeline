# H5 壳 Plan 阶段交付规范

Agent **Part 1（Plan）** 须一次性产出下列文件。细则以本文为准；prompt 不重复条文。

## Deliverable 1) `功能文档.md`（English 规格 + 中文产品概述 + App Store Listing）

**一步产出**：`agent.plan.spec` 写 **一个** `功能文档.md`，不再单独产出 `{全称}.md`。

**深度：** 须通过 plan.gate `SPEC-xxx`；tier 见 `skill-input/context.json` → `businessDepthTier`。先读《H5壳功能文档深度标准.md》。

**章节顺序（全部包含于同一文件）：**

**English 规格块：**

- **App Theme & Angle** — 一段， grounded in CSV product flow
- **Screen Inventory** — 表：**PM 完整 H5 路由**（无流水线默认页；Splash/Welcome/Legal/Plaza/Store 仅在产品需要时列入）
- **Tab navigation (h5_shell)** — tab-root 须与 `_preview/preview-canonical.md` §Tabs 一致（3–5 个 bottom TabBar 路由）；`#/legal`、`#/plaza` 等 stack 路由不计入 3–5
- **Interaction Topology** — 引用 topology id；主/次模块；Explicitly NOT
- **Domain Model & Data Contract** — 实体表
- **Business Rules Engine** — BR-01…
- **Primary Workflow** — 编号步骤
- **Secondary Workflows** — 按 tier 数量
- **State & Empty Matrix**
- **Professional Surface** — Glossary + Metrics + **signature H5 interaction** 绑定 Primary Workflow 一步
- **4.2 Native Offset** — ≥3 Bridge 能力
- **Bridge Capability Matrix**
- **Export / Save Flow**
- **IAP Catalog & Free Tier** — 对齐 `iap-catalog.generated.md`
- **§H5 Architecture** — h5StateModel / h5RouterPattern / h5ScreenPattern 文件映射

**中文产品块**（格式见《H5壳产品文档格式.md》）：

- `#### 产品概述 (Product Overview)` — 定位、边界、差异化、受众、协议链接

**English Listing 块（文件末尾，仅一次）：**

- `#### App Store Listing` — Subtitle · Promotional Text · Description · Keywords

**锁定：** Screen Inventory 为权威； listed = MUST implement；禁止 optional/may/可选项。

### Export / Welcome / 主题收口（产包后必过 · 20260721）

| 项 | 必须 | 禁止 |
|----|------|------|
| **Export** | 预览与导出 **同构图同比例**；按预览实际像素导出 | 导出再缩放导致文案变形；预览有图导出空白 |
| **Welcome** | 三屏贴合主题；关键交互可见可发现 | 纯模板口号墙；交互控件对比度不足 |
| **主题贴合** | Tab1 有英雄焦点；motif 一眼可读 | 灰土默认底、乱配色、装饰抢戏 |
| **内容收敛** | 主 Tab 合并展示、间距有章法 | 多视图并列过载 |

功能文档 **Export / Save Flow** 与 **Primary Workflow** 须写明导出保真约束；Welcome 槽位以 `pages/welcome.md` 为准并在实现阶段验交互可见性。

## Deliverable 1b) Legal agreements（English MD）

- `{主名字} Privacy Agreement.md`
- `{主名字} User Agreement.md`

与 `功能文档.md` 同一步（`agent.plan.spec`）产出。规范：《法律协议规范.md》。plan.gate 调用 `verify_h5_legal_md()`。

**产包后（有在线链接时）**：产品概述 / 登记须写入可访问 HTTPS；H5 点击走 **系统浏览器**（见《H5壳Legal弹层规范.md》外开模式）。MD 仍为文档产物与 gate 正文源。
## Deliverable 2) 视觉规范（**不再**产出 `视觉蓝图.md`）

h5_shell 包的 UI 规范由 skill 链写入 workspace，Agent **禁止**再写 `视觉蓝图.md`（与 skill 产物冲突）：

| 来源步骤 | 路径 |
|----------|------|
| `skill.design` | `design-system/*/MASTER.md` |
| `skill.enrich` | `ux-checklist.md` · `h5-interface-brief.md` |
| `skill.adapt` | `skill-adapt/design-brief.md` · `ambient-canvas-brief.md` · `design-tokens.css` |
| `skill.pages` | `design-system/*/pages/*.md` |
| `agent.plan.pack` | `本包视觉锁.json`（componentSelection · colorTokens · ambientCanvas · assetBrief 六槽） |
| `agent.assets` | 真图六槽（仅 task「真图」=1） |

H5 实现读 `agent-spec-index` 索引路径；逐屏 override 以 `pages/*.md` 为准。

### （Legacy）Welcome / Hub Canon

Welcome / Hub 场景叙事与槽位见 `design-system/*/pages/welcome.md` · `hub.md`（`skill.pages` 动态生成），不再写进 `视觉蓝图.md`。

## 其他 Plan 产物

- `本包登记信息.json` — shellRuntime、Bridge/kit draws、h5 vault、appSlug、h5EntryUrl*
- `本包视觉锁.json` — designerDeckSelections、ambientCanvas、componentSelection
- `产包计划.md` — P2-Shell → P2-H5 → dev.h5.build → deploy gate

Pack 级约束详见《H5壳Pack约束.md`。
