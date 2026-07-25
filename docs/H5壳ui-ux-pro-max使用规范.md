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
| `agent.h5` | 严格按本包 MASTER + pages + stack-vue/html-tailwind 实现；发现 SaaS/跨包皮则停写并先修设计 |

## 7. 交付前自检（设计）

- [ ] Query / Category / Style 符合本包主题，非默认 SaaS  
- [ ] Style 偏 Mobile 或明确触控友好  
- [ ] 仅使用 vue + html-tailwind 作为 H5 实现栈  
- [ ] 未引用其他包 design-system / h5 皮肤  
- [ ] `本包视觉锁.json` 色板与 MASTER 一致  

## 导航

- 上级：`H5壳Vite工程规范.md` · `H5壳Pack约束.md`  
- 技能说明：工作区内 `.cursor/skills/ui-ux-pro-max`（若已链接）
