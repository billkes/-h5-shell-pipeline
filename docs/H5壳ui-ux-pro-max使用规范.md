# H5 壳 · ui-ux-pro-max 使用规范

> Agent 必读。消费向 **Vue Mobile H5**（WKWebView）如何正确调用技能仓库。  
> 技术栈锁定：**Vue 3 + Vite + Tailwind + Phosphor**——不换栈；纠偏靠**用法判断**，不靠穷举代码。

## 1. 职责分工

| 角色 | 职责 |
|------|------|
| **流水线** `prepare.context` | 把技能**克隆/复制进本包** `.cursor/skills/ui-ux-pro-max/`（真实文件）；写 context / 规范语料 |
| **`agent.design`** | **设计主产**：用包内 skill 选型并 `--persist`；写 briefs/tokens + `skill-adapt/design-audit.md` |
| **后续 Agent** | 默认信任 design-audit；Pack 只锁视觉；H5 做两阶段实现 |
| **薄 gate（脚本）** | 仅挡明显违规（如缺 MASTER / 仍落成 SaaS 名）——不替代 Agent 行业判断 |

**原则：** 第一枪由读过本规范的 **`agent.design`** 打出；流水线**不再**在 Agent 前跑 `skill.design`～`skill.tokens` 草稿链。  
**原则：** Agent **只认包内** `.cursor/skills/ui-ux-pro-max/`，不依赖本机 `UUPM_SKILL_DIR` / 兄弟仓路径（兼容网页 Agent）。

## 2. 本包栈（禁止误用）

| 用途 | 技能入口 | 说明 |
|------|----------|------|
| 架构 | `--stack vue` → `stack-vue.md` | 仅 Vue 3 Composition / SFC / router |
| 样式 | `--stack html-tailwind` → `stack-html-tailwind.md` | 继续 Tailwind；检索时偏 mobile |
| Mobile UX | `--domain web`（`app-interface`） | 触控 / 安全区 / 移动导航 |
| 视觉风格 | `--design-system` + 优先 **Type=Mobile** 风格 | 见 §4 |

**禁止**把下列栈当 H5 业务实现源：

- `react-native` / `swiftui` / `flutter` / `jetpack-compose`（原生指南，不是 Vue H5）
- `nuxtjs` / `nuxt-ui`（本流水线不用 Nuxt）
- 对照 `output/` 下其他包的 MASTER / `h5/` 当模板

原生壳仍可读 `swiftui` / `flutter` stack——**仅限壳工程**，不指导 H5 页面皮肤。

## 3. Query 怎么写（对齐技能 README）

技能靠 **英文行业关键词** 定 product 类型再推风格。错误 query → Productivity / SaaS。

### 3.1 推荐形态

```text
{行业词} {场景词} mobile app
```

示例（按 CSV `赛道` / `核心场景` 自行替换，勿照抄）：

| 赛道倾向 | 推荐 query 关键词 |
|----------|-------------------|
| 美妆个护 | `beauty spa wellness skincare self-care` |
| 健康个护 / 健康 | `healthcare wellness calm organic`（可加 scene：lens / habit / sleep…） |
| 亲子家庭 | `family parenting household warm` |
| 教育培训 | `education classroom learning academic` |
| 休闲生活 / 爱好 | `lifestyle hobby cozy collection` |

技能 README 正向示例：`beauty spa wellness`、`fintech banking`。  
**仅当**产品真是 B2B / 企业后台时才用：`SaaS dashboard`、`productivity tool`。

### 3.2 禁止（消费向 H5 默认）

- query 含：`saas`、`SaaS dashboard`、`b2b`、`enterprise productivity`
- 无必要的泛词堆砌：`productivity tool` + `habit tracker` 叠用导致 product 漂到 Productivity Tool
- 把中文 CSV 原文塞进 BM25 query
- 为「防撞」往 query 里加 `saas` / `dashboard productivity`（与本规范冲突）

### 3.3 命令（`agent.design` 主产时）

技能须已在本包根下（`prepare.context` 克隆/复制，**非**宿主机 symlink）：

```bash
# 设计系统（行业 query + 项目名）— 第一枪由 Agent 打出
python .cursor/skills/ui-ux-pro-max/scripts/search.py "<行业 query>" --design-system --persist -p "<AppName>"

# Mobile UX 补强
python .cursor/skills/ui-ux-pro-max/scripts/search.py "touch safe-area 44px mobile navigation" --domain web -n 8

# 栈指南（保持双栈）
python .cursor/skills/ui-ux-pro-max/scripts/search.py "touch 44px mobile-first safe-area" --stack html-tailwind -n 8
python .cursor/skills/ui-ux-pro-max/scripts/search.py "composition script setup router" --stack vue -n 8
```

Windows 用 `python`；路径固定为包内相对路径，网页 Agent 同此命令。

## 4. 选型硬规则（Agent 自检清单）

对 `design-system/*/MASTER.md` 与 `candidates.json` 逐条核对：

1. **禁 SaaS（消费向默认）**  
   - Style 名含：`SaaS`、`Enterprise SaaS`、`SaaS Mobile`  
   - Category 为：`SaaS (General)`、`Micro SaaS`、无场景依据的 `Productivity Tool`  
   → **不合格**，必须按 §3 重跑并改写 MASTER / 相关 brief。

2. **偏 Mobile**  
   - 优先 Style `Type=Mobile` 或明确 Mobile-First / 触控友好的风格  
   - 配色与字体服务手机一屏，而非桌面 dashboard

3. **贴主题**  
   - Category / 色板 notes / typography mood 能对应本包 `coreScene` / `audience` / `track`  
   - 隐形眼镜 / 染发护色等垂直场景，不得落成通用企业后台皮

4. **栈文件仍在**  
   - 必须保留 `stack-vue.md` + `stack-html-tailwind.md`  
   - 不得改成 RN/SwiftUI 实现说明替代 H5

5. **禁止跨包抄设计**  
   - 不得 `Read` / `find` 其他 App 的 `design-system/**/MASTER.md` 或 `h5/src/styles` 当母版  
   - 视觉锁与 H5 实现只认**本包** skill 产物 + 本规范

## 5. 何时必须重跑技能

出现任一则 **`agent.design` 不得交付**（须换 query 重跑技能，`design-audit` 记 `REPAIRED`）：

- MASTER Style / Category 命中 §4.1  
- 色板 + 字体 + pattern 与同批兄弟包明显同构（通用灰蓝 Inter + App Store landing）  
- 主题是美妆/健康/亲子等，MASTER 却是企业/Productivity/SaaS 气质  
- `stack-html-tailwind.md` 只有桌面 container/max-width 指引、完全无 touch / mobile-first 条目  

交付前必须齐：

- `design-system/<slug>/MASTER.md`（及 `candidates.json` / 双栈文件）  
- `design-system/<slug>/pages/welcome.md` · `pages/hub.md`（各含 `### Scene Brief`，字段见 `phase_agent_design`）  
- `skill-adapt/design-brief.md` + tokens，与 MASTER 一致  
- `skill-adapt/design-audit.md`（`PASS` / `REPAIRED`，含 `welcomePattern` · `hubPrimaryZone`）  
- 之后由 `agent.plan.pack` 写 `本包视觉锁.json`

## 6. 与后续 Agent 步骤的关系

| 步骤 | 与本规范 |
|------|----------|
| `prepare.context` | 克隆技能进 `.cursor/skills/ui-ux-pro-max/`（真实文件） |
| `agent.design` | **主产**设计系统 + design-audit（打第一枪） |
| `agent.plan.spec` | 功能文档 UX 对齐本包 MASTER，不发明第二套皮肤 |
| `agent.plan.pack` | **只锁**视觉：按 design-audit + MASTER 写 `本包视觉锁.json`（含六槽 `assetBrief`） |
| `agent.assets` | task「真图」=1：替换 logo / launch×2 / global_bg×2 / retry；=0 跳过 |
| `agent.shell` | 原生栈指南可分读；H5 皮肤仍以本包 design-system 为准 |
| `agent.h5` | **两阶段**：先 `_preview/pages/*.html`（HTML+Tailwind），再固定栈移植进 `h5/`（见 §8） |

## 7. 交付前自检（设计）

- [ ] `skill-adapt/design-audit.md` 已写（`PASS` / `REPAIRED` + `welcomePattern` · `hubPrimaryZone`）  
- [ ] `pages/welcome.md` · `pages/hub.md` 各有完整 `### Scene Brief`  
- [ ] Query / Category / Style 符合本包主题，非默认 SaaS  
- [ ] Style 偏 Mobile 或明确触控友好  
- [ ] 仅使用 vue + html-tailwind 作为 H5 实现栈  
- [ ] 未引用其他包 design-system / h5 皮肤  
- [ ] `本包视觉锁.json` 色板与 MASTER 一致（由 Pack 落锁）  

## 8. H5 两阶段实现（HTML 预览 → Vue 移植）

技能默认 **Web (HTML) + Tailwind**。H5 Agent 用单页 HTML 把视觉细节钉死，再用固定 Vue 栈「抄」进完整工程——**扩展现有 `_preview/`**，不开第三套预览目录。

### 8.1 目录（扩展 `_preview/`，勿另起体系）

与流水线 `preview.tabs`（`{slug}-tabs-preview.html` · `preview-canonical.md`）并存：

```text
_preview/
├── preview-canonical.md          # 已有：Tab / 色 / 字（流水线）
├── {slug}-tabs-preview.html      # 已有：Tab 明暗总览（流水线）
└── pages/                        # Agent 新增：逐屏 HTML 视觉契约
    ├── INDEX.md                  # 路由 → 文件映射 + 必做/选做标记
    ├── FREEZE.md                 # 冻结声明（移植开始后生效）
    ├── welcome.html
    ├── hub.html                  # Tab1 / 主区
    ├── export.html               # 若 Inventory 有导出/主工作流面
    └── ….html                    # 其他已列路由
```

文件名：hash 路由去 `#/`，`/` → `-`（如 `#/day/detail` → `day-detail.html`）。

### 8.2 阶段 A — 逐页 HTML 快速预览

**顺序（保持焦点）**

1. 打开本包 `pages/welcome.md` · `hub.md`（及 Inventory 对应的其他 `pages/*.md`）Scene Brief。  
2. 按 Brief 的 Beats / Primary zone / Motif **逐段写出**各 MUST HTML（再写 SHOULD）。  
3. 写 `INDEX.md`（路由 → 文件 → 必做/选做 → 对应 `pages/*.md`）。  
4. 写 `FREEZE.md`（含下方完成证明表）后，再进入阶段 B。  
5. 之后若改视觉：先改 HTML 与 FREEZE 证明行，再移植 Vue。

**范围**

- 页面清单 = **功能文档 Screen Inventory**。  
- 每页独立 HTML：mobile-first（建议 viewport ~390）、Tailwind（CDN 或 MASTER / `design-tokens` CSS 变量）、Phosphor 可用简易 SVG/CDN **仅预览**。  
- **MUST**：Welcome、Tab1/Hub、Primary Workflow / Export（Inventory 有则做）。  
- **SHOULD**：其余 bottom tab-root（各 tab 自有主区布局，对齐该 tab 职责）。  
- **MAY**：stack/overlay；Legal / Plaza 可用极简 HTML，专项规范 + Vue 落地。  
- HTML 钉视觉与信息架构；Bridge / IAP / router / 持久化在阶段 B。

**完成标准（MUST）**

| 面 | 完成时文件内应具备 |
|----|-------------------|
| Welcome | ≥2 个 beat 区块（或明确 step 结构），布局/motif 与 Scene Brief 各 beat 对应；末拍含同意控件 + 协议链 + Continue；Hero craft + 场景向标题 |
| Hub / Tab1 | 场景问候 + 主工作区（空态可为骨架）+ 进入主工作流 CTA；主结构层级与 Welcome 可区分 |
| Export / 主工作流面 | 与 Hub 预览同构图示意（同 aspect）；主控件与 Scene Brief / 功能文档一致 |
| 各 SHOULD tab | 标题 + 该 tab 专属主区（骨架/motif + CTA），与 Inventory 角色一致 |

**FREEZE.md 完成证明**（阶段 B 前写齐）

- 冻结时间、Inventory 摘要、MUST 文件列表  
- 每个 MUST 一行：`file · beats或主区 · token来源 · 与邻页的布局差异一语`

### 8.3 阶段 B — 固定栈移植进 `h5/`

1. 自建完整 Vite 工程（《H5壳Vite工程规范.md》）。  
2. **逐路由对照** `_preview/pages/<file>.html`：结构与 Tailwind class **优先原样迁移**进 SFC；再补 Composition / router / store。  
3. 交互与 Bridge 按功能文档 + Bridge 协议补全；HTML 上的主 CTA 在 Vue 内可点通（browserMock 或真机）。  
4. 图标改为 `@phosphor-icons/vue`（与 `icon-manifest.json` 对齐）。  
5. **可构建交付物只有 `h5/` → `h5_site/`**；流水线工程检查验 `h5/`；`_preview/pages` 由 Agent 按本节完成标准交付。

### 8.4 协作约定

| 主题 | 约定 |
|------|------|
| **视觉真源节奏** | 冻结前：HTML = 视觉契约；冻结后至交付：以 Vue `h5/` 为实现真源，视觉变更先回写 HTML + FREEZE 再移植 |
| **可点通** | Primary / Secondary Workflow、Export、权限与 IAP 路径在 Vue 内可走通 |
| **范围** | 严格执行 MUST / SHOULD / MAY（§8.2）；Legal/Plaza 可用极简 HTML |
| **与 tabs 预览** | `preview-canonical` / tabs HTML 管 Tab IA 与色板；`pages/*.html` 管单屏密度；色板以 MASTER + `preview-approved-colors` / canonical 为准 |
| **本包设计** | 预览与 Vue 只认本包 `design-system` / Scene Brief / tokens |
| **RESUME** | 先补齐 MUST HTML + FREEZE 证明，再按页移植 |

### 8.5 阶段自检

**阶段 A**

- [ ] 已按 Scene Brief 写出 MUST HTML（Welcome beats、Hub 主区均到位）  
- [ ] INDEX 覆盖 Inventory 中全部 MUST 路由，并链到对应 `pages/*.md`  
- [ ] FREEZE.md 含 MUST 完成证明表（每文件一行）  
- [ ] 色板来自 MASTER / tokens / canonical  
- [ ] 任意两 MUST 页并排时，靠主结构即可区分（标题以外有布局差异）  

**阶段 B**

- [ ] 每个 MUST HTML 有对应 Vue 路由/视图，class/层级可追溯  
- [ ] Workflow / Bridge / Legal 分支可走通  
- [ ] 交付从 `h5/` 构建；`_preview/pages` 保持与实现对齐的视觉契约  

## 导航

- 上级：`H5壳Vite工程规范.md` · `H5壳Pack约束.md` · `H5壳H5实现检查清单.md`  
- 技能说明：工作区内 `.cursor/skills/ui-ux-pro-max/`（`prepare.context` 克隆的真实文件）
