# Permission Gate

## 组件 ID

`shell/permission_gate`

## 分类

`shell`

## 适用包类型

| 包类型 | 使用场景 | 实现要点 |
|--------|---------|---------|
| flutter_tool | 相机/麦克风/相册权限拒绝反馈 | error_state + 单行 `OK` 弹窗 |
| h5_shell | Bridge 权限拒绝反馈 | snackbar + 重试 |
| flutter_contentpack | 录音/相册权限 | 同 flutter_tool |

## 变体

| 变体 | 说明 |
|------|------|
| `denied` | 权限拒绝提示 + `OK` |
| `blocked` | 权限被禁 + `OK` |
| `request` | 首次请求引导 |

## 注意事项

1. **error_state 引用 `feedback/error_state`**。
2. **CTA 引用 `primitives/button` secondary**；Flutter 权限被拒弹窗**仅一个 `OK` 按钮**，**禁止**「Open Settings / 去设置」跳转。
3. **H5：Bridge 权限回调失败 → snackbar + 重试**（brain §6）。
4. **固定英文文案**：`No camera permission`、`No photos permission`、`No microphone permission`、`Camera unavailable`。
5. **禁止静默失败**：必须给反馈。
6. Flutter 显式请求顺序与 Podfile 宏见《工具包Flutter产品要求.md》§7。

## 踩坑与规避

| 坑 | 规避 |
|---|---|
| 权限拒绝无反馈 | 须 snackbar / error_state 提示（brain §6） |
| 弹窗带「去设置」按钮 | 按产品要求只保留一个 `OK` 按钮 |
| blocked 态仍显示 request | 按状态分支：denied/blocked/request |
| Flutter 未封装 error_state | 引用 `feedback/error_state` + `OK` CTA |
| 文案与产品要求不一致 | 统一使用 `No camera/photos/microphone permission` |
| 多屏复制私有 PermissionGate | 统一放 `shared/{Prefix}PermissionGate.dart` |

## 落盘规则

- Flutter：`{architectureFolders.views}/shared/{Prefix}PermissionGate.dart`
- H5：`c-{prefix}-permission`；error_state + CTA

## 依赖

- 引用：`feedback/error_state`、`primitives/button`、`shell/bridge_toast`
- brain：`h5-deflavor-interaction-pitfalls` §6

## 实现过程（思路，无代码）

1. 检测权限状态；
2. denied/blocked 显示 error_state + 单行 `OK`；
3. H5 Bridge 回调失败 → bridge_toast。

## 组件自身需要去风味的点

- 无特殊（依赖组件已处理）。

## 导航

- [[component_kit/feedback/error_state]]
- [[component_kit/shell/bridge_toast]]
- [工具包Flutter产品要求 §7](../../../../docs/工具包Flutter产品要求.md)
