# h5-shell-pipeline

H5 Shell 批量生产流水线。支持：

- `h5_shell`（Flutter 运行时）
- `h5_flutter_shell`
- `h5_swift_shell`
- `h5_oc_shell`

## 前置要求

- Python 3.10+
- Git
- Flutter / Xcode（按目标包类型）
- `h5_swift_shell` / `h5_oc_shell` 需要 **macOS + Xcode**；`h5_swift_shell` 额外需要 [xcodegen](https://github.com/yonaskolb/XcodeGen) 来生成 `.xcodeproj`（`brew install xcodegen`）

> Windows 用户若使用 PowerShell 执行 `./run.ps1` 时遇到“执行脚本已禁用”，请用 **管理员 PowerShell** 运行 `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`，或改用 `run.bat` / 直接设置 `PYTHONPATH=scripts` 后运行 `python -m batch ...`。

## 快速开始

```bash
# 交互式菜单（批次准备 + Agent 产包）
./run.sh

# 1. 初始化空 task.csv
./run.sh task init --batch-id 88-0714 --rows 6

# 2. 人工填充 task.csv 后抽 Bridge 七维
./run.sh task fill

# 3. 校验
./run.sh task validate
./run.sh task audit
./run.sh task ready

# 4. Agent 产包
./run.sh --name Buildioo
./run.sh --dry-run --name Buildioo

# 5. 无 Agent 模板构建（仅套 Swift 壳）
./run.sh build-all
```

Windows PowerShell：

```powershell
.\run.ps1 task-init --batch-id 88-0714 --rows 6
```

Windows CMD：

```cmd
.\run.bat task-init --batch-id 88-0714 --rows 6
```

## Task CLI

| 命令 | 说明 |
|------|------|
| `task init --batch-id <id> --rows <n>` | 创建空 task.csv |
| `task add --count <n>` | 追加空行 |
| `task fill` | 抽 Bridge 七维 + productFlow |
| `task validate` | 基础校验 |
| `task list` | 列出任务 |
| `task audit` | 批内审计 |
| `task ready` | 产包前严格校验 |
| `--name <应用主名称>` | Agent 产包（单包） |
| `--dry-run` | 仅打印 Step，不调 Agent |
| `build-all` | 模板构建（无 Agent） |

Build 命令支持 `--h5-host`、`--bundle-id-prefix`、`--team-id`，也支持对应环境变量 `H5_PROD_HOST`、`BUNDLE_ID_PREFIX`、`APPLE_TEAM_ID`。

## task.csv 列说明

| 列 | 必填 | 说明 |
|----|------|------|
| `应用主名称` | 是 | App 主名称（PascalCase） |
| `全称` | 是 | 完整显示名 |
| `状态管理` | 是 | Flutter 状态管理（GetX / Bloc / Provider 等）；非 Flutter 包可填 `SetState` |
| `架构模式` | 是 | Flutter 架构模式（MVC / MVP / MVVM 等）；非 Flutter 包可填 `MVC` |
| `命名混淆规则` | 是 | 生成代码前缀的规则 |
| `协议风格` | 是 | Legal 协议风格 |
| `隐私文件` | 是 | 隐私政策文件名 |
| `仓库地址` | 是 | Git 仓库地址 |
| `首个商品Code` | 是 | IAP 首个商品 ID |
| `编程风格` | 是 | 美国人 / 英国人 / 德国人 / 法国人 / 俄罗斯人 / 日本人 / 中国人 |
| `应用类型` | 产包前 | `h5_shell` / `h5_flutter_shell` / `h5_swift_shell` / `h5_oc_shell` |
| `主题编号` | 产包前 | 主题库编号 |
| `中文主题` | 产包前 | 中文主题描述 |
| `赛道分类` | 产包前 | 赛道 |
| `目标人群` | 产包前 | 目标用户 |
| `核心场景` | 产包前 | 核心使用场景 |
| `本地功能` | 产包前 | 本地功能 |
| `productFlow` | 产包前 | 产品流程 |
| `webviewEngine` | H5 shell | WebView 引擎 |
| `bridgeCallStyle` | H5 shell | H5 → Native 调用方式 |
| `bridgeCallbackStyle` | H5 shell | Native → H5 回调方式 |
| `bridgeEnvelope` | H5 shell | 消息信封格式 |
| `mediaServe` | H5 shell | 媒体资源服务方式 |
| `bridgeErrorCode` | H5 shell | 错误码形态 |
| `bridgeInjectTiming` | H5 shell | Bridge 注入时机 |

> 非 Flutter 包（Swift/OC）的 `状态管理` 与 `架构模式` 可填写占位值，但列必须存在。

## 模板支持状态

| 应用类型 | 状态 | 说明 |
|----------|------|------|
| `h5_shell` / `h5_flutter_shell` | ⚠️ 未实现 | 需要 Flutter 壳工程模板 |
| `h5_swift_shell` | ✅ 可用 | `xcodegen generate` 生成 `.xcodeproj` |
| `h5_oc_shell` | ✅ 可用 | Hathoo-OC 厂包夹板 + `apply.py` + 手写 `.xcodeproj` |

## 快速开始（产包）

```bash
# 1. 初始化并填充 task.csv
./run.sh task-init --batch-id 88-0714 --rows 3
# 编辑 task.csv，确保每行 pack_type = h5_swift_shell 且 Bridge 七维已填充

# 2. 校验
./run.sh task-validate
./run.sh task-ready

# 3. 产包
export H5_PROD_HOST="test.darin.beauty"
export APPLE_TEAM_ID="YOURTEAMID"
./run.sh build-all

# 产出在 output/{AppName}/
# macOS 上进入单个包目录生成 Xcode 工程（Swift）：
# cd output/{AppName} && xcodegen generate
```

> **测试包名固定**：流水线阶段 `bundleId` 固定为 `test.duckegg.ios`（可通过环境变量 `XCODE_BUNDLE_ID` 或 `config.yaml` 的 `xcode.bundle_id` 修改），不随应用名变化。

## 目录结构

```
h5-shell-pipeline/
├── task.csv                    # 批次台账
├── run.sh / run.ps1 / run.bat  # 入口脚本
├── scripts/batch/              # Python 流水线模块
│   ├── __main__.py             # CLI 入口
│   ├── csv_tasks.py            # task.csv 解析
│   ├── task_schema.py          # 列定义
│   └── ...                     # 各 Phase 实现
├── data/
│   ├── decks/                  # Bridge 七维牌池
│   ├── static/                 # 静态模板与资源
│   │   └── templates/
│   │       └── swift_shell/    # h5_swift_shell 厂包夹板
│   └── registry/               # 登记表
├── docs/                       # 规范文档
│   ├── rules/                  # 仓库级规则
│   ├── H5-Bridge协议.md
│   ├── H5壳Swift实现规范.md
│   └── ...
├── .cursor/                    # Cursor IDE 仓库级规则
│   └── rules/
│       ├── cib-项目结构.mdc
│       ├── cib-主题防火墙.mdc
│       ├── cib-批量添加任务.mdc
│       ├── cib-批次准备.mdc
│       └── cib-H5壳包开发.mdc
├── prompts/                    # Agent prompt 模板
└── output/                     # 产出目录
```

## 仓库规则

- [docs/rules/项目结构规则.md](docs/rules/项目结构规则.md)
- [docs/rules/主题防火墙说明.md](docs/rules/主题防火墙说明.md)
- [docs/rules/批量添加任务规则.md](docs/rules/批量添加任务规则.md)
- [docs/rules/批次准备规则.md](docs/rules/批次准备规则.md)
- [docs/rules/H5壳包开发规则.md](docs/rules/H5壳包开发规则.md)

Cursor IDE 会自动读取 `.cursor/rules/*.mdc` 中的规则提示。

## 相关文档

- [docs/H5-Bridge协议.md](docs/H5-Bridge协议.md)
- [docs/H5壳Swift实现规范.md](docs/H5壳Swift实现规范.md)
- [docs/H5壳业务流程文字版.md](docs/H5壳业务流程文字版.md)
