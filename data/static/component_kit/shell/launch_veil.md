# Launch Veil

## 组件 ID

`shell/launch_veil`

## 分类

`shell`（h5_shell 专用）

## 适用包类型

| 包类型 | 使用场景 | 实现要点 |
|--------|---------|---------|
| h5_shell | 冷启动闪屏交接 | LaunchScreen → shellReady → LaunchVeil 淡出 |

## 变体

无；壳侧单一闪屏交接。

## 注意事项

1. **时序**：LaunchScreen（iOS）→ WebView load → `shellReady` → LaunchVeil 淡出。
2. **禁止**：Flutter Splash Widget（h5_shell 全 H5）。
3. 详细时序与 Flutter/H5 分工见《H5壳启动闪屏规范.md》。

## 依赖

- 规格：《H5壳启动闪屏规范.md》《H5壳Flutter产品要求.md》
- baseline：见 Flutter §Flutter
- brain：`h5-shell-启动闪屏时序-pitfalls`

## Flutter 落盘规则

- 壳侧 LaunchScreen.storyboard；无 Flutter Splash Widget

## H5 落盘规则

- H5 侧 LaunchVeil DOM；shellReady 后 CSS opacity 淡出

## 实现过程（思路，无代码）

1. iOS LaunchScreen；
2. WebView load 完成触发 shellReady；
3. LaunchVeil 淡出。

## 组件自身需要去风味的点

- 无特殊（时序控制）。

## 导航

- [[component_kit/shell/webview_host]]
- [H5壳启动闪屏规范](../../../../docs/H5壳启动闪屏规范.md)
- 全局大脑：`h5-shell-启动闪屏时序-pitfalls-20260707`
