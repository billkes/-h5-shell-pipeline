# H5 壳 · ui-ux-pro-max 使用规范

> Agent 必读。消费向 **Vue Mobile H5**（WKWebView）如何正确调用技能仓库。  
> 技术栈锁定：**Vue 3 + Vite + Tailwind + Phosphor**——不换栈；纠偏靠**用法判断**，不靠穷举代码。

## 1. 职责分工

| 角色 | 职责 |
|------|------|
| **流水线脚本** `skill.design`～`skill.tokens` | 产出**草稿**设计系统（MASTER / candidates / stack / pages / tokens） |
| **Agent** | 读本规范 + CSV 主题，**审核并在不合格时重跑技能**，再写登记/实现 |
| **薄 gate（脚本）** | 仅挡明显违规（如 style 名含 SaaS 仍落盘）——不替代 Agent 行业判断 |

**原则：** 行业匹配、Mobile 气质、是否 SaaS——由 Agent 按主题判断；脚本不得假装覆盖所有赛道。

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

### 3.3 命令（Agent 重跑时）

在本包工作区、技能已链到 `.cursor/skills/ui-ux-pro-max`（或流水线注入的 scripts）时：

```bash
# 设计系统（行业 query + 项目名）
python .cursor/skills/ui-ux-pro-max/scripts/search.py "<行业 query>" --design-system --persist -p "<AppName>"

# Mobile UX 补强
python .cursor/skills/ui-ux-pro-max/scripts/search.py "touch safe-area 44px mobile navigation" --domain web -n 8

# 栈指南（保持双栈）
python .cursor/skills/ui-ux-pro-max/scripts/search.py "touch 44px mobile-first safe-area" --stack html-tailwind -n 8
python .cursor/skills/ui-ux-pro-max/scripts/search.py "composition script setup router" --stack vue -n 8
```

Windows 可用 `python` 代替 `python3`。路径以本包内实际 skill 位置为准。

## 4. 选型硬规则（Agent 审核清单）

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

出现任一则 Agent **先修设计再继续**（Plan Pack 写视觉锁之前；H5 实现之前再确认一次）：

- MASTER Style / Category 命中 §4.1  
- 色板 + 字体 + pattern 与同批兄弟包明显同构（通用灰蓝 Inter + App Store landing）  
- 主题是美妆/健康/亲子等，MASTER 却是企业/Productivity/SaaS 气质  
- `stack-html-tailwind.md` 只有桌面 container/max-width 指引、完全无 touch / mobile-first 条目，且实现已偏桌面布局  

重跑后同步：

- `design-system/<slug>/MASTER.md`（及需要时的 `candidates.json`）  
- 必要时请流水线或本地再跑 `skill.adapt` / `skill.tokens` 相关产物；至少更新 `skill-adapt/design-brief.md` 与色板叙述，使与新 MASTER 一致  
- 再写 `本包视觉锁.json`

## 6. 与后续 Agent 步骤的关系

| 步骤 | 与本规范 |
|------|----------|
| `agent.plan.spec` | 功能文档 UX 描述对齐本包 MASTER，不发明第二套皮肤 |
| `agent.plan.pack` | **审核** skill 草稿；不合格则按 §3–§5 修复；再写 `本包视觉锁.json` |
| `agent.shell` | 原生栈指南可分读；H5 皮肤仍以本包 design-system 为准 |
| `agent.h5` | **两阶段**：先 `_preview/pages/*.html`（HTML+Tailwind），再固定栈移植进 `h5/`（见 §8） |

## 7. 交付前自检（设计）

- [ ] Query / Category / Style 符合本包主题，非默认 SaaS  
- [ ] Style 偏 Mobile 或明确触控友好  
- [ ] 仅使用 vue + html-tailwind 作为 H5 实现栈  
- [ ] 未引用其他包 design-system / h5 皮肤  
- [ ] `本包视觉锁.json` 色板与 MASTER 一致  

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

1. 以 **功能文档 Screen Inventory** 为页面清单（禁止加 Inventory 外路由）。  
2. 每页一个独立 HTML：mobile-first（建议 viewport 宽 ~390）、Tailwind（CDN 或与 MASTER token 一致的内联 CSS 变量）、Phosphor 可用简易 SVG/CDN **仅预览**。  
3. 视觉对齐：`MASTER.md` · `pages/<screen>.md` · `design-tokens` / 本包视觉锁色板。  
4. **写** `_preview/pages/INDEX.md`（路由、文件、必做/选做、对应 `pages/*.md`）。  
5. **必做（MUST）**：Welcome、Tab1/Hub、Primary Workflow / Export 面（Inventory 有则做）。  
6. **应做（SHOULD）**：其余 bottom tab-root。  
7. **可做（MAY）**：stack/overlay（day、capture、store…）；Legal / Plaza **不要求**精美 HTML——专项规范 + Vue 落地即可（可极简壳或跳过）。  
8. HTML **只钉视觉与信息架构**：可示意空态/主态；**不**实现真 Bridge、真 IAP、真 router、真持久化。

阶段 A 结束、开始写 `h5/` **之前**：写 `_preview/pages/FREEZE.md`（冻结时间、Inventory 版本摘要、MUST 文件列表）。冻结后 **禁止**为「好看一点」改 HTML 却不改 Vue；若必须改视觉：先改 HTML → 更新 FREEZE → 再同步 Vue。

### 8.3 阶段 B — 固定栈移植进 `h5/`

1. 自建完整 Vite 工程（《H5壳Vite工程规范.md》）。  
2. **逐路由对照** `_preview/pages/<file>.html`：结构与 Tailwind class **优先原样迁移**进 SFC；再补 Composition / router / store。  
3. 交互与 Bridge **必须**按功能文档 + Bridge 协议补全——禁止「只有静态皮、按钮无业务」。  
4. 图标改为 `@phosphor-icons/vue`（与 `icon-manifest.json` 对齐）；去掉预览用的临时 CDN 图标方案。  
5. **可构建交付物只有 `h5/` → `h5_site/`**；gate / `dev.h5.build` **不**把 `_preview/pages` 当部署产物。

### 8.4 风险处理（必须遵守）

| 风险 | 处理 |
|------|------|
| **双真源** | 冻结前：HTML = 视觉契约；冻结后至交付：以 **Vue `h5/` 为唯一实现真源**。禁止 HTML/Vue 长期分叉。 |
| **抄成死页面** | 每条 Primary / Secondary Workflow、Export、权限与 IAP 路径须在 Vue 内可点通（browserMock 或真机）；HTML 有的 CTA 在 Vue 须有对应 handler。 |
| **成本爆炸** | 严格执行 MUST / SHOULD / MAY（§8.2）；Legal/Plaza 不强制精美 HTML。 |
| **与 tabs 预览冲突** | `preview-canonical` / tabs HTML 管 **Tab 信息架构与色板**；`pages/*.html` 管 **单屏视觉密度**。色板冲突时以 MASTER + `preview-approved-colors` / canonical 为准，改单页 HTML 对齐，不另起色板。 |
| **跨包抄袭** | 预览与 Vue 均禁止对照其他包 `_preview/` / `h5/`。 |
| **RESUME 半成品** | 若已有部分 `h5/`：先补齐缺失的 MUST HTML + FREEZE，再按页补移植；勿在无预览契约时大面积重写皮肤。 |

### 8.5 阶段自检

**阶段 A**

- [ ] INDEX 覆盖 Inventory 中全部 MUST 路由  
- [ ] FREEZE.md 已写且 MUST 文件存在、非空壳（有主标题 + 主区结构）  
- [ ] 色板与 MASTER / canonical 一致，非 SaaS 灰蓝默认皮  

**阶段 B**

- [ ] 每个 MUST HTML 有对应 Vue 路由/视图，class/层级可追溯  
- [ ] Workflow / Bridge / Legal 分支按规范可走通  
- [ ] 未手改 `h5_site/`；未把 `_preview/pages` 当部署入口  

## 导航

- 上级：`H5壳Vite工程规范.md` · `H5壳Pack约束.md` · `H5壳H5实现检查清单.md`  
- 技能说明：工作区内 `.cursor/skills/ui-ux-pro-max`（若已链接）
