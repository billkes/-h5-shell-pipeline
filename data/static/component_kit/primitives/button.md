# Button

## 组件 ID

`primitives/button`

## 分类

`primitives`

## CSS 类（必须）

| 元素 | 类名 | 说明 |
|------|------|------|
| Primary CTA | `c-{prefix}-btn` | 主按钮 |
| Secondary | `c-{prefix}-btn c-{prefix}-btn--secondary` | 次要操作 |
| Destructive | `c-{prefix}-btn c-{prefix}-btn--destructive` | 删除/危险 |

## 样式合同

- `min-height: 44px`
- 颜色/圆角/阴影来自 `--{prefix}-*` token + `skill-adapt/kit-skeleton.css`
- `:disabled` 须降 opacity 并阻断点击
- 禁止裸 `<button>` 无 class

## H5 落盘规则

- 骨架：`skill-adapt/kit-skeleton.css` → 扩展为 `h5/src/styles/kit.css`
- Vue：`<button type="button" class="c-{prefix}-btn">`

## 去风味

- 不用浏览器默认 button 外观
- `:active` 用 mechanical press（Bauhaus 包豪斯：`translate` + shadow collapse）

## 导航

- [[component_kit/primitives/input]]
- [[component_kit/patterns/welcome_gate]]
