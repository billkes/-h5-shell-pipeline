# H5 壳 Legal 弹层规范

h5_shell 包 **Privacy / User Agreement** 在应用内的展示规范。与 `视觉蓝图.md` §Legal Overlay、Modal Interior Spec 对齐。

## 内容层

1. PM 产出 `{App} Privacy Agreement.md` / `{App} User Agreement.md`
2. 流水线运行 `sync_h5_legal_bundled.py` → `app_legal_bundled.js`（H5 站点统一文件名，不随壳 prefix 变化）
3. `app_entry.htm` 在 `app_core.js` **之前** load bundled script
4. `app_core.js` **禁止** inline `NS.ui.LEGAL`

验收：`audit_h5_legal_bundled.py` PASS

## 展示层（Modal Interior）

**路由：** Legal 为 hash overlay（`#/legal`）时，必须按《H5壳Overlay路由规范.md》叠加来源页 + veil，禁止整页替换导致遮罩不透明。

**禁止** `U.LEGAL[doc].replace(/\n/g, '<br>')` 单 div 输出。

必须采用 kit（`data/static/h5_legal_kit/`）：

| 区域 | 规格 |
|------|------|
| 卡片 | `c-app-legal-card` · flex column · `width: min(90vw, 340px)` · `max-height: 85vh` |
| Header | `c-app-legal-header` · titleMedium 16/600 · Close 44×44 |
| 滚动体 | `c-app-legal-scroll` · 16pt pad · 独立 overflow |
| 章节 | `c-app-legal-section` · 14px/600 |
| 正文 | `c-app-legal-para` · bodySmall 11px |

### 组件层约定

- **class 前缀**：`c-{prefix}-legal-*`（如 `c-app-legal-card`、`c-app-legal-scroll`）
- **render 函数**：`renderLegal` / `formatLegalBody`（参考 `h5_legal_kit/` 的 `legal_render.js.snippet`）
- **Flutter 壳侧**：不实现 Legal Widget；全由 H5 弹窗/页面承担
- **overlay 叠加**：Legal 为 hash overlay（`#/legal`）时，按《H5壳Overlay路由规范.md》叠加来源页 + veil，禁止整页替换导致遮罩不透明
- **内容同步**：`sync_h5_legal_bundled.py` → `{prefix}_legal_bundled.js`；`app_entry.htm` 在 `app_core.js` 之前加载

## 滚动与去风味（强制）

《H5去风味规范.md》§4：**禁止系统滚动条**。

- Legal 滚动区使用 **底部 mask 渐变** 暗示可继续滚动
- **禁止** `.c-app-legal-scroll::-webkit-scrollbar { display: block }`
- 使用 `scrollbar-width: none` + `::-webkit-scrollbar { display: none }`

验收：`audit_h5_legal_ui.py` PASS

## 流水线时序

```
H5 Implementer → sync_h5_legal_bundled → verify bundled + verify UI → Auditor
```

任一 verify 失败 → Phase 失败，不得标记 `phase_h5_agent` done。

## 参考实现

Pawioo：`paaow_render.js` `formatLegalBody` / `renderLegal` · `paaow_baseline.css` `.c-paaow-legal-*`
