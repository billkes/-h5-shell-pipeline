# H5 壳 Vite 工程规范

> **无仓库代码模板。** 流水线不拷贝 `data/static/templates/h5_vite`。  
> Agent 按本文 + 包内 `design-system/*/pages/*.md`、`功能文档.md`、`docs/H5壳*.md` **从零创建** `h5/`。

## 职责边界

| 谁 | 做什么 |
|----|--------|
| Agent | 创建完整 `h5/`（工具链 + `src/` + 全部业务 UI） |
| 流水线 | `sync_h5_legal_bundled`、theme/layout contract、`dev.h5.build`、`dev.h5.gate` |
| Gate | 行为/结构硬检；**不要求**文件长得像旧模板 |

## 工程骨架（Agent 自建）

目录建议（可按包调整，但须满足 gate）：

```
h5/
├── package.json          # vue、vue-router、vite、vite-plugin-singlefile
├── vite.config.ts        # build → ../h5_site/{prefix}_entry.htm；dev port 5174；host: true
├── index.html
├── tsconfig.json
├── scripts/              # 部署拷贝到 h5_site 的脚本（build:deploy）
└── src/
    ├── main.ts
    ├── App.vue
    ├── router/
    ├── views/
    ├── components/       # TopBar / TabBar / LegalOverlay / MediaSourceSheet 等按需自写
    ├── bridge/
    ├── lib/
    ├── styles/global.css
    ├── legal/{prefix}_legal_bundled.ts   # 由 sync_h5_legal_bundled 生成，勿手改正文
    └── store/
```

### package.json 约定

- `dev`: `vite --host`（或等价，暴露 LAN）
- `build` / `build:deploy`: Vite 单文件产物落到 `h5_site/`，入口名与 `本包登记信息.json` 的 `h5SiteEntry` / prefix 一致
- 依赖：`vue`、`vue-router`、`vite`、`vite-plugin-singlefile`（或等价单文件方案）

### vite.config.ts 约定

- `server.host: true`，端口 **5174**
- 单文件打包输出到仓库约定的 `h5_site` 路径
- Legal MD 热同步可选用仓库脚本约定；亦可依赖流水线 `sync_h5_legal_bundled`

## 实现原则

1. **无页面模板**：Hub / List / Settings / Welcome / Plaza / Legal 的 Vue/CSS 全部 Agent 自写。
2. **规范文档为唯一自然语言真相源**：
   - 每页：`design-system/{app}/pages/*.md`
   - Legal：`docs/H5壳Legal弹层规范.md`（无 `h5_legal_kit`）
   - Plaza：`docs/H5壳广场页规范.md`
   - Overlay：`docs/H5壳Overlay路由规范.md`
   - 总则：`docs/rules/H5壳包开发规则.md`
3. **Prompt 只列路径**（`${PAGE_OVERRIDES_BLOCK}`），不内联细则。
4. **合规靠 gate**：Welcome Canon、Legal UI、Plaza SKU `311400`、UX font-size、layout contract 等。

## Legal body 格式（行为约束，非模板文件）

`formatLegalBody(raw, prefix)` 须产出：

- `title` = 首行
- body：按空行分块；短标题块 → `h2.c-{prefix}-legal-section`；段落 → `p.c-{prefix}-legal-para`
- 可选 `Latest Updated:` 行 → `p.c-{prefix}-legal-meta`
- HTML 转义；禁止整段 `<br>` dump

实现可放在 `h5/src/lib/formatLegalBody.ts` 或内联组件，gate 只检渲染结果。

## Default seed（编组 I）

当功能文档要求首发数据：Agent 自写 `defaultSeed.ts`（`ensureBootstrapData`）、Settings 清数据逻辑、main 启动引导。流水线**不**注入 stub 模板。

## 禁止

- 依赖仓库内 H5 Vue/CSS 代码模板目录
- 手改 `h5_site/` 部署产物
- 把 H5 站点打进 Native `pubspec` / Xcode 资源（除登记的 SeedBundle 光栅）

## 导航

- 上级：[[docs/rules/H5壳包开发规则]]
- 相关：[[docs/H5壳Legal弹层规范]] · [[docs/H5壳广场页规范]] · [[docs/H5壳Overlay路由规范]]
