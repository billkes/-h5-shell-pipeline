# Webview Host

## 组件 ID

`shell/webview_host`

## 分类

`shell`（h5_shell 专用）

## 适用包类型

| 包类型 | 使用场景 | 实现要点 |
|--------|---------|---------|
| h5_shell | Flutter 壳主 WebView 容器 | 单 host；冷启动 `loadRequest(h5EntryUrl)` |

## 变体

无；壳侧单一 host。

## 注意事项

1. **单 host**：冷启动 fullscreen WebView 加载 `h5EntryUrl`。
2. **Launch 续接**：占位图 + LaunchVeil 直至 `shellReady`。
3. **禁止**：Flutter Splash / Welcome / Tab bar / Legal Widget（全在 H5）。
4. 详细 WebView 约束见《H5壳Flutter产品要求.md》§3 与《H5壳Flutter交付自检清单.md》§1。

## 踩坑与规避

| 坑 | 规避 |
|---|---|
| input 聚焦无键盘 | 检查是否误设 `isTextInteractionEnabled=false` |
| 首屏白屏很久 | 检查 `h5EntryUrl` 可达性；Veil 应盖住直至 `shellReady` |
| CDN prod 真机 Load timeout / -999 | monolith ~450KB 蜂窝慢；须 `mainFrameDidFinish` + 30s/8s + 忽略 -999（见 `native_dev_network` gate） |
| WebView 缩放导致双击放大镜 | Flutter `enableZoom(false)` + H5 CSS |
| 底部 accessory 灰条 | 壳 swizzle `inputAccessoryView` → nil |
| 加载失败无重试 | 英文 Retry 触发重新 `loadRequest` |

## 落盘规则

- Flutter：壳侧 `Runner/` 或 `{Prefix}WebView`；不在 lib 业务层
- 从 `本包登记信息.json` 读取 `h5EntryUrl` / `appSlug`
- H5：业务站点在 `h5SiteRoot`，**不**列入 pubspec assets

## 依赖

- 规格：《H5壳Flutter产品要求.md》《H5壳Flutter交付自检清单.md》《H5壳启动闪屏规范.md》
- baseline：见 Flutter §Flutter
- brain：`h5-wkwebview-双击放大镜-pitfalls`、`h5-shell-启动闪屏时序`

## 实现过程（思路，无代码）

1. 冷启动 LaunchVeil 下 `loadRequest(h5EntryUrl)`；
2. 配置 WKWebView（enableZoom false、accessory swizzle）；
3. Bridge 注入；
4. 处理 `shellReady` 撤 Veil。

## 组件自身需要去风味的点

- 禁 `isTextInteractionEnabled=false`；
- accessory swizzle 需 rebuild iOS。

## 导航

- [[component_kit/baseline]]
- [H5壳Flutter产品要求](../../../../docs/H5壳Flutter产品要求.md)
- [H5壳Flutter交付自检清单](../../../../docs/H5壳Flutter交付自检清单.md)
- 全局大脑：`h5-wkwebview-双击放大镜-pitfalls-20260707`
