# Bridge Toast

## 组件 ID

`shell/bridge_toast`

## 分类

`shell`（h5_shell 专用）

## 适用包类型

| 包类型 | 使用场景 | 实现要点 |
|--------|---------|---------|
| h5_shell | Bridge 回调反馈、权限失败、mediaServe 重试 | 复用 `primitives/snackbar`；通过 Bridge 触发 |

## 变体

同 `primitives/snackbar`。

## 注意事项

1. **Bridge 调用失败 / 权限拒绝 / mediaServe 未就绪时显示**。
2. **复用 `primitives/snackbar` 变体**。
3. **禁止用 `alert()` 反馈 Bridge 结果**。
4. **mediaServe 未就绪：调用 `getDeviceInfo` 重试**（brain §6）。

## 踩坑与规避

| 坑 | 规避 |
|---|---|
| 权限拒绝无反馈 | Bridge 回调须 snackbar 提示（brain §6） |
| Bridge 失败用 `alert()` | 改 snackbar；alert 被禁 |
| mediaServe 未就绪直接失败 | `getDeviceInfo` 重试 + snackbar |
| 多屏复制 Bridge toast 逻辑 | 统一走 `shell/bridge_toast` |
| snackbar 变体与语义不匹配 | 失败→failure，权限→warning/info |

## 落盘规则

- Flutter：壳侧不实现（H5 触发）
- H5：复用 `c-{prefix}-snackbar--{variant}`

## 依赖

- 引用：`primitives/snackbar`
- 规格：《H5-Bridge协议.md》《H5壳业务流程文字版.md》
- brain：`h5-deflavor-interaction-pitfalls` §6

## 实现过程（思路，无代码）

1. Bridge 回调失败 → 触发 snackbar；
2. mediaServe 未就绪 → 重试 + snackbar。

## 组件自身需要去风味的点

- 见 `primitives/snackbar`。

## 导航

- [[component_kit/primitives/snackbar]]
