# Checkbox

## 组件 ID

`primitives/checkbox`

## 分类

`primitives`

## CSS 类（必须）

| 元素 | 类名 | 说明 |
|------|------|------|
| 行容器 | `c-{prefix}-checkbox-row` | label 包裹 checkbox + 文案 |
| 控件 | `c-{prefix}-checkbox` | `<input type="checkbox">` |

## 样式合同

- 行 `min-height: 44px`
- checkbox 尺寸 ≥ 20×20px，`accent-color: var(--{prefix}-accent)`
- 合规文案 ≥ 14px（labelMedium）
- 禁止裸 `<input type="checkbox">` 无 class

## H5 落盘规则

```html
<label class="c-{prefix}-checkbox-row">
  <input v-model="checked" type="checkbox" class="c-{prefix}-checkbox" />
  <span>I am 18 years or older</span>
</label>
```

Welcome 页须 18+ + Privacy/User 两个 checkbox。

## 去风味

- `global.css` 的 `appearance: none` 须排除 checkbox/radio
- 禁止 inline `style` 替代 kit 类

## 导航

- [[component_kit/patterns/welcome_gate]]
- [[component_kit/primitives/button]]
