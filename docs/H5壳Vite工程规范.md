# H5 壳 Vite 工程规范

> **无仓库代码模板。** 流水线不拷贝 `data/static/templates/h5_vite`。  
> Agent 按本文 + **ui-ux-pro-max skill 产物** + `功能文档.md` **从零创建** `h5/`。

## 技能统一栈（唯一 UI 标准）

| 维度 | skill 来源 | H5 落地 |
|------|-----------|---------|
| 架构 | `design-system/*/stack-vue.md` | Vue 3 + Composition API + `vue-router` |
| 样式 | `design-system/*/stack-html-tailwind.md` | Tailwind CSS（theme 接 tokens） |
| 字体 | `MASTER.md` · `typography-brief.md` | Google Fonts `@import` |
| 图标 | `icon-brief.md` · `skill-adapt/icon-manifest.json` | `@phosphor-icons/vue` |
| Token | `skill-adapt/design-tokens.css` | Tailwind theme / `:root` |
| 部署 | `h5-runtime.md`（流水线） | vite-plugin-singlefile → `h5_site/` |

**禁止**另起手写 CSS 体系或 inline SVG sprite kit 与 skill 双轨并行。

## 职责边界

| 谁 | 做什么 |
|----|--------|
| skill.design / enrich / adapt / tokens | UI 标准（栈、色、字、图标、token） |
| Agent | 创建完整 `h5/`（工具链 + `src/` + 业务 UI） |
| 流水线 | `sync_h5_legal_bundled`、theme/layout contract、`dev.h5.build` |
| Gate | Bridge / Legal / 审核红线；**不**禁止 Phosphor / Tailwind |

## 工程骨架（Agent 自建）

```
h5/
├── package.json          # vue · vue-router · vite · vite-plugin-singlefile · tailwindcss · @phosphor-icons/vue
├── vite.config.ts        # build → ../h5_site/{prefix}_entry.htm；dev port 5174；host: true
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
- `build` / `build:deploy`: 单文件产物到 `h5_site/`，入口对齐 `本包登记信息.json`
- 依赖至少：`vue`、`vue-router`、`vite`、`vite-plugin-singlefile`、`tailwindcss`、`@phosphor-icons/vue`

### vite.config.ts 约定

- `server.host: true`，端口 **5174**
- 单文件打包输出到约定的 `h5_site` 路径

## 实现原则

1. **无页面模板**：业务 Vue/Tailwind 由 Agent 按 `pages/*.md` 自写。
2. **规范真相源**：
   - 栈：`stack-vue.md` · `stack-html-tailwind.md`
   - 每页：`design-system/{app}/pages/*.md`
   - Legal / Plaza / Overlay：`docs/H5壳*.md`
3. **合规靠 gate**：Welcome / Legal / Plaza / layout contract 等运行时约束。

## Legal body 格式（行为约束）

`formatLegalBody(raw, prefix)` 须产出 section / para / meta 结构；gate 只检渲染结果。

## 禁止

- 依赖仓库内 H5 Vue/CSS 代码模板目录
- 手改 `h5_site/` 部署产物
- 把业务 H5 打进 Native assets
- iconfont / Font Awesome / Material Icons（与 skill Phosphor 冲突）

## 导航

- 上级：[[docs/rules/H5壳包开发规则]]
- 相关：[[docs/H5壳Legal弹层规范]] · [[docs/H5壳广场页规范]] · [[docs/H5壳Overlay路由规范]]
