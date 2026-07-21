# H5 壳 Legal 弹层规范

h5_shell 包 **Privacy / User Agreement** 在应用内的展示规范。

> **无代码 kit。** 不复用 `data/static/h5_legal_kit/`（已移除）。  
> Agent 按本规范 + 包内视觉蓝图 / design-system **自行设计** Legal UI；每包视觉应可区分。  
> Gate（`verify_h5_legal_ui`）只检行为与无障碍合规，不锁死卡片宽高/字号/版式。

## 两种展示模式（勿混用同一入口）

| 模式 | 何时用 | 行为 |
|------|--------|------|
| **A · 弹层 bundled**（流水线默认 / 尚无在线链） | Plan 仅产出 MD、未提供 HTTPS | MD → `*_legal_bundled` + `LegalOverlay` 读全文 |
| **B · 系统浏览器外开**（**产包后现行 · 20260721**） | 产品提供 Google Docs / 在线 Privacy·Terms URL | Welcome/Settings 点击 → Bridge **`openExternalUrl`** / 原生 `UIApplication.shared.open` |

> Palioy / Somaoo / Yeario / Reviio：加工阶段有在线链时 **主路径 = B**。  
> **禁止**主 WKWebView `load(第三方 HTTPS)` 当协议页。  
> 同一入口勿既弹层全文又外开（可「说明卡 + Open online」两步，见 pitfalls）。

深读：脑库 [[2_领域/cursor-ios-batch-流水线/h5-shell-协议外链系统浏览器-pitfalls-20260720]] · 加工 [[2_领域/App-Store-审核风控/h5-shell-加工checklist/编组D-H5首屏合规/SKILL]]

---

## 内容层（流水线）

1. PM 产出 `{App} Privacy Agreement.md` / `{App} User Agreement.md`（正文规范见《法律协议规范.md》）
2. 有在线链时：登记 / 产品概述 / H5 常量写入 **可访问 HTTPS**（隐私与条款分开）
3. 模式 A：`sync_h5_legal_bundled.py` → `h5/src/legal/{prefix}_legal_bundled.ts`
4. **禁止**在业务 core 里手写 / 摘要 `LEGAL` 字符串

验收：模式 A → `verify_h5_legal_bundled` PASS；模式 B → 真机点协议跳出 App 打开在线页

---

## 展示层 · 模式 A（弹层）

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
- class 可用 `c-{prefix}-legal-*`（header / title / scroll / section / para）方便 gate 识别

### 组件层

- Flutter / Swift / OC 壳侧：**不**实现 Legal Widget；全由 H5 承担
- 实现位置：`LegalOverlay.vue` 或等价

---

## 展示层 · 模式 B（外开 · 产包后）

| 必须 | 禁止 |
|------|------|
| Bridge `openExternalUrl { url }` 或等价原生 open | 主 WebView 导航到 docs.google / 第三方域 |
| Welcome + Settings 均可点到对应协议 | 臆造 URL；两条链相同却未确认 |
| 真机验证跳出 App | 仅模拟器 `window.open` 当过关 |

H5 失败兜底：`window.open(url, '_blank')`（浏览器预览可用；真机依赖 Bridge）。

---

## 滚动与去风味（强制 · 模式 A）

见《H5去风味规范.md》：

- Legal 滚动区 **禁止** 重新打开系统滚动条（`display: block` / `scrollbar-thumb`）
- 用 mask / 渐变等暗示可继续滚

验收：`verify_h5_legal_ui()` PASS

## 流水线时序

```
Plan 产出 MD（+ 可选在线 URL）
  → 模式 A：sync_h5_legal_bundled → verify UI
  → 模式 B（加工）：写入 HTTPS 常量 + Bridge 外开 → 真机点协议
```

## 导航

- 上级：[[docs/rules/H5壳包开发规则]]
- 相关：[[docs/H5壳Vite工程规范]] · [[docs/H5壳Overlay路由规范]] · [[docs/法律协议规范]] · [[docs/H5-Bridge协议]] · [[docs/H5壳Pack约束]]
