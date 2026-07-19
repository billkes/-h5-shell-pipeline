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

## Deliverable 1b) Legal agreements（English MD）

- `{主名字} Privacy Agreement.md`
- `{主名字} User Agreement.md`

与 `功能文档.md` 同一步（`agent.plan.spec`）产出。规范：`docs/法律协议规范.md`。plan.gate 调用 `verify_h5_legal_md()`。

## Deliverable 2) 视觉规范（**不再**产出 `视觉蓝图.md`）

h5_shell 包的 UI 规范由 skill 链写入 workspace，Agent **禁止**再写 `视觉蓝图.md`（与 skill 产物冲突）：

| 来源步骤 | 路径 |
|----------|------|
| `skill.design` | `design-system/*/MASTER.md` |
| `skill.enrich` | `ux-checklist.md` · `h5-interface-brief.md` |
| `skill.adapt` | `skill-adapt/design-brief.md` · `ambient-canvas-brief.md` · `design-tokens.css` |
| `skill.pages` | `design-system/*/pages/*.md` |
| `agent.plan.pack` | `本包视觉锁.json`（componentSelection · colorTokens · ambientCanvas） |

H5 实现读 `agent-spec-index` 索引路径；逐屏 override 以 `pages/*.md` 为准。

### （Legacy）Welcome / Hub Canon

Welcome / Hub 场景叙事与槽位见 `design-system/*/pages/welcome.md` · `hub.md`（`skill.pages` 动态生成），不再写进 `视觉蓝图.md`。

## 其他 Plan 产物

- `本包登记信息.json` — shellRuntime、Bridge/kit draws、h5 vault、appSlug、h5EntryUrl*
- `本包视觉锁.json` — designerDeckSelections、ambientCanvas、componentSelection
- `产包计划.md` — P2-Shell → P2-H5 → dev.h5.build → deploy gate

Pack 级约束详见《H5壳Pack约束.md`。
