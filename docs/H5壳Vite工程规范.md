# H5 壳 Vite 工程规范

> **无仓库代码模板。** 流水线不拷贝 `data/static/templates/h5_vite`。  
> Agent 按本文 + **ui-ux-pro-max skill 产物** + `功能文档.md` **从零创建** `h5/`。  
> **两阶段**：先 `_preview/pages/*.html`（HTML+Tailwind 视觉契约）→ 再移植进本工程；细则见《H5壳ui-ux-pro-max使用规范.md》§8。

## 技能统一栈（唯一 UI 标准）

| 维度 | skill 来源 | H5 落地 |
|------|-----------|---------|
| 架构 | `design-system/*/stack-vue.md` | Vue 3 + Composition API + `vue-router` |
| 样式 | `design-system/*/stack-html-tailwind.md` | Tailwind CSS（theme 接 tokens） |
| 字体 | `MASTER.md` · `typography-brief.md` | Google Fonts `@import` |
| 图标 | `icon-brief.md` · `skill-adapt/icon-manifest.json` | `@phosphor-icons/vue` |
| Token | `skill-adapt/design-tokens.css` | Tailwind theme / `:root` |
| 部署 | `h5-runtime.md`（流水线） | vite-plugin-singlefile → `h5_site/` |
| 视觉预览契约 | Agent 写 `_preview/pages/*.html` | **不**部署；供移植对照 |

**禁止**另起手写 CSS 体系或 inline SVG sprite kit 与 skill 双轨并行。

## 职责边界

| 谁 | 做什么 |
|----|--------|
| skill.design / enrich / adapt / tokens | UI 标准（栈、色、字、图标、token） |
| Agent 阶段 A | Screen Inventory → `_preview/pages/*.html` + INDEX + FREEZE |
| Agent 阶段 B | 创建完整 `h5/`，按冻结 HTML 移植 + 补 Bridge/业务 |
| 流水线 | `sync_h5_legal_bundled`、theme/layout contract、`dev.h5.build`、`preview.tabs` |
| Gate | Bridge / Legal / 审核红线；验 `h5/` / `h5_site`；**不**把 `_preview/pages` 当部署入口 |

## 工程骨架（Agent 自建）

```
h5/
├── package.json          # vue · vue-router · vite · vite-plugin-singlefile · tailwindcss · @phosphor-icons/vue
├── vite.config.ts        # build → ../h5_site/{appSlug}/index.html；dev port 5174；host: true
├── tailwind.config.*     # theme.extend.colors ← design-tokens / MASTER
├── index.html
├── tsconfig.json
├── scripts/              # build:deploy
└── src/
    ├── main.ts
    ├── App.vue
    ├── router/
    ├── views/
    ├── components/
    ├── bridge/
    ├── lib/
    ├── styles/           # @tailwind base/components/utilities + tokens import
    ├── legal/{prefix}_legal_bundled.ts
    └── store/
```

### package.json 约定

- `dev`: `vite --host`
- `build` / `build:deploy`: 单文件产物到 `h5_site/{appSlug}/index.html`（vite-plugin-singlefile；禁止拆 css/js/htm）
- 依赖至少：`vue`、`vue-router`、`vite`、`vite-plugin-singlefile`、`tailwindcss`、`@phosphor-icons/vue`

### vite.config.ts 约定

- `server.host: true`，端口 **5174**
- 单文件打包输出到 `../h5_site/{appSlug}/index.html`（`appSlug` = 应用名小写；入口文件名固定 `index.html`）
- **禁止** `{prefix}_entry.htm`、外挂 `.css` / `.js` 部署树、或 `h5_modular_*` 产物形态

## 实现原则

1. **无仓库页面模板**：不从仓内拷贝业务 Vue；视觉先落 `_preview/pages`，再移植。
2. **规范真相源**：
   - 栈：`stack-vue.md` · `stack-html-tailwind.md`
   - 每页文案/IA：`design-system/{app}/pages/*.md`
   - 每页视觉契约（冻结后）：`_preview/pages/*.html`
   - Legal / Plaza / Overlay：《H5壳Legal弹层规范.md》· 《H5壳广场页规范.md》· 《H5壳Overlay路由规范.md》
3. **双阶段真源**：冻结前 HTML 钉视觉；冻结后至交付以 `h5/` 为唯一实现真源（见使用规范 §8.4）。
4. **合规靠 gate**：Welcome / Legal / Plaza / layout contract 等运行时约束。

## 两阶段目录约定

```text
_preview/pages/
├── INDEX.md       # 路由 ↔ html ↔ MUST/SHOULD/MAY
├── FREEZE.md      # 开始写 h5/ 前必写
├── welcome.html
├── hub.html
└── …
h5/                # 阶段 B：唯一可 build 工程
```

- MUST：Welcome、Tab1/Hub、Primary Export/工作流面（Inventory 有则做）  
- SHOULD：其他 tab-root  
- MAY：stack 子页；Legal/Plaza 不强制精美 HTML  
- 与 `{slug}-tabs-preview.html` / `preview-canonical.md` **共存**：后者管 Tab 总览与色板；前者管单屏密度  

## Browser Bridge mock（Vite DEV · 必做）

浏览器无壳时，媒体 / 权限 Bridge **不得**用 `reject('Bridge unavailable')` 打断业务流程。

| 项 | 约定 |
|----|------|
| 真相源 snippet | `data/static/h5_snippets/bridge/browserMock.ts` |
| 落地路径 | `h5/src/bridge/browserMock.ts`（替换 `{{APP_NAME_LOWER}}`） |
| 接线 | 无 native handler 时 `tryBrowserBridgeMock(action, payload)` → **resolve** 假 path / granted |
| 显图 | `getBrowserMockDisplayUrl(path)` 优先于 custom scheme |
| 壳内 | `isNativeShellPresent()` 为 true 时 **不走** mock |
| 真机 | 仍用 Plaza 验权；mock 不替代真机验收 |
| 禁止 | 业务页裸写 `<input type="file">`（选文件只许在 browserMock 内） |

流水线：`ensure_h5_vite_scaffold` 在已有 `h5/` 上会拷贝 snippet，并尽量把历史 `Bridge unavailable` reject 改成 mock 调用。

## Legal body 格式（行为约束）

`formatLegalBody(raw, prefix)` 须产出 section / para / meta 结构；gate 只检渲染结果。

## 禁止

- 依赖仓库内 H5 Vue/CSS 代码模板目录
- 手改 `h5_site/` 部署产物
- 把业务 H5 打进 Native assets
- iconfont / Font Awesome / Material Icons（与 skill Phosphor 冲突）

## 导航

- 相关（产包工作区内）：《H5壳ui-ux-pro-max使用规范.md》· 《H5壳H5实现检查清单.md》· 《H5壳Legal弹层规范.md》· 《H5壳广场页规范.md》· 《H5壳Overlay路由规范.md》· 《H5壳Pack约束.md》
- 流水线仓规则（`docs/rules/`）**勿**作为产包 Agent 必读路径。
