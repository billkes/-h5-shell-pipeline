# H5 壳 Legal 弹层规范

h5_shell 包 **Privacy / User Agreement** 在应用内的展示规范。

> **无代码 kit。** 不复用 `data/static/h5_legal_kit/`（已移除）。  
> Agent 按本规范 + 包内视觉蓝图 / design-system **自行设计** Legal UI；每包视觉应可区分。  
> Gate（`verify_h5_legal_ui`）只检行为与无障碍合规，不锁死卡片宽高/字号/版式。

## 同一入口 · 运行时二选一（20260725）

**Welcome / Settings（及 Inventory 声明处）共用一个 `openLegal(kind)` 入口**，按是否配置了有效 HTTPS 分支：

| 分支 | 条件 | 行为 |
|------|------|------|
| **A · 弹层 bundled** | `privacyUrl` / `termsUrl` 为空、缺省、或非有效 `https://` | MD → `*_legal_bundled` + `LegalOverlay` 读全文 |
| **B · 系统浏览器外开** | 对应 kind 配了**真实可访问**的 HTTPS | Bridge **`openExternalUrl`** / 原生 open |

```
openLegal(kind):
  url = legalLinks[kind]
  if isExternalLegalUrl(url) → bridge openExternalUrl({ url })   // B
  else → openLegalOverlay(kind)                                 // A
```

### 流水线 vs 产包后

| 阶段 | URL 配置 | 期望 |
|------|----------|------|
| **流水线产包** | **不提供**在线链；`legalLinks` 保持 `''` | 只走 A；bundled sync + UI gate 必过 |
| **产包后快测 / 加工** | 人填真实 Docs / 在线 Privacy·Terms | 自动走 B；清空 URL 即回到 A |

### 硬禁止

- **禁止**在逻辑里写占位假链：`example.com`、`localhost`、`TODO`、`placeholder`、`#`、空壳 `https://`
- **禁止**主 WKWebView `load(第三方 HTTPS)` 当协议页
- **禁止**产包 Agent 臆造两条「看起来像真的」的 URL
- 隐私与条款 URL **分开**（非产品明确要求相同）

参考 snippet（可拷入包）：`data/static/h5_snippets/legal/legalLinks.ts`  
产包后外开真机验证由加工侧执行；**勿**出产包工作区追脑库 pitfalls / 加工 checklist。

---

## 内容层（流水线）

1. PM 产出 `{App} Privacy Agreement.md` / `{App} User Agreement.md`（正文规范见《法律协议规范.md》）
2. H5 落 `h5/src/legal/legalLinks.ts`（或等价）：`privacyUrl` / `termsUrl` 默认 **`''`**；实现 `isExternalLegalUrl` + 统一 `openLegal`
3. 模式 A 内容：`sync_h5_legal_bundled.py` → `h5/src/legal/{prefix}_legal_bundled.ts`
4. **禁止**在业务 core 里手写 / 摘要 `LEGAL` 字符串
5. 在线 HTTPS **仅**产包后由人写入常量 / 登记字段；流水线不填

验收：产包态 → `verify_h5_legal_bundled` + `verify_h5_legal_ui` PASS（走 A）；填链后 → 真机点协议跳出 App（走 B）

---

## 展示层 · 分支 A（弹层 · 默认）

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

## 展示层 · 分支 B（外开 · 有有效 HTTPS 时）

| 必须 | 禁止 |
|------|------|
| Bridge `openExternalUrl { url }` 或等价原生 open | 主 WebView 导航到 docs.google / 第三方域 |
| Welcome + Settings 均可点到对应协议 | 臆造 / 占位 URL；两条链相同却未确认 |
| 真机验证跳出 App | 仅模拟器 `window.open` 当过关 |

H5 失败兜底：`window.open(url, '_blank')`（浏览器预览可用；真机依赖 Bridge）。  
无有效 URL 时**不得**调用 B07，必须回落分支 A。

---

## 滚动与去风味（强制 · 分支 A）

见《H5去风味规范.md》：

- Legal 滚动区 **禁止** 重新打开系统滚动条（`display: block` / `scrollbar-thumb`）
- 用 mask / 渐变等暗示可继续滚

验收：`verify_h5_legal_ui()` PASS

## 流水线时序

```
Plan 产出 MD（无在线 URL）
  → H5：legalLinks 空串 + openLegal 运行时分支 + LegalOverlay（A）
  → sync_h5_legal_bundled → verify UI
  →（产包后可选）人填真实 HTTPS → 自动走 B → 真机点协议
```

## 导航

- 相关（产包工作区内）：《H5壳Vite工程规范.md》· 《H5壳Overlay路由规范.md》· 《法律协议规范.md》· 《H5-Bridge协议.md》· 《H5壳Pack约束.md》
- 流水线仓 `docs/rules/` **勿**作为产包 Agent 必读路径。
