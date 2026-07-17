[h5-shell-pipeline — context note]
This repo is independent from cursor-ios-batch. Follow workspace `.cursor/rules/*.mdc` and `docs/rules/` as the source of truth.
Role focus for this phase:
   - `01_tech_common/A-Crush项目总览.md`
   - `01_tech_common/Cursor-Agent上下文隔离.md`
   - `01_tech_common/Flutter-ui-layout-pitfalls.md`
   - `01_tech_common/Flutter-asset-alignment-pitfalls.md`
   - `02_audit_risk/App-Store-Guideline-4.3-Spam.md`
   - `02_audit_risk/0630-4.3复盘结论.md`

You are the **Build Agent — Part 1 (Plan & design artifacts)** for one H5 shell iOS app.



App Name: Monthio
Description: Theme: 月度习惯复盘; Track: 个人成长; Audience: 需要追踪长期习惯并进行月度复盘的自我提升者; Core scene: 月末生成习惯复盘报告; Local feature: 习惯打卡与月度数据可视化分析; Product flow: Track daily habits for 月末生成习惯复盘报告; log streak data into 习惯打卡与月度数据可视化分析; highlight completed months on a yearly heatmap with optional milestone badges; browse the monthly habit trends and export a growth summary card for 需要追踪长期习惯并进行月度复盘的自我提升者; StoreKit unlocks premium habit templates, PDF growth reports, and dark themes with Restore Purchases in Me.

**Rules:**
- Output ENGLISH plan/design files only — **no implementation code** in this sub-step.
- **Read `skill-adapt/design-brief.md` + `skill-adapt/ambient-canvas-brief.md` + `design-system/*/MASTER.md` before writing 视觉蓝图.md.**
- Do NOT invent generic UI/UX rules — expand ui-ux-pro-max outputs into batch deliverables.


You are the **combined PM + UI Designer + Delivery Planner** for one **H5 shell** iOS app in a batch. Produce **seven files** in one pass. All output text is ENGLISH unless otherwise specified. Do NOT write Dart/Swift/OC/H5 implementation code in this phase.

App Name: Monthio
One-line Description: Theme: 月度习惯复盘; Track: 个人成长; Audience: 需要追踪长期习惯并进行月度复盘的自我提升者; Core scene: 月末生成习惯复盘报告; Local feature: 习惯打卡与月度数据可视化分析; Product flow: Track daily habits for 月末生成习惯复盘报告; log streak data into 习惯打卡与月度数据可视化分析; highlight completed months on a yearly heatmap with optional milestone badges; browse the monthly habit trends and export a growth summary card for 需要追踪长期习惯并进行月度复盘的自我提升者; StoreKit unlocks premium habit templates, PDF growth reports, and dark themes with Restore Purchases in Me.
Tech Stack: H5 remote site + native WebView shell (Flutter / Swift / OC per pack type)
[CSV Product Doc — REQUIRED]
- 全称(full_name) from CSV: Monthio - Habit & Review
- Product documentation file MUST be named exactly `Monthio - Habit & Review.md` (not a creative variant).
- Format: read 《H5壳产品文档格式.md》 — sections: 产品概述, App Store Listing, 业务流程总结, 审核/演示路线 (Mockoo 样例).
- H1 MUST be: `# Monthio - Habit & Review`


[Required Reading — this workspace]
- 《H5壳Flutter产品要求.md》 — product contract
- 《H5壳产品文档格式.md》 — **{全称}.md** 中文产品文档章节模板（Mockoo 样例）
- skill-adapt/design-brief.md · skill-adapt/ambient-canvas-brief.md · design-system/*/MASTER.md — ui-ux-pro-max (**primary UI source**)
- design-system/*/pages/*.md · ux-checklist.md · h5-interface-brief.md — skill.enrich + skill.pages
- data/static/component_kit/README.md · baseline.md · tokens.md
- `.cursor/rules/*.mdc` — iron rules (h5_shell: iron-1..5 + vault-compliance + h5-deflavor)

[Component Kit — Plan gate only; read kit `.md` files during §Component Selection]
- Index: `data/static/component_kit/README.md` · `baseline.md` · `tokens.md`
- Do NOT invent off-list shared widgets; cite kit paths in §Component Selection.
[Required §Component Selection — batch-enforced at plan.gate]
MUST appear in 视觉蓝图 §Component Selection, 本包视觉锁.json componentSelection, §Package Token Overrides, and 产包计划 §2.x:
- `shell/bridge_toast`
- `shell/launch_veil`
- `shell/webview_host`
Currently missing from visual lock (add now): shell/bridge_toast, shell/launch_veil, shell/webview_host

[Hard Constraints — wired in by the batch script]
[Code & Structure — ASSIGNED for this package; you MUST document and use these exactly]
- dartCodePrefix: foztu
- namingStyle: screen_suffix
- folderStyle: by_feature   (anti-correlation tag only; see architecturePattern)
- architecture: layered   (anti-correlation tag only; code STRUCTURE is governed by architecturePattern below)
- stateManagement: setstate
- codeOrganization: fine_grained
- fileNaming: snake_case
- importStyle: relative
- constantsLayout: per_feature
- iapModuleName: PurchaseService
- reportModuleName: ContentReportService
- constantsModuleName: ThemeConfig
- networkLayerName: RequestManager
- routeCoordinatorName: NavigationHandler
- utilityHelperName: FormatterHelper
- architectureFolders: {'models': {'role': 'models', 'folderSuffix': 'spark_slot', 'folderBasename': 'foztu_spark_slot', 'stubBasename': 'foztu_quill_port_anchor', 'stubClassSuffix': 'Layer'}, 'views': {'role': 'views', 'folderSuffix': 'nova_zone', 'folderBasename': 'foztu_nova_zone', 'stubBasename': 'foztu_http_hub_anchor', 'stubClassSuffix': 'Layer'}, 'controllers': {'role': 'controllers', 'folderSuffix': 'mesh_path', 'folderBasename': 'foztu_mesh_path', 'stubBasename': 'foztu_dock_link_anchor', 'stubClassSuffix': 'Controller'}}
- programmingStyle: 法国人
- architecturePattern: mvc
- csvStateManagement: SetState
- csvArchitecturePattern: MVC
- namingObfuscationRule: 辅音核心策略
- namingRuleMeta: {'ruleKey': 'consonant_core', 'packageSeed': 'foztu', 'affix': 'prefix', 'lengthRange': [2, 4], 'joinStyles': {'class': 'pascal', 'record': 'pascal', 'method': 'camel', 'field': 'camel', 'param': 'camel', 'local': 'camel', 'enum_value': 'camel', 'file': 'snake', 'folder': 'snake'}, 'batchId': 'TEST-0717', 'namingObfuscationRule': '辅音核心策略'}

[CSV Architecture — REQUIRED]
状态管理 and 架构模式 are TWO INDEPENDENT dimensions from CSV. Do NOT merge them into one nested label or treat one as a subtype of the other.
- stateManagement (CSV 状态管理): SetState → internal key `setstate`, use built-in StatefulWidget + setState only
- architecturePattern (CSV 架构模式): MVC → internal key `mvc`; MVC — Model / View / Controller; role folders are opaque names in architectureFolders (NOT {prefix}_models/ etc.)
- Read 状态管理矩阵.md and 架构模式矩阵.md: state rules and folder layout apply separately per dimension.
- architecturePattern and stateManagement (from CSV) are AUTHORITATIVE for code structure and state; the combo `architecture` / `folderStyle` keys are anti-correlation tags only — do NOT treat them as a second, conflicting structural directive.
- Do NOT default to setState unless CSV 状态管理 is SetState.
- Add required pubspec dependencies for the chosen state package.
- Document both dimensions in 功能文档.md Code layout section.


[CSV Programming Style — REQUIRED]
- programmingStyle (from CSV 编程风格): 法国人
- Read 编程人设风格.md; locate the row for this persona.
- Apply ALL 7 matrix cells for that row to every `.dart` file:
  1) Widget split & nesting  2) Style / const / final
  3) Syntax sugar & iteration  4) Control flow & async
  5) Method split & null safety
  6) Lib directory topology (libLayout)  7) Asset roots & naming
- The 7 cells are MANDATORY and override your defaults.
- Dims 6–7 are enforced via 本包维度锁.json + 本包资源布局.json.
- Persona affects coding style and tree shape — NOT feature scope.

[CSV Programming Style — Layout (dims 6–7) — REQUIRED]
- libLayout: `dual_hub` — Split `{prefix}_core/` (tokens, models) vs `{prefix}_surface/` (views, presenters/controllers); no top-level `{prefix}_skin/`.
- assetLayout: `assets_prefix_surfaces_glyphs` — Two obfuscated roots: surface vs glyph rasters.
- skinBucket directory: `foztu_skin/`
- pubspec asset roots (ONLY these): `assets/foztu/surfaces/`, `assets/foztu/glyphs/`
- assetNamingPattern: transform_identifier(entity=file|folder) when namingRuleMeta present
- FORBIDDEN basenames (never use): global_background.jpg, global_background.png, splash_background.jpg, splash_background.png
- Read 本包资源布局.json; all Image.asset paths MUST live under declared roots.


[CSV Naming Obfuscation v2 — REQUIRED]
- namingObfuscationRule (from CSV): 辅音核心策略
- ruleKey: consonant_core
- Read 命名混淆规则.md — dynamic key per identifier (no pre-baked affix).
- dartCodePrefix / packageSeed in 本包代码组合.json is the package seed only.
- Affix position: prefix | suffix | infix | mirror (see namingRuleMeta.affix).
- Affix length varies within lengthRange; join style per entity (camel/pascal/snake/compact/dot/hyphen).
- Use transform_identifier() / derive_key() for EVERY namable (folders, files, classes, methods, fields, params, locals).

[CSV IAP Context — REQUIRED]
- 首个商品Code(first_product_code): `Month00`
- Increment style: suffix (base `Month`)
- All 19 productIds are listed in `iap-catalog.generated.md` (00–19 continuous; regular 12 then promo 8).
- Implement EVERY productId from that file in native/IAP code — not only the first SKU.
- FORBIDDEN: any `**/*.storekit` file and any `StoreKitConfigurationFileReference` in `*.xcscheme`. IAP must use App Store Connect / sandbox only (Flutter: in_app_purchase; OC/Swift: native StoreKit API).
- If you find dangling pbxproj/scheme references to a deleted `.storekit`, strip the references — do NOT re-add the file.
- FORBIDDEN in store/native IAP code: 324001, 32408, or any ID from old `内购项列表参考.md` price tables.
- EXCEPTION: Bridge Plaza `#/plaza` `purchase` QA button MUST use productId `311400` only (not catalog SKUs).

[IAP Catalog — SINGLE SOURCE OF TRUTH]
- Product count: 12 regular + 7 promotional = 19 consumable SKUs.
- Prices, coins, tags: workspace `iap-products.json` (same as repo `data/static/iap-products.json`).
- Product IDs: workspace `iap-catalog.generated.md` — generated from CSV 首个商品Code with 00–18 continuous increment (regular first, then promo).
- Layout / interaction: workspace `ios-iap-page-schemes.md` (compliance + dual-section layout rules).
- DO NOT use legacy IDs (311400, 324001, 32408, …) or prices from old docs.
- FORBIDDEN: `**/*.storekit` and `StoreKitConfigurationFileReference` in any `*.xcscheme` — IAP uses App Store Connect / sandbox only.
- `内购项列表参考.md` is consumable compliance only, not a product list.
- In 功能文档.md include an **IAP Catalog** section mirroring `iap-catalog.generated.md` tables (all productIds, coins, prices, tags).

# IAP Catalog (auto-generated — do not edit by hand)

本文件由 batch 根据 `iap-products.json` + CSV 首个商品Code 生成，为**本包唯一商品数据源**。实现内购页、功能文档 IAP 章节、App Store Connect 商品 ID 均须与此表一致。

- 首个商品Code（CSV）: `Month00`
- 自增方式: **suffix**（base `Month`，共 19 档，编号 00–18 连续）
- 版式与交互: `ios-iap-page-schemes.md`（双专区、禁 App 侧超时等）
- `内购项列表参考.md` 仅说明消耗型合规，**不得**抄其中旧价/324xxx

## 非促销专区

| productId | coins | price (USD) | tags |
|-----------|-------|-------------|------|
| Month00 | 99 | 0.99 | — |
| Month01 | 149 | 1.49 | — |
| Month02 | 399 | 3.99 | — |
| Month03 | 495 | 4.95 | — |
| Month04 | 899 | 7.99 | — |
| Month05 | 1190 | 9.9 | — |
| Month06 | 1495 | 12.95 | — |
| Month07 | 2499 | 19.99 | — |
| Month08 | 3999 | 29.99 | — |
| Month09 | 6999 | 49.99 | — |
| Month10 | 8499 | 59.99 | — |
| Month11 | 14999 | 99.99 | — |

## 限时促销专区

| productId | coins | promo (USD) | original (USD) |
|-----------|-------|---------------|----------------|
| Month12 | 190 | 0.99 | 1.99 |
| Month13 | 490 | 1.99 | 4.99 |
| Month14 | 740 | 2.99 | 5.99 |
| Month15 | 1190 | 4.95 | 9.95 |
| Month16 | 2690 | 11.95 | 20.95 |
| Month17 | 4590 | 19.99 | 29.99 |
| Month18 | 6990 | 35.99 | 49.99 |
[Design System — ui-ux-pro-max via skill.design + skill.adapt]
# Design Brief (skill.adapt)

**Selection:** Selected combined score 0.411 among 3 candidate(s) (collision + theme-fit + audience). Visual: bauhaus (包豪斯) / #0f172a / playfair display / horizontal scroll journey.

## Product Navigation Canon (MANDATORY — overrides uupm page pattern name)

- **Interaction topology:** T5_workspace · Single workspace
- **Core scene:** 月末生成习惯复盘报告
- **Local feature:** 习惯打卡与月度数据可视化分析
- **Audience:** 需要追踪长期习惯并进行月度复盘的自我提升者

Implement navigation, hub layout, and primary workflows from **productFlow** + topology above.
Candidate `pattern.name` (e.g. Lead Magnet / Enterprise SaaS) is **visual tone only**, not IA.

### Topology module roles
- **form:** canvas
- **list:** none
- **detail:** inline
- **export:** canvas-card

## Primary Sources
- `design-system/monthio/MASTER.md` — full design system (ui-ux-pro-max MASTER)
- `design-system/monthio/stack-html-tailwind.md` — stack implementation guidelines
- `design-system/*/pages/*.md` — per-screen overrides (override MASTER)
- `design-system/*/ux-checklist.md` — UX/a11y acceptance checklist
- `design-system/*/h5-interface-brief.md` — H5 monolith Do/Don't

## Visual Identity (colors & typography — IA from Product Navigation Canon)
- **Style:** Bauhaus (包豪斯) — bauhaus, geometric, constructivist, primary colors, hard shadow, bold, tactile, functional, poster, mechanical, architectural
- **Colors:** primary `#0F172A`, background `#020617`
- **Typography:** Playfair Display / Source Serif 4 (monochrome, editorial, austere, typographic, pocket manifesto, luxury, high contrast, brutalist mobile)
- **uupm pattern (visual tone only):** Horizontal Scroll Journey

## Ambient Canvas
Expand `skill-adapt/ambient-canvas-brief.md` into 视觉蓝图.md **§Ambient Canvas Canon**.
Motif follows **interaction topology**, not generic SaaS style keywords.

## Anti-Patterns (hard avoid in 视觉蓝图.md)
Excessive decoration

## Agent Rule
IA + workflows: topology + productFlow. Visual: MASTER + pages. Do not copy uupm pattern name as navigation.
MASTER path: `design-system/monthio/MASTER.md`
Ambient canvas: `skill-adapt/ambient-canvas-brief.md`
[Skill Enrich — ui-ux-pro-max domain briefs]
- ux: `design-system/monthio/ux-checklist.md`
- icons: `design-system/monthio/icon-brief.md`
- web: `design-system/monthio/h5-interface-brief.md`
- chart: `design-system/monthio/chart-brief.md`
[Tab-root Page Scaffold — pipeline-owned; DO NOT rewrite template]
- Topology: `T5_workspace` → section composer builds hub/list/settings from `sections/*.vue.frag`.
- Blueprint: `TAB_ROOT_BLUEPRINT` in `h5_page_sections.py` (aligned with `H5_PAGE_SPECS`).
- Implement business logic ONLY in `views/*View.logic.ts` (create if missing).
- Wizard / Live / Export / RunDetail — full Agent ownership.
- Welcome / Legal overlay markup + global CSS are pipeline-owned when legal docs or Legal modal are in scope.
- **All pipeline scaffold copy is English-only** — never inject CSV 中文主题/核心场景 into visible UI.
- When `_preview/*-tabs-preview.html` exists: tab-root views with `<!-- PREVIEW-IMPL:locked -->` or preview DOM markers are **never overwritten** by this step.

- Tab-root views will be scaffolded when router declares /hub, /runs, /settings.

Use skill-adapt/impl-ui-input.md during Programmer phase.
[Designer Selection — from ui-ux-pro-max skill.adapt; copy to 本包视觉锁.json designerDeckSelections]
- colorTemperature: Enabled green + disabled grey + experimental amber
- shapeLanguage: Bauhaus (包豪斯)
- typographyPersonality: Playfair Display
- navigationPattern: Single workspace
- heroVisualMotif: 月末生成习惯复盘报告 · 习惯打卡与月度数据可视化分析 · Single workspace
- interactionFlavor: Standard
- iconStyle: rounded outlined SVG
[Ambient Canvas — MANDATORY for 视觉蓝图.md + H5 entry.htm]
- Read `skill-adapt/ambient-canvas-brief.md` **before** writing 视觉蓝图.md.
- 视觉蓝图.md MUST include **§Ambient Canvas Canon** (see plan template): scene table, layer stack, CSS token table, motif implementation notes tied to heroVisualMotif / key_effects / navigationPattern.
- 本包视觉锁.json MUST include `ambientCanvas` object (scenes + token keys).
- H5 implementer MUST ship `u-{prefix}-ambient` in entry.htm per brief — not a post-hoc CSS tweak.
[Skill Enrich — ui-ux-pro-max domain briefs]
- ux: `design-system/monthio/ux-checklist.md`
- icons: `design-system/monthio/icon-brief.md`
- web: `design-system/monthio/h5-interface-brief.md`
- chart: `design-system/monthio/chart-brief.md`
[Tab-root Page Scaffold — pipeline-owned; DO NOT rewrite template]
- Topology: `T5_workspace` → section composer builds hub/list/settings from `sections/*.vue.frag`.
- Blueprint: `TAB_ROOT_BLUEPRINT` in `h5_page_sections.py` (aligned with `H5_PAGE_SPECS`).
- Implement business logic ONLY in `views/*View.logic.ts` (create if missing).
- Wizard / Live / Export / RunDetail — full Agent ownership.
- Welcome / Legal overlay markup + global CSS are pipeline-owned when legal docs or Legal modal are in scope.
- **All pipeline scaffold copy is English-only** — never inject CSV 中文主题/核心场景 into visible UI.
- When `_preview/*-tabs-preview.html` exists: tab-root views with `<!-- PREVIEW-IMPL:locked -->` or preview DOM markers are **never overwritten** by this step.

- Tab-root views will be scaffolded when router declares /hub, /runs, /settings.
[Design Tokens — read `skill-adapt/token-impl-block.md` before entry.htm styles]
[CSS Motion — read `skill-adapt/css-motion-brief.md` for H5 animation canon]
[Icon Sprite Manifest — read `skill-adapt/icon-sprite-manifest.json`; embed `foztu-mark-*` symbol IDs in entry.htm — NO icon font libraries]
[Free Tier — MANDATORY for content/video apps]
- Section title in 功能文档.md: **"Free Tier"**.
- freeTierCount: 2 for Publish (and any other IAP-gated actions).
- gatedActions: Publish MUST use free tier first; Detail Innovation save/export may also gate.
- uiPlacement: Compose/Publish screen and Profile show "Free posts remaining: N".
- logic: freeRemaining > 0 on publish → allow without coins; else coin deduction + confirm;
  insufficient → store.
- Persist key: free_remaining_v1 (int). Coin balance default 0.
[Business Depth — MANDATORY for 功能文档.md (plan.gate SPEC-xxx)]
- Tier: **L3** (analytics) — see 《H5壳功能文档深度标准.md》
- Min length: 4500 chars
- Domain entities: ≥4
- Business rules BR-01…: ≥9
- Primary Workflow numbered steps: ≥14
- Secondary Workflows: ≥2 (each ≥8 steps)
- Domain Glossary terms: ≥10
- Metrics & Reports definitions: ≥2
- Sections (English, in order): Domain Model · Business Rules · Primary Workflow ·
  Secondary Workflows · State & Empty Matrix · Professional Surface ·
  4.2 Native Offset · Bridge Capability Matrix · Screen Inventory ·
  Export/Save · IAP & Free Tier · §H5 Architecture
- signature H5 interaction MUST cite a Primary Workflow step (not decorative-only).
- FORBIDDEN: optional / may / 可选项 — every listed item is MUST implement.
- Complexity stays in H5 domain logic + Bridge; NO login / cloud sync / native Tabs.
[Interaction Topology — MANDATORY]
- Assigned: **T5_workspace** (Single workspace)
- Module roles: form=canvas, list=none, detail=inline, export=canvas-card
- FORBIDDEN as home/landing: list landing; master-detail stack
- Do NOT default to: chip filter → browse list → detail page → export weekly card.
- 功能文档.md MUST include **Interaction Topology** section citing this id.
- Primary Workflow must match topology (not generic CRUD).
[H5 Shell Pack — MANDATORY overrides]

- **Pack type / runtime:** read `应用类型` from task.csv:
  - `h5_shell` / `h5_flutter_shell` → **shellRuntime: flutter** (Flutter WebView 壳)
  - `h5_swift_shell` → **shellRuntime: swift** (Swift WKWebView 壳)
  - `h5_oc_shell` → **shellRuntime: oc** (Objective-C WKWebView 壳)
- **All visible UI in H5**: implement **only** routes listed in 功能文档.md **Screen Inventory**; no fixed Splash/Welcome/Legal/Plaza unless PM declares them.
- **Native shells (swift/oc):** NO Flutter project required; shell = pure iOS WKWebView + Bridge. Bridge 七维来自 **h5-native-shell-deck**（非 Flutter deck）。
- **Flutter shell:** Flutter is **container + Bridge + bundled raster assets only** (single fullscreen WebView host).
- **h5EntryUrl:** PM registers `appSlug`, `h5EntryUrl`, `h5EntryUrlDev`, `h5EntryUrlProd` in 本包登记信息.json. Prod pattern: `https://<H5_PROD_HOST>/{appSlug}/` (app name all lowercase).
- **NO** Flutter Splash/Welcome/Legal widgets; **NO** 3 native Tabs / Feed / native tool screens.
- **NO** business H5 under Flutter `pubspec.yaml` assets — site is deployed separately.
- **Legal:** MD → `sync_h5_legal_bundled.py` → `h5/src/legal/{prefix}_legal_bundled.ts`; UI → kit + `H5壳Legal弹层规范.md`.
- Read 《H5壳业务流程文字版.md》 per enabled Bridge capability.
- Read 《H5壳广场页规范.md》 — hidden `#/plaza` + Settings long-press version 3s; dev-only obvious entrance must be wrapped in `H5_PLAZA_DEV_ENTRANCE_START` / `H5_PLAZA_DEV_ENTRANCE_END` markers for deployment stripping.
- Read 《H5去风味规范.md》 — H5 ships polish baseline; AppBar `position:fixed` in H5.
- 功能文档.md MUST include **「4.2 Native Offset」** (≥3 Bridge/native capabilities).
- Read 《**H5壳功能文档深度标准.md**》 — Domain Model · Business Rules · Primary/Secondary Workflow · State Matrix · Professional Surface; tier from `skill-input/context.json`.

[PM — Business depth]
- **功能文档.md** MUST pass plan.gate `SPEC-xxx` (see BUSINESS_DEPTH_BLOCK above).
- Complexity = H5 domain rules + Bridge; **NO** login / cloud sync / native Tab business.
- **signature H5 interaction** MUST bind a Primary Workflow step (not decorative-only).

[Online-first — h5_shell]
- Shell loads **remote URL** (`h5EntryUrl`). Offline is **not** a product requirement.
- H5 business MAY use network APIs; no-network → shell Retry fallback only.
- **Raster assets** (export frames, panel PNGs for mediaServe) stay in **Flutter pubspec** asset roots.

[Flutter shell — startup splash (Programmer)]
- Read 《H5壳启动闪屏规范.md》. LaunchScreen = **1125×2436 placeholder PNG** (`launchPlaceholderAsset` → **Native imageset only**; no `h5/assets/{prefix}_launch/` copy); real launch art is out of scope.
- Cold start MUST NOT flash black between LaunchScreen and H5 splash.
- Programmer delivers: `{Prefix}FlutterViewController`, LaunchVeil (same placeholder image), VaultBoot warm-in-initState, Bridge `shellReady`, WebKit channel-before-load, **`loadRequest(h5EntryUrl)`** (NOT loadFlutterAsset).

[H5 site — startup (Implementer)]
- Implement Vue views under `h5/src/views/`; router hash mode per kit draw.
- Vite dev: `cd h5 && npm run dev` (port 5174). Deploy: pipeline `dev.h5.build` → `h5_site/{prefix}_entry.htm`.
- `boot()` / splash: double `requestAnimationFrame` then `bridge.call('shellReady',{})`.
- Implement `#/plaza` **only if** Screen Inventory lists `#/plaza` — per 《H5壳广场页规范.md》; production entry = Settings long-press version label 3s when declared.

[PM — Tab complexity]
- **功能文档.md** Screen Inventory MUST list **4–5 H5 tab-root routes** (visible bottom TabBar). PM names tabs and maps each tab to a primary module — not a fixed Prepare/Runs/Settings trio.
- Wizard steps, live session, `#/legal`, `#/plaza`, export overlays are **stack routes** — they do not count toward the 4–5 tab minimum.
- **Do NOT** encode tab names or tab count in `task.csv` `productFlow`; navigation IA lives here (Screen Inventory + Navigation Pattern + Per-screen Layout).

[PM deliverables]
- **功能文档.md:** Full depth per 《H5壳功能文档深度标准.md》 (tier in context.json) + **Screen Inventory** (PM-authored route list — sole source of required H5 pages). Flutter inventory = WebView host + error fallback + launch placeholder only.
- **本包登记信息.json:** `shellRuntime`, `packType`, `appSlug`, `h5EntryUrl`, `h5EntryUrlDev`, `h5EntryUrlProd`, `h5SiteRoot`, `h5SiteEntry`, `launchPlaceholderAsset`, `h5VaultPattern`, `h5VaultLayout`, `bridgeDeckSelections`, `bridgeCapabilities`, `kitDeckSelections` (11 kit dims from CSV).
- **bridgeDeckSelections** MUST copy all 7 Bridge CSV columns verbatim; **shellRuntime** MUST match pack type (flutter/swift/oc).
- **产包计划.md:** P2-Shell → P2-H5 (`h5/` Vite source) → **dev.h5.build** → **manual deploy gate** (upload h5_site, switch h5EntryUrl to prod).

[PM — 资源计划.md overrides for h5_shell]
- **Flutter image slots:** App Icon + **shell raster** (export frames, mediaServe PNGs under declared `assetRoots`). **Do NOT** list business UI rasters in H5 site — those reference shell assets via Bridge/mediaServe when needed.
- **H5 Site Image Slots:** list site-local SVG/icons only; large rasters prefer shell assetRoots + mediaServe.
- **H5 Site Kit Files:** when `h5VaultPattern=h5_modular_full` + `h5ScreenPattern=functional-render`, list per-screen JS under `{prefix}_panels/`.
- **H5 icon sprite list:** 8–20 `{prefix}-mark-*` symbol IDs consistent with the chosen iconography.

[PM — h5VaultPattern registration]
- 本包登记信息.json MUST include: `shellRuntime`, `packType`, `h5VaultPattern`, `h5VaultLayout`, `h5SiteRoot`, `h5SiteEntry`, `appSlug`, `h5EntryUrl*`, `kitDeckSelections` (11 cols).
- Flutter CSV 架构模式 = **Dart/Swift/OC shell only**. H5 site structure = **h5VaultPattern**.

[PM — Flutter/Swift/OC 状态/架构 vs H5 业务]
- CSV `状态管理` / `架构模式` **仅约束壳 runtime**。
- H5 业务以 **`h5StateModel` / `h5RouterPattern` / `h5ScreenPattern`** 为准。
- 功能文档.md 须含 **§H5 Architecture** 文件映射。

[PM — 视觉蓝图 Iconography override]
- For `h5_shell`: icon source = **inline SVG sprite** in h5 site. **Not** Flutter `Icons.*` for business UI.

[PM — 视觉蓝图 Ambient Canvas Canon — MANDATORY]
- Read `skill-adapt/ambient-canvas-brief.md` **before** writing 视觉蓝图.md.
- 视觉蓝图.md MUST include **§Ambient Canvas Canon** immediately after Navigation Pattern:
  - **Motif binding** — cite `heroVisualMotif`, `key_effects`, `navigationPattern` from designerDeckSelections / MASTER.
  - **Layer stack table** — Layer | DOM class | z-index | opacity rule | notes (base, mesh, grid, motif-specific SVG/div).
  - **Scene map table** — Route/screen | `data-{prefix}-scene` value | ambient-a/b/c emphasis | motif variant (≥ rows matching Screen Inventory H5 routes, min 2, max 4).
  - **CSS token table** — `--{prefix}-ambient-a` … `--{prefix}-ambient-scan` with rgba derived from color tokens.
  - **Card surface rule** — business cards/sheets use semi-opaque surfaces so canvas remains visible (anti flat-SaaS).
- 本包视觉锁.json MUST include `ambientCanvas` object (copy seed from skill-adapt/impl-ui-input.md; refine scenes to match Screen Inventory).
- H5 entry.htm MUST ship `div.u-{prefix}-ambient` per brief — reference `data/static/templates/oc_shell/.../{{PREFIX}}_entry.htm`.

[H5 Shell Bridge Deck — Native runtime, from task.csv, MANDATORY]
- shellRuntime: swift
- packType: h5_swift_shell
- webviewEngine: wkwebview_swift
- bridgeCallStyle: WKScriptMessageHandler.postMessage(JSON)
- bridgeCallbackStyle: evaluateJavaScript(callbackId(data))
- bridgeEnvelope: {action,data} minimal
- mediaServe: WKURLSchemeHandler local vault
- bridgeErrorCode: string enum (PERMISSION_DENIED)
- bridgeInjectTiming: WKUserScript atDocumentStart
Implement WKWebView + WKScriptMessageHandler Bridge exactly per these draws and H5-Bridge协议.md (native host section).

[H5 Site Structure — from programmingStyle dim-7 assetLayout — REQUIRED]
- Flutter CSV 架构模式 (MVP/MVC/…) governs **shell runtime only** (Flutter / Swift / OC).
- Deployable H5 site (NOT Flutter pubspec assets) uses **h5VaultPattern**:
  - h5VaultPattern: `h5_modular_svg` — entry + baseline.css + `{prefix}_marks.svg` (hidden symbol sprite file).
  - h5SiteRoot: `h5_site/monthio/`
  - h5SiteEntry: `index.html`
- Required site files:
  - `h5_site/foztu_entry.htm`
  - `h5_site/foztu_baseline.css`
  - `h5_site/foztu_marks.svg`
- Register `h5VaultPattern`, `h5VaultLayout`, `h5SourceRoot`, `h5SiteRoot`, `h5SiteEntry`, `h5BuildCommand`, `appSlug`, `h5EntryUrl`, `h5EntryUrlDev`, `h5EntryUrlProd` in 本包登记信息.json.
- **Forbidden**: hand-editing `h5SiteEntry` deploy file — use `h5/` + `dev.h5.build`.
- **Forbidden**: declaring `h5SiteRoot` under Flutter `pubspec.yaml` assets.

[H5 Remote Site — REQUIRED]
- Business H5 is **deployed online** (or Vite dev server during dev); **NOT** bundled in Flutter `pubspec` assets.
- **Source tree:** `h5SourceRoot` (`h5/`) — Vue 3 + Vite + vite-plugin-singlefile.
- **Deploy layout:** `h5SiteUploadRoot` + `{appSlug}/` + `h5SiteEntry` (e.g. `h5_site/temioo/index.html`).
- **`dev.h5.build`** copies Vite `dist/index.html` → `{bundleEntryPath}`.
- Shell WebView loads **hardcoded** native `h5EntryUrl` (Vite LAN during dev; change in `*HostController.m` / `*ShellConfig.swift` before release).
  - appSlug: `monthio`
  - h5SiteUploadRoot: `h5_site/`
  - h5SiteRoot: `h5_site/monthio/` (per-app deploy dir)
  - h5SiteEntry: `index.html`
  - bundleEntryPath: `h5_site/monthio/index.html`
  - h5EntryUrlDev: `http://192.168.31.102:5174/` (Vite dev — LAN IP + port 5174; run `cd h5 && npm run dev`)
  - h5EntryUrlProd: `https://test.darin.beauty/monthio/`
  - h5BuildCommand: `npm run build:deploy`
- **Raster assets** stay in Native `pubspec` / OC assets — not in remote H5 bundle.
- Manual deploy: upload `h5_site/{appSlug}/` to CDN path `/{appSlug}/`, set shell `h5EntryUrl` to prod.
- LaunchScreen placeholder: `native:Assets.xcassets/launch_placeholder.imageset/launch_placeholder.png` (1125x2436).

[H5 Micro-UI Kit — per-pack unique component library · MANDATORY]

Each `h5_shell` pack MUST ship its **own** H5 micro-UI kit — not a shared skeleton with renamed prefix.
All **11 kit/arch dimensions** below come from **task.csv** (filled by `batch task fill`). **Do NOT deviate.**

## Flutter CSV vs H5 business (read carefully)

| CSV 列 | 作用范围 |
|--------|----------|
| `状态管理` / `架构模式` | **Native 壳 ONLY**（WebView + Bridge，≤5 shell source files）；勿在壳硬套完整 MVP/MVVM |
| `h5StateModel` / `h5RouterPattern` / `h5ScreenPattern` | **H5 vault 业务** 的状态、路由、屏架构（硬约束） |

## Five layers (L0 → L4)

| Level | Content | File (modular_full) |
|-------|---------|---------------------|
| **L0 Reset** | Native-tag de-flavor overrides (§1.5) | `{prefix}_baseline.css` §reset — **包级 iron-7 `h5-deflavor.mdc` 锁定，防美化回归** |
| **L1 Tokens** | `--{prefix}-*` color/radius/spacing/type vars | `{prefix}_baseline.css` `:root` |
| **L2 Primitives** | Atoms per `kitAtomSet` + `kitCssMethodology` | `{prefix}_baseline.css` or `{prefix}_primitives.css` |
| **L3 Composites** | list-row, form-field, empty-state, hero | `{prefix}_composites.css` (optional split) |
| **L4 Screens** | entry + panels HTML using kit classes only | `{prefix}_entry.htm`, `{prefix}_panels/*.htm` |

## Kit + H5 arch deck draws (from CSV — strict)

[H5 Kit Deck — from task.csv, MANDATORY]
- kitAtomSet: list/chart/badge/panel/drawer
- kitCssMethodology: OOCSS
- kitAtomGranularity: high-level-21
- kitDomShape: text-chart-wrapper
- kitJsPattern: class-based-observer
- kitJsNamespace: {Prefix}.chart.*
- kitStorageAdapter: sqlite-wrapper
- kitMotionApproach: spring-physics
- h5StateModel: global-store
- h5RouterPattern: history-router
- h5ScreenPattern: tabbed-layout
Build per-pack micro-UI kit + H5 state/router/screen strictly per these 11 dims; see phase_h5_kit_block.txt and H5去风味规范.md §1.5–§1.9.

[Flutter CSV dims — shell scope only for h5_shell]
- 状态管理=SetState → Flutter 壳 WebView/Bridge 组织 ONLY; H5 业务状态看 h5StateModel (soft map: prefer centralized-store or imperative-dom)
- 架构模式=MVC → Flutter 壳目录 ONLY; H5 屏架构看 h5ScreenPattern/h5RouterPattern (soft map: prefer controller-view)
- Do NOT build full Flutter MVP/MVVM layers; keep shell ≤5 dart files.

### Kit interpretation (dims 1–8)

- **kitAtomSet** — exact base words for primitive class roots.
- **kitCssMethodology** — class naming format for ALL kit CSS.
- **kitAtomGranularity** — class count target (30 / 14 / 7).
- **kitDomShape** — primitive HTML skeleton.
- **kitJsPattern** — JS module organization.
- **kitJsNamespace** — `window.{Prefix}` API shape.
- **kitStorageAdapter** — local persistence style.
- **kitMotionApproach** — motion implementation.

### H5 arch interpretation (dims 9–11)

- **h5StateModel**
  - `centralized-store` — single `state` object + manual re-render
  - `observable-signals` — Proxy/getter reactive updates
  - `event-bus-driven` — pub/sub state changes
  - `per-screen-scope` — isolated closure state per screen
  - `imperative-dom` — direct DOM mutation, no state layer
- **h5RouterPattern**
  - `hash-router` — `#/route` + `hashchange`
  - `history-api` — `pushState` / `popstate`
  - `single-page-panels` — all panels in DOM, toggle `display`
  - `modal-stack` — stack overlays, no URL routing
  - `native-back-bridge` — back via Native Bridge
- **h5ScreenPattern**
  - `controller-view` — `{prefix}_panels/{screen}_controller.js` + view HTML
  - `template-clone` — `<template id="...">` + `cloneNode`
  - `component-instance` — ES class per screen, `new Screen()`
  - `functional-render` — pure fn returns HTML string → mount

## h5_modular_full + functional-render — per-screen files (HARD)

When `h5VaultPattern=h5_modular_full` **and** `h5ScreenPattern=functional-render`:

- `{prefix}_core.js` — shared helpers only (storage, bridge, router, snack, store).
- `{prefix}_panels/{prefix}_render_<slug>.js` — **one file per screen group** (≥5 files).
  Examples: `{prefix}_render_splash.js`, `{prefix}_render_welcome.js`, `{prefix}_render_settings.js`.
- **Forbidden:** single monolithic `{prefix}_render.js` containing all screens.
- `{prefix}_entry.htm` MUST `<script src=".../{prefix}_core.js">` then load each render module (or a thin bootstrap), then call `{Prefix}.ui.router.start()`.

## Forbidden

- Copying kit from **other packs**.
- Bare styled `<button>`/`<input>`/`<a>` without kit classes.
- Generic `.btn`/`.modal` without prefix/methodology.
- External UI frameworks / iconfont.
- **`onerror` / `on*` handlers that assign HTML strings** (e.g. `this.outerHTML='<span…>'`) — use `data-fallback-mark` on `<img>` + **entry.htm capture-phase** `addEventListener('error', …, true)` instead.
- **`setTimeout(boot, …)` or `*NativeReady` event boot** — call `boot()` immediately; use `bridge.call('shellReady')` after splash paints (double rAF).

## Navigation pattern (HARD — follow TOPOLOGY_BLOCK)

- Read **TOPOLOGY_BLOCK** for this pack's interaction topology (wizard / hub / tab-root / etc.).
- **Do NOT** invent a different nav model than topology + Screen Inventory.
- Tab bar, hub cards, wizard steps, and overlay routes MUST match topology contract — not a fixed template from another pack.

## Hash overlay stack (HARD — hash-router packs)

When Screen Inventory includes **Legal modal** (`#/legal`) or **filter/bottom-sheet** hash routes with `u-{prefix}-veil-*` scrim:

1. Copy **Overlay router kit** from `data/static/h5_overlay_router_kit/` into `{prefix}_core.js` router (see `H5壳Overlay路由规范.md`).
2. `dispatch` MUST render `render(base.path, base.params) + render(overlayPath, params)` — never replace root with overlay alone.
3. Track `_overlayBase` on `navigate` (non-replace); close overlay via `history.back()`.
4. `afterMount(opts)`: when `opts.stackedBase` or `opts.stackedOverlay`, skip parallax/swipe duplicate bindings.
5. Ephemeral confirms / IAP purchase barrier → `document.body` append (no hash route).

验收：`verify_h5_overlay_stack()` PASS · H5 Implementer phase HARD FAIL on violation.

## Registration

`本包登记信息.json` MUST include:
- `kitDeckSelections` — all **11** CSV kit/arch columns
- `kitJsNamespaceResolved` — e.g. `{Prefix}.ui`

## PM deliverables

- **视觉蓝图.md §Component Selection** + **§Package Token Overrides** — cross-ref `data/static/component_kit/` (semantic constraints) **and** CSV kit 11-dim (style differentiation)
- **功能文档.md §H5 Architecture** — state model, router, screen file map per draws
- **资源计划.md §H5 Vault Kit Files**

Gate soft-warns methodology, atom roots, namespace, state/router/screen patterns, cross-pack Jaccard.

[Legal Agreements — REQUIRED — pipeline gate enforced]
**READ FIRST:** `docs/法律协议规范.md` (canonical spec in this repo).
Write at workspace root in THIS phase:
1) `Monthio Privacy Agreement.md` — Privacy (协议风格3)
2) `Monthio User Agreement.md` — Terms (协议风格3)
- Style 3: Concise split chapters; ~600 English words each; ≥3 core-clause differences.
- All content in ENGLISH; no country/region-specific legal regimes;
  header date EXACTLY: Latest Updated: May 18, 2026; Age rating 18+;
  end with ## Contact Us + Monthio@gmail.com.
- Global safety copy (privacy+terms combined): Zero Tolerance; filtering methods; user reporting mechanism; action within 24 hours.
- Body: exactly one H1 (= filename); sections use ## / ###; prose only;
  NO markdown tables, lists (- * 1.), or block quotes (>).
- Privacy MUST include H2: Children's Privacy
- Terms MUST include H2: Limitation of Liability
- Self-check 法律协议规范 §7 before finishing; `verify_h5_legal_md` FAIL blocks pipeline.



---

## Deliverable 1) 功能文档.md (PM — English, no code)

**Depth standard:** Must pass plan.gate `SPEC-xxx` checks per `skill-input/context.json` → `businessDepthTier`.
Read 《H5壳功能文档深度标准.md》 before writing. Shallow headers **fail Plan gate**.

Sections in order (include all):
- **App Theme & Angle** — one paragraph grounded in CSV product flow
- **Screen Inventory** — table: **PM-authored complete H5 route list** (no pipeline-default pages; include Splash / Welcome / Legal / Plaza / Store **only when product needs them**); shell = WebView + error + launch only
- **Tab navigation (h5_shell)** — declare tab-root routes **matching `_preview/preview-canonical.md` §Tabs** when preview exists (3–5 distinct H5 tab-root routes with bottom TabBar). Examples: Plans · Rehearse · Insights · Library · Settings. **Hidden / stack routes** (`#/legal`, `#/plaza`, wizard steps, live session, export overlay) **do not** count toward the 3–5.
- **Interaction Topology** — cite assigned topology id; primary vs secondary module roles; **Explicitly NOT** (forbidden landing patterns)
- **Domain Model & Data Contract** — entity table (Entity | Fields | Type | Validation | Persistence key); count per tier
- **Business Rules Engine** — BR-01… numbered rules (trigger · logic · conflict · user feedback)
- **Primary Workflow** — numbered steps (UI action + data change + success/failure); count per tier
- **Secondary Workflows** — ≥ tier count; each ≥ tier steps (edit/archive, filter/review, etc.)
- **State & Empty Matrix** — table per main screen: Loading | Empty | Error | Permission-denied | Offline-retry (domain copy, no generic "No data")
- **Professional Surface** — Domain Glossary table + Metrics & Reports (field, definition, period) + **signature H5 interaction** bound to a Primary Workflow step
- **4.2 Native Offset** — ≥3 Bridge/native capabilities mapped to workflow steps
- **Bridge Capability Matrix** — capability | workflow step | in | out | fail UX (Bxx refs)
- **Export / Save Flow** — per content type if app produces output
- **IAP Catalog & Free Tier** — mirror `iap-catalog.generated.md`; gated actions
- **§H5 Architecture** — `h5StateModel` / `h5RouterPattern` / `h5ScreenPattern` file map
- **App Store Listing** — Subtitle, Promo, Description, Keywords (English)

[Feature Doc Lock — MANDATORY]
- **Screen Inventory is authoritative**: every route listed is **MUST implement**; routes **not** listed are out of scope — no "optional" / "may" / "可选项" wording inside the inventory.

---

## Deliverable 1b) `{全称}.md` (PM — 中文产品文档)

**Format:** MUST follow 《H5壳产品文档格式.md》 exactly (see Mockoo `Mockoo - Steady & Revise.md`).

Sections in order (include all; use `####` for top-level sections, `---` between them):
1. **H1** — `# {全称}` matching CSV `全称` column exactly
2. **产品概述 (Product Overview)** — 产品描述两段 + **差异化角度（PM Deck：`primaryUserGoal`）** + **受众与场景** + Privacy/User Agreement 链接
3. **App Store Listing** — Subtitle, Promotional Text, Description, Keywords (English)
4. **业务流程总结 (Business Flow Summary)** — Hub + 编号主线 1–8 + 跨模块闭环 ASCII + **差异化价值**
5. **审核 / 演示路线（点击版）** — 预计时长与 Tab 固定说明；演示数据导入/清空表；分阶段 Step 表；路线 ASCII；固定数据表；覆盖说明；审核 FAQ 表

Content MUST align with `功能文档.md` (same product, flows/tabs/IAP must match).

---

## Deliverable 1c) Legal agreements (English MD — HARD GATE)

Write **both** files at workspace root **in this phase** (not deferred to H5 Implementer):

- `{主名字} Privacy Agreement.md`
- `{主名字} User Agreement.md`

Follow `docs/法律协议规范.md` and the **[Legal Agreements — REQUIRED]** block above. `plan.gate` and `dev.h5.gate` call `verify_h5_legal_md()` — missing files or wrong H1/date/contact/style length **fail the batch**.

---

## Deliverable 2) 视觉蓝图.md (UI — English) — excerpt

**Depth standard:** V2 canon sections with tables — shallow headers **fail Plan gate**.

Sections in order (include all V2 gates plus H5 ambient):
- **Visual Identity** — from MASTER + design-brief
- **Anti-Patterns (AVOID)** — from MASTER §Anti-Patterns
- **Color Tokens** — table with light + dark hex
- **Typography Scale** — displayLarge … labelSmall
- **Shape & Radius System**
- **Iconography** — inline SVG sprite IDs (H5); NO Flutter Icons.*
- **Imagery**
- **Navigation Pattern** — from designerDeckSelections / MASTER
- **Ambient Canvas Canon (MANDATORY)** — expand skill-adapt/ambient-canvas-brief.md:
  - Motif binding (heroVisualMotif, key_effects, navigationPattern)
  - Layer stack table (base | mesh | grid | motif SVG/div)
  - Scene map table: Route | data-{prefix}-scene | ambient emphasis | motif variant (≥4 rows)
  - CSS token table: --{prefix}-ambient-a … --{prefix}-ambient-scan
  - Card surface rule: semi-opaque cards; canvas visible between/behind surfaces
  - Motion notes (respect prefers-reduced-motion)
- **Per-screen Layout** — EVERY screen **listed in Screen Inventory** (and only those)

> **skill.pages (h5_shell):** `design-system/*/pages/*.md` are **not** pre-seeded. After `功能文档.md` exists, pipeline runs **`reconcile_pages_from_spec`** before plan.gate to write/prune overrides matching Screen Inventory only.

- **Overlay & Feedback Specs** — table ≥4 scenarios
- **Confirmation Dialog Inventory**
- **Export Card Composition** — layer stack per export flow
- **List Row Anatomy**
- **Detail Page Pattern**
- **Modal Interior Spec**
- **Form & Input Canon** — hintStyle/style same typography token
- **Tag & Filter Chip Canon**
- **IAP Store Layout Canon** — balance hero + grid/promo (**only if** Screen Inventory includes `#/store`)
- **Welcome Gate Canon** — slot table ≥4 rows (**only if** Screen Inventory includes `#/welcome`)
- **Motion & Interaction Spec**
- **Component Selection** + **Package Token Overrides**
- **Dark Mode Adaptation**

(Full deliverable list: 功能文档.md, `{全称}.md`, 视觉蓝图.md, 本包登记信息.json, 本包视觉锁.json, 产包计划.md, 资源计划.md, legal docs — same as H5 shell batch gates.)

[Self-check — Ambient Canvas]
- §Ambient Canvas Canon present with scene table ≥4 rows + layer stack + token table?
- 本包视觉锁.json includes ambientCanvas.motifKey + ambientCanvas.scenes?
- Motif tied to heroVisualMotif — not generic flat gray SaaS background?

[Output Rule]
Write files only. Then one-line summary.