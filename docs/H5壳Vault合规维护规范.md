# h5_shell Vault 合规维护规范

> 本文件是 h5_shell 带壳 H5 包的 **流水线维护者约束**，不是仓库级 Cursor 规则。
> 产包时，其约束会下沉为每个 h5_shell 包 `.cursor/rules/h5-vault-compliance.mdc`。

改以下任一处时，须 **同步** gate、prompt、包级 `h5-vault-compliance.mdc` 生成逻辑：

| 区域 | 路径 |
|------|------|
| 内容 sync | `scripts/batch/sync_h5_legal_bundled.py` |
| UI 校验 | `scripts/batch/h5_legal_ui.py` · `verify_h5_legal_ui()`（行为门禁，无视觉 kit） |
| 默认 seed | `scripts/batch/h5_default_seed.py` · 加工编组 I |
| 包级铁律 | `scripts/batch/cursor_rules.py` → `h5-vault-compliance.mdc` |
| 弹层规范 | 《H5壳Legal弹层规范.md》 |
| 去风味规范 | 《H5去风味规范.md》 |

**禁止**只改单个 output 包而不更新 gate / `cursor_rules.py`。

**去风味**：Legal 滚动 **禁止** web 滚动条（`display: block`）；仅 mask 渐变。美化不得突破《H5去风味规范.md》§4。

---

## Seed / 品牌图必须在 iOS 工程内（20260721）

> 踩坑：图只在对话目录或 workspace 外 → 工程内「看不见」/ 运行蓝底问号。

| 必须 | 禁止 |
|------|------|
| OC/Swift：`ios/{AppName}/SeedBundle/` + Xcode Copy Bundle Resources | 仅放 `Desktop/对话`、workspace 根 `assets/img/`、`h5/assets/{prefix}_vault/` |
| 运行时展示 `photos/seed/{file}` + `resolvePhotoDisplayUrl` → data URL | WKWebView `<img src>` 回退 custom scheme 当主路径 |
| 品牌 / Launch / 氛围图落 Native Assets | 启动图仍 PLACEHOLDER 提审 |

验收：Xcode 工程树能展开看到 seed 文件；冷启动主 Tab 图文齐全。  
产包后加工对照：《H5壳Pack约束.md》「产包后共性」#3（Seed / 品牌图在 iOS 工程内）。
