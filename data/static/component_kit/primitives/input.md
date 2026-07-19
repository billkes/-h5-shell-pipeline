# Input

## 组件 ID

`primitives/input`

## 分类

`primitives`

## CSS 类（必须）

| 元素 | 类名 |
|------|------|
| 文本输入 | `c-{prefix}-input` |

## 样式合同

- `min-height: 44px`，`font-size: 16px`（防 iOS zoom）
- 背景/边框/文字用 `--{prefix}-background|border|foreground`
- 禁止裸 `<input>` / `<textarea>` 无 class（checkbox 除外，走 checkbox 组件）

## H5 落盘规则

- 骨架见 `skill-adapt/kit-skeleton.css`
- 表单页须 `@focus-visible` outline（ux-checklist）

## 去风味

- `appearance: none` + 自定义 border/radius
- 禁止浏览器默认 inset shadow

## 导航

- [[component_kit/primitives/checkbox]]
- [[component_kit/primitives/button]]
