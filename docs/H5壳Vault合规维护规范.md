# h5_shell Vault 合规维护规范

> 本文件是 h5_shell 带壳 H5 包的 **流水线维护者约束**，不是仓库级 Cursor 规则。
> 产包时，其约束会下沉为每个 h5_shell 包 `.cursor/rules/h5-vault-compliance.mdc`。

改以下任一处时，须 **同步** gate、prompt、包级 `h5-vault-compliance.mdc` 生成逻辑：

| 区域 | 路径 |
|------|------|
| 内容 sync | `scripts/batch/sync_h5_legal_bundled.py` |
| UI 校验 | `scripts/batch/h5_legal_ui.py` · `verify_h5_legal_ui()`（行为门禁，无视觉 kit） |
| 包级铁律 | `scripts/batch/cursor_rules.py` → `h5-vault-compliance.mdc` |
| 弹层规范 | `docs/H5壳Legal弹层规范.md` |
| 去风味规范 | `docs/H5去风味规范.md` |

**禁止**只改单个 output 包（如 Pawioo）而不更新 gate / `cursor_rules.py`。

**去风味**：Legal 滚动 **禁止** web 滚动条（`display: block`）；仅 mask 渐变。美化不得突破《H5去风味规范.md》§4。
