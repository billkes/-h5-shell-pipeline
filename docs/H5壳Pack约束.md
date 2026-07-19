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

`h5/src/views/`；hash router；`dev.h5.build` → `h5_site/{prefix}_entry.htm`；splash 双 rAF 后 `shellReady`。

## 关联规范

- 《H5壳业务流程文字版.md》— 按 Bridge 能力阅读
- 《H5壳广场页规范.md》— `#/plaza`（若在 Inventory）
- 《H5去风味规范.md》
- Legal UI：《H5壳Legal弹层规范.md》；内容 `sync_h5_legal_bundled.py`
- Vault：《H5壳Vault合规维护规范.md》
- Bridge：《H5-Bridge协议.md》

## CSV 维度边界

命名 > 架构 > 状态管理 > 编程人设。Flutter CSV `状态管理`/`架构模式` **仅约束壳**；H5 业务以 `h5StateModel` / `h5RouterPattern` / `h5ScreenPattern` 为准（见《H5壳Micro-UI Kit约束.md》）。
