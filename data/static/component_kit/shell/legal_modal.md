# Legal Modal

## 组件 ID

`shell/legal_modal`

## 分类

`shell`（h5_shell 专用）

## 适用包类型

| 包类型 | 使用场景 | 实现要点 |
|--------|---------|---------|
| h5_shell | Legal / Privacy / Terms 弹层 | 复用 `h5_legal_kit/`；禁 web 滚动条 |

## 变体

无；kit 模板统一。

## 注意事项

1. **复用** `data/static/h5_legal_kit/`（`legal_render.js.snippet` + `legal.css.snippet`）。
2. 内容由 `sync_h5_legal_bundled.py` → `{prefix}_legal_bundled.js`。
3. 详细规格见《H5壳Legal弹层规范.md》。

## 踩坑与规避

| 坑 | 规避 |
|---|---|
| 手写 LEGAL 在 core | 走 `sync_h5_legal_bundled.py` 注入 |
| `LEGAL[doc].replace(/\n/g, '<br>')` | 用 kit 渲染，禁止 `<br>` 替换 |
| visible web scrollbars | `display: block` + mask fade（见 `docs/H5壳Vault合规维护规范.md`） |

## 依赖

- 引用：`primitives/dialog`（overlay 行为）
- kit：`data/static/h5_legal_kit/`
- 规格：《H5壳Legal弹层规范.md》《H5壳Overlay路由规范.md》《H5壳Vault合规维护规范.md》
- brain：`h5-legal-modal-ui-kit`、`h5-legal-md-sync`、`h5-overlay-router-stack`

## Flutter 落盘规则

- 壳侧不实现（全 H5）

## H5 落盘规则

- class：`c-{prefix}-legal-*`
- 滚动：`display: block` + mask fade，禁 web scrollbar
- overlay 叠加 base 页

## 实现过程（思路，无代码）

1. 从 `h5_legal_kit/` 复制 snippet；
2. `sync_h5_legal_bundled.py` 注入内容；
3. overlay router 叠加 base；
4. 滚动 mask fade。

## 组件自身需要去风味的点

- **禁** web 滚动条；
- **禁** `<br>` 替换换行。

## 导航

- [[component_kit/primitives/dialog]]
- [H5壳Legal弹层规范](../../../../docs/H5壳Legal弹层规范.md)
- 全局大脑：`h5-legal-modal-ui-kit-20260707`
