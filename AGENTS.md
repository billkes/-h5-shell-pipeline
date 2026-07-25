# AGENTS.md — h5-shell-pipeline 项目指令上下文

## 项目概述

**h5-shell-pipeline** 是独立于 `cursor-ios-batch`（A-Crush）的 H5 壳包批量生产流水线。仅处理：

- `h5_shell` / `h5_flutter_shell`（Flutter 运行时壳）
- `h5_swift_shell`（Swift 原生壳，xcodegen）
- `h5_oc_shell`（Objective-C 原生壳，Hathoo-OC 厂包夹板）✅

核心目标：批量生成 **H5 业务 SPA + Native 壳** 组合包，Bridge 七维锁定，符合 App Store 4.3 差异化要求。

## 技术栈

| 层级 | 技术 |
|------|------|
| 流水线引擎 | Python 3.10+，`scripts/batch/` |
| Agent | Cursor CLI（默认）/ iFlow SDK |
| H5 | Vite monolith 单文件 HTML |
| Native | Swift（xcodegen）/ Flutter / OC |
| 台账 | 根目录 `task.csv`（36 列含 Kit 八维） |
| 配置 | `config/config.yaml` + `config/config.env` |

## 快速开始

```bash
./run.sh                          # 交互式菜单
./run.sh task init --batch-id 88-0714 --rows 6
./run.sh task fill                # Bridge 七维 + productFlow
./run.sh task audit
./run.sh task ready
./run.sh --name Buildioo          # Agent 产包
./run.sh --dry-run --name Buildioo
./run.sh build-all                # 无 Agent，仅套 Swift 模板
```

## Pipeline V3 Steps（H5）

```
prepare.context → lock.dimensions → sync.distilled
→ agent.design → agent.plan.spec → agent.plan.pack → agent.shell → agent.h5
→ plan.gate → dev.h5.build → git.plan → git.dev
```

Flutter 壳额外：`dev.pubget` → `dev.analyze`

`prepare.context` 将 ui-ux-pro-max **克隆进包内** `.cursor/skills/ui-ux-pro-max/`；设计由 **`agent.design`** 主产（无脚本草稿链）。详见 `docs/H5壳ui-ux-pro-max使用规范.md`、`docs/rules/H5壳包开发规则.md`。

## 目录结构

```
h5-shell-pipeline/
├── task.csv
├── run.sh / run.ps1 / run.bat
├── scripts/batch/          # Python 流水线（自有副本，不引用 A-Crush）
├── output/{AppName}/       # 产出目录（平铺，无 batch 子层）
├── data/decks/             # Bridge 七维牌池
├── data/static/templates/  # swift_shell 等厂包夹板
├── prompts/h5_shell/       # Agent prompt
├── docs/rules/             # 仓库规则
└── config/                 # 本地配置（不提交）
```

## 与 A-Crush 的关系

- **完全独立仓库**：禁止运行时 import 或路径引用 A-Crush
- 共有模块（Gate、deck）在本仓内自有维护
- 飞书同步：**未接入**，task.csv 人工维护

## 常用命令

```bash
./run.sh task init --batch-id <id> --rows <n>
./run.sh task add --count <n>
./run.sh task fill
./run.sh task audit
./run.sh task ready
./run.sh --name <App> [--dry-run] [--agent-provider cursor|iflow]
./run.sh build-all   # 模板构建（template_build）
pytest scripts/batch/tests/test_pipeline_smoke.py -q
```

## 开发约定

- 配置优先级：命令行 > 环境变量 > config.yaml > config.env > 默认值
- 断点续跑：`output/.../App/.build-state.json`
- 产出目录 `output/` 不提交 Git；`h5_site/` 为 Vite 部署产物（`dev.h5.build` 生成），同样不提交
- 浏览器 Vite DEV：无壳时 Bridge 走 `h5/src/bridge/browserMock.ts`（snippet 见 `data/static/h5_snippets/bridge/`），避免媒体调用卡死 UI；真机 Plaza 仍为原生验收
