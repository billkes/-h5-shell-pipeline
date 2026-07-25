# H5 壳 Overlay 路由规范

hash-router 包中 **Legal / Filter / Bottom Sheet / Dialog** 等带 scrim 的弹层，必须与来源页 **叠加渲染**，禁止整页替换。

## 症状

- 遮罩 `rgba(0,0,0,0.5)` 看起来是 **整块不透明灰屏**
- 根因：`router.dispatch` 仅 `root.innerHTML = render(overlayPath)`，底层页面被销毁，scrim 只能叠在 `body` 背景上

## 正确模式（hash-router + functional-render）

| 弹层类型 | 典型路由 | 渲染方式 |
|----------|----------|----------|
| Legal 居中弹窗 | `#/legal?doc=privacy` | base 页 + `u-app-veil-dialog` |
| 筛选 Bottom Sheet | `#/journal/filter` | Journal 页 + `u-app-veil-sheet` |
| 确认框 / IAP 屏障 | 无路由或 Bridge 回调 | `document.body.insertAdjacentHTML` / `appendChild` |

实现要点见下文「`app_core.js` 必含」；无单独 overlay kit 目录。

## `app_core.js` 必含

1. **`OVERLAY_PATHS`** — 列出所有 hash overlay 路由（至少 `/legal`；有筛选则加 `/journal/filter` 等）
2. **`isOverlayPath(path)`** — 判断是否 overlay
3. **`_overlayBase`** — `navigate` 进 overlay 时记录当前 `{ path, params }`（非 replace）
4. **`dispatch` 叠加** — overlay 时：
   ```js
   root.innerHTML = render(base.path, base.params) + render(overlayPath, params);
   afterMount(base, { stackedBase: true });
   afterMount(overlay, { stackedOverlay: true });
   ```
5. **`overlayFallbackBase`** — 冷启动/刷新直链 overlay 时的默认底页
6. **关闭** — overlay 内 `history.back()`；`afterMount` 叠加态 **跳过** parallax/swipe 重复绑定

## CSS（已有 veil token 即可）

- `--app-veil-scrim` / `--app-veil-dialog-scrim` 保持半透明 `rgba`
- 勿把 scrim 写成不透明 hex；问题通常在路由而非 token

## 流水线验收

| 阶段 | 检查 |
|------|------|
| H5 Implementer 后 | `verify_h5_overlay_stack()` HARD FAIL |
| Phase 6 | `audit_h5_overlay_stack.py` PASS |
| 交付自检 | 《H5壳H5实现检查清单.md》· Overlay 相关项 |

## 参考实现

hash-router 包：core 模块中 `OVERLAY_PATHS` / `router.dispatch`；render 模块中 `renderLegal` / `renderFilter`（路径与命名随本包 prefix，禁止照抄他包文件名）。
