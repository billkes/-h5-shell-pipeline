# Snackbar

## 组件 ID

`primitives/snackbar`

## 分类

`primitives`

## CSS 类（必须）

| 元素 | 类名 |
|------|------|
| Toast 条 | `c-{prefix}-snackbar` |

## 样式合同

- `position: fixed`，高于 TabBar（`z-index: 60`）
- 底部 inset 避开 `--{prefix}-page-inset-bottom`
- 文案 14px，对比度 ≥ 4.5:1

## H5 落盘规则

- 由 `SnackbarHost.vue` 统一渲染
- 禁止 `alert()` / 原生 toast

## 导航

- [[component_kit/feedback/error_state]]
