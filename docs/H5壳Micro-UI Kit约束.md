# H5 Micro-UI Kit 约束

每包须独立 micro-UI kit。**11 维 kit/arch 抽牌**存于 `本包登记信息.json` → `kitDeckSelections`（来自 task.csv，勿偏离）。

## Flutter CSV vs H5 业务

| CSV 列 | 作用范围 |
|--------|----------|
| `状态管理` / `架构模式` | **Native 壳 ONLY** |
| `h5StateModel` / `h5RouterPattern` / `h5ScreenPattern` | **H5 业务** |

## 五层 L0–L4

| Level | 内容 |
|-------|------|
| L0 Reset | de-flavor overrides · `{prefix}_baseline.css` |
| L1 Tokens | `--{prefix}-*` |
| L2 Primitives | kitAtomSet + kitCssMethodology |
| L3 Composites | list-row, form-field, empty-state, hero |
| L4 Screens | entry + panels |

## 维度释义

- **kitAtomSet** — primitive class 词根
- **kitCssMethodology** — 全部 kit CSS 命名
- **kitAtomGranularity** — class 数量目标
- **kitDomShape** / **kitJsPattern** / **kitJsNamespace** / **kitStorageAdapter** / **kitMotionApproach**
- **h5StateModel** — centralized-store · observable-signals · event-bus-driven · per-screen-scope · imperative-dom
- **h5RouterPattern** — hash-router · history-api · single-page-panels · modal-stack · native-back-bridge
- **h5ScreenPattern** — controller-view · template-clone · component-instance · functional-render

## h5_modular_full + functional-render

`{prefix}_core.js` + `{prefix}_panels/{prefix}_render_<slug>.js`（每屏组一文件，≥5）；禁止单体 `{prefix}_render.js`。

## 禁止

- 复制其他包 kit · 裸 `<button>`/`<input>` · 通用 `.btn`/`.modal` · 外部 UI 框架/iconfont
- img `onerror` 写 HTML — 用 `data-fallback-mark` + capture-phase listener
- `setTimeout(boot)` / `*NativeReady` 启动 — 双 rAF 后 `shellReady`

## Overlay stack

Legal/filter hash overlay：见《H5壳Overlay路由规范.md》· `data/static/h5_overlay_router_kit/`。

## 登记

`本包登记信息.json`：`kitDeckSelections`（11 列）、`kitJsNamespaceResolved`。

## PM 交叉引用

- `视觉蓝图.md` §Component Selection · §Package Token Overrides
- `data/static/component_kit/` 语义约束
- `功能文档.md` §H5 Architecture

Gate 对 methodology、atom、namespace、state/router/screen 做软警告及跨包 Jaccard。
