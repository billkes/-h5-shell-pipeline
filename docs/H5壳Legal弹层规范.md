# H5 壳 Legal 弹层规范

h5_shell 包 **Privacy / User Agreement** 在应用内的展示规范。

> **无代码 kit。** 不复用 `data/static/h5_legal_kit/`（已移除）。  
> Agent 按本规范 + 包内视觉蓝图 / design-system **自行设计** Legal UI；每包视觉应可区分。  
> Gate（`verify_h5_legal_ui`）只检行为与无障碍合规，不锁死卡片宽高/字号/版式。

## 内容层（流水线）

1. PM 产出 `{App} Privacy Agreement.md` / `{App} User Agreement.md`
2. `sync_h5_legal_bundled.py` → `h5/src/legal/{prefix}_legal_bundled.ts`（或 vault 等价路径）
3. **禁止**在业务 core 里手写 / 摘要 `LEGAL` 字符串

验收：`verify_h5_legal_bundled` PASS

## 展示层（Agent 自建）

### 必须满足（行为）

| 要求 | 说明 |
|------|------|
| 入口 | Settings（或产品声明处）打开 Privacy / User；可用 modal 或 overlay |
| 结构化正文 | 用 `formatLegalBody`（或等价）把 bundled 文本拆成标题 + 段落 HTML；**禁止** `LEGAL[doc].replace(/\n/g, '<br>')` 整墙 dump |
| 可滚动阅读 | 正文区可独立滚动；系统滚动条隐藏（去风味） |
| 滚动暗示 | 底部 fade / mask 等暗示「还有内容」（实现不限） |
| Close | 明确关闭控件；触控目标 ≥ 44×44 |
| Overlay | 若走 hash `#/legal`，按《H5壳Overlay路由规范.md》叠加来源页 + veil |

### 视觉（Agent 自由，须差异化）

- 卡片宽度、圆角、阴影、字体、色板、章节层级样式 → **跟本包视觉锁 / pages 规范**，不要抄成「全批次同一张 340px 灰卡」
- class 可用 `c-{prefix}-legal-*`（header / title / scroll / section / para）方便 gate 识别；命名可扩展，但须能被审计找到滚动区与标题区

### 组件层

- Flutter / Swift / OC 壳侧：**不**实现 Legal Widget；全由 H5 承担
- 实现位置：`LegalOverlay.vue` 或等价；样式可进 `global.css` 或 scoped（gate 会扫 `h5/src`）

## 滚动与去风味（强制）

见《H5去风味规范.md》：

- Legal 滚动区 **禁止** 重新打开系统滚动条（`display: block` / `scrollbar-thumb`）
- 用 mask / 渐变等暗示可继续滚

验收：`verify_h5_legal_ui()` PASS

## 流水线时序

```
H5 Implementer（自建设计）→ sync_h5_legal_bundled → verify bundled + verify UI → Auditor
```

## 导航

- 上级：[[docs/rules/H5壳包开发规则]]
- 相关：[[docs/H5壳Vite工程规范]] · [[docs/H5壳Overlay路由规范]] · [[docs/法律协议规范]]
