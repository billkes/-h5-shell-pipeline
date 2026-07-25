# H5 壳 Pack 约束（Plan / Shell / H5 共用）

CSV 抽牌结果写入 `本包登记信息.json` / `本包代码组合.json`；本文为自然语言规范，prompt 仅指向本文件。

## Pack type / runtime

| task.csv 应用类型 | shellRuntime |
|-------------------|--------------|
| h5_shell / h5_flutter_shell | flutter |
| h5_swift_shell | swift |
| h5_oc_shell | oc |

- **可见 UI 均在 H5**：仅实现 `功能文档.md` **Screen Inventory** 中的路由。
- **Native（swift/oc）：** 纯 WKWebView + Bridge；Bridge 七维来自 h5-native-shell-deck。
- **Flutter 壳：** 容器 + Bridge + shell raster assets；单 WebView host。
- **禁止** Flutter Splash/Welcome/Legal/原生 Tab 业务屏。
- **禁止** 把业务 H5 打进 Flutter `pubspec.yaml` assets。

## h5EntryUrl

PM 在 `本包登记信息.json` 登记 `appSlug`、`h5EntryUrl`、`h5EntryUrlDev`、`h5EntryUrlProd`。Prod：`https://<H5_PROD_HOST>/{appSlug}/`（小写）。

## Online-first

Shell 加载远程 URL；离线非产品需求。Raster（export frames、mediaServe PNG）留在 **Flutter pubspec** asset roots。

## 功能文档深度

《H5壳功能文档深度标准.md》；tier 见 `skill-input/context.json`。须含 **4.2 Native Offset**（≥3 Bridge 能力）。signature H5 interaction 须绑定 Primary Workflow。

## Tab 复杂度（PM）

Screen Inventory：**4–5 个 H5 tab-root**（bottom TabBar）；wizard、`#/legal`、`#/plaza` 等为 stack 路由，不计入 4–5。

## Flutter 壳启动（Programmer）

《H5壳启动闪屏规范.md》：LaunchScreen/LaunchVeil **1125×2436 placeholder**；`loadRequest(h5EntryUrl)`；Bridge `shellReady`。

## H5 启动（Implementer）

`h5/src/views/`；hash router；`dev.h5.build` → `h5_site/{appSlug}/index.html`；splash 双 rAF 后 `shellReady`。

## 关联规范

- 《H5壳业务流程文字版.md》— 按 Bridge 能力阅读
- 《H5壳广场页规范.md》— `#/plaza`（若在 Inventory）
- 《H5去风味规范.md》
- Legal UI：《H5壳Legal弹层规范.md》；内容《法律协议规范.md》；**产包后协议主路径见下节「产包后共性」**
- Vault：《H5壳Vault合规维护规范.md》
- Bridge：《H5-Bridge协议.md》
- 产包后加工 checklist：**流水线仓 / 加工侧**维护，不在产包 Agent 封闭语料内。

---

## 产包后共性（20260721）

> 产包兜底只保证能跑；**加工收尾**须过下列共性。细则落对应规范 + 加工 checklist 编组，禁止旁路另开一轮。

| # | 共性 | 规范落点 | 加工编组 |
|---|------|----------|----------|
| 1 | 启动图首次冷启动无缩小弹回 | 《H5壳启动闪屏规范》· Swift/OC §启动；真图优先由 task「真图」+ `agent.assets` 写入 | **A** |
| 2 | 协议：有 HTTPS 则系统浏览器外开，否则 bundled 弹层 | 《H5壳Legal弹层规范》· 《H5-Bridge协议》B07 | **D** |
| 3 | Seed / 品牌图在 **iOS 工程内**真图齐全 | 《H5壳Vault合规维护规范》；壳六槽（logo/launch×2/bg×2/retry）由「真图」列控制 | **I**（联 **A/H**） |
| 4 | 录音可回放；麦克风权限可走通 | 《H5-Bridge协议》B03/B04 · 《H5去风味规范》 | **E**+**F** |
| 5 | 列表/Sheet 不贴 Dock；弹窗有安全区 | 《H5去风味规范》safe-area | **E** |
| 6 | 主题 motif 一眼贴合；Tab1 有亮点 | 《H5壳Plan交付规范》视觉锁 | **L** |
| 7 | Welcome 非模板；关键交互可见 | 《H5壳Plan交付规范》Welcome | **D** |
| 8 | 导出 = 预览（同构图同比例） | 《H5壳Plan交付规范》Export | **L** |
| 9 | 权限 plist key ↔ H5/Bridge 入口对齐 | 《H5壳Swift实现规范》§权限 · 同 OC | **F** |
| 10 | 主 Tab 内容收敛、间距有章法 | 《H5壳Plan交付规范》· 视觉锁 | **L** |

产包后共性条目来自多包加工复盘；细节由加工侧维护，产包 Agent 以本表 + 上表规范落点为准。

## CSV 维度边界

命名 > 架构 > 状态管理 > 编程人设。Flutter CSV `状态管理`/`架构模式` **仅约束壳**；H5 业务以 `h5StateModel` / `h5RouterPattern` / `h5ScreenPattern` 为准（见《H5壳Micro-UI Kit约束.md》）。
