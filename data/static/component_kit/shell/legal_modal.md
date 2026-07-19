# Legal Modal

## 组件 ID

`shell/legal_modal`

## 分类

`shell`（h5_shell 专用）

## 适用包类型

| 包类型 | 使用场景 | 实现要点 |
|--------|---------|---------|
| h5_shell | Legal / Privacy / Terms 弹层 | Agent 自建 UI；禁 web 滚动条；禁 `<br>` dump |

## 变体

无固定视觉变体 — 跟本包设计系统差异化。

## 注意事项

1. **无代码 kit** — 不复制 snippet；读《H5壳Legal弹层规范.md》。
2. 内容由 `sync_h5_legal_bundled.py` → `{prefix}_legal_bundled.ts` / `.js`。
3. 视觉跟 `design-system/*/pages` + 视觉蓝图，避免批次同质化。

## 踩坑与规避

| 坑 | 规避 |
|---|---|
| 手写 LEGAL 在 core | 走 `sync_h5_legal_bundled.py` |
| `LEGAL[doc].replace(/\n/g, '<br>')` | `formatLegalBody` 结构化 HTML |
| visible web scrollbars | 隐藏滚动条 + scroll affordance |

## 依赖

- 规格：《H5壳Legal弹层规范.md》《H5壳Overlay路由规范.md》
- 内容 sync：`sync_h5_legal_bundled.py`

## Flutter 落盘规则

- 壳侧不实现（全 H5）

## H5 落盘规则

- Agent 自写 markup/CSS；gate 检行为

## 导航

- [[component_kit/primitives/dialog]]
- [H5壳Legal弹层规范](../../../../docs/H5壳Legal弹层规范.md)
