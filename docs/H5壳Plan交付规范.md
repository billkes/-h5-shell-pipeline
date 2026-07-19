# H5 壳 Plan 阶段交付规范

Agent **Part 1（Plan）** 须一次性产出下列文件。细则以本文为准；prompt 不重复条文。

## Deliverable 1) `功能文档.md`（English，无代码）

**深度：** 须通过 plan.gate `SPEC-xxx`；tier 见 `skill-input/context.json` → `businessDepthTier`。先读《H5壳功能文档深度标准.md》。

**章节顺序（全部包含）：**

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
- **App Store Listing**

**锁定：** Screen Inventory 为权威； listed = MUST implement；禁止 optional/may/可选项。

## Deliverable 1b) `{全称}.md`（中文产品文档）

格式：《H5壳产品文档格式.md》；H1 = CSV `全称`；与 `功能文档.md` 对齐。

## Deliverable 1c) Legal agreements（English MD）

- `{主名字} Privacy Agreement.md`
- `{主名字} User Agreement.md`

规范：`docs/法律协议规范.md`（workspace 根目录拷贝）。plan.gate / dev.h5.gate 调用 `verify_h5_legal_md()`。

## Deliverable 2) `视觉蓝图.md`（English）

须含 V2 门禁章节 + **§Ambient Canvas Canon**（读 `skill-adapt/ambient-canvas-brief.md` 后展开）。

**章节顺序：** Visual Identity · Anti-Patterns · Color Tokens · Typography · Shape & Radius · Iconography（inline SVG sprite）· Imagery · Navigation Pattern · **Ambient Canvas Canon** · Per-screen Layout（仅 Screen Inventory 内屏幕）· Overlay & Feedback · Confirmation Dialog · Export Card · List Row · Detail · Modal · Form · Tag & Filter · IAP Store（若有 `#/store`）· Welcome Gate（若有 `#/welcome`）· Motion · Component Selection · Package Token Overrides · Dark Mode。

**skill.pages：** `design-system/*/pages/*.md` 不预置；`功能文档.md` 存在后 pipeline 在 plan.gate 前运行 `reconcile_pages_from_spec`。

## 其他 Plan 产物

- `本包登记信息.json` — shellRuntime、Bridge/kit draws、h5 vault、appSlug、h5EntryUrl*
- `本包视觉锁.json` — designerDeckSelections、ambientCanvas、componentSelection
- `产包计划.md` — P2-Shell → P2-H5 → dev.h5.build → deploy gate

Pack 级约束详见《H5壳Pack约束.md》。
