# Chip

## 组件 ID

`primitives/chip`

## 分类

`primitives`

## CSS 类（必须）

| 状态 | 类名 |
|------|------|
| 默认 | `c-{prefix}-chip` |
| 选中 | `c-{prefix}-chip c-{prefix}-chip--active` |

## 样式合同

- `min-height: 32px`，可点击
- 选中态须有 border/shadow 差异（非仅 color）
- Trends 筛选、Hub 标签等场景使用

## H5 落盘规则

- 扩展 `kit-skeleton.css` 中的 `.c-{prefix}-chip`
- 禁止 `<span onclick>` 替代 button/chip

## 导航

- [[component_kit/patterns/filter_panel]]
