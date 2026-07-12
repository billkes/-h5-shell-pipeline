# 风格示例（参考 / 扩展）

本目录保存 `h5_swift_shell` 在不同 **编程风格 + 命名规则** 下的参考实现与说明。

> **注意**：基础夹板 `../{{APP_NAME}}/ios/{{APP_NAME}}/` 已包含**完整可构建**的 Swift 实现（标准英文命名）。场包时直接拷贝该基础夹板即可产出可构建的壳。
>
> `examples/` 仅用于：
> - 理解 Prepoo-Swift（standard）与 Mockoo-Swift（german_persona）的结构差异
> - 未来扩展 `apply.py --style` 时提供源码蓝本

## 子目录

- `standard/` — 标准英文命名、集中式 `Bridge/`（对应 `Prepoo-Swift`）
- `german_persona/` — 德国 persona 混淆前缀、`nested_role_leaf` 分散模块（对应 `Mockoo-Swift`）
