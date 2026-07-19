# Welcome Gate

## 组件 ID

`patterns/welcome_gate`

## 分类

`patterns`

## 适用场景

`#/welcome` 首次引导 — narrative / carousel / dialogue 分步 onboarding。

## CSS 类（必须）

| 槽位 | 类名 |
|------|------|
| 标题 | `c-{prefix}-welcome-title` |
| Beat 文案 | `c-{prefix}-welcome-beat` |
| Trust 列表 | `c-{prefix}-welcome-trust` |
| 品牌 motif | `c-{prefix}-welcome-hex`（或蓝图指定 variant） |
| CTA | `c-{prefix}-btn` |
| 合规行 | `c-{prefix}-checkbox-row` + `c-{prefix}-checkbox` |
| 法律链接 | `c-{prefix}-link` |

## 结构合同

- 禁止一屏堆叠多 beat + trust bullet（须分步 `currentStep` / carousel）
- 合规 checkbox 仅在最终 beat
- `route meta.scene='welcome'` 或 `setScene('welcome')`
- 文字颜色继承 `page-full` + `--{prefix}-on-ambient`

## H5 落盘规则

- 读 `design-system/*/pages/welcome.md` + 视觉蓝图 §Welcome Gate Canon
- 扩展 `skill-adapt/kit-skeleton.css` welcome 段到 `kit.css`

## 导航

- [[component_kit/primitives/checkbox]]
- [[component_kit/primitives/button]]
