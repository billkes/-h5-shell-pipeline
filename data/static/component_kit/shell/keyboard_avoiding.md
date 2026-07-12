# Keyboard Avoiding

## 组件 ID

`shell/keyboard_avoiding`

## 分类

`shell`

## 适用包类型

| 包类型 | 使用场景 | 实现要点 |
|--------|---------|---------|
| flutter_tool | 表单页、含 TextField 的 sheet | `resizeToAvoidBottomInset` + SafeArea |
| h5_shell | 输入聚焦时 viewport 调整 | viewport meta + scroll |
| flutter_contentpack | 发布表单 | 同 flutter_tool |

## 变体

| 变体 | 说明 |
|------|------|
| `scaffold` | Scaffold 级避让 |
| `sheet` | bottom_sheet 内避让 |

## 注意事项

1. **Flutter：`Scaffold(resizeToAvoidBottomInset: true)` + `MediaQuery.viewInsets`**。
2. **pinned CTA 须在键盘上方**。
3. **H5：viewport meta + focus 时 `scrollIntoView`**。
4. **禁止 full dispatch 刷新**（brain §6）。

## 踩坑与规避

| 坑 | 规避 |
|---|---|
| input 聚焦被键盘盖住 | `resizeToAvoidBottomInset: true` + `scrollIntoView` |
| 底部 accessory 灰条 | 壳 swizzle `inputAccessoryView` → nil（brain §4） |
| pinned CTA 被键盘顶出 | 计算 viewInsets / safe-area 固定 |
| H5 full dispatch 刷新表单 | 局部更新；禁 full dispatch |
| 多屏复制私有 KeyboardAvoiding | 统一放 `shared/{Prefix}KeyboardAvoiding.dart` |

## 落盘规则

- Flutter：`{architectureFolders.views}/shared/{Prefix}KeyboardAvoiding.dart`；封装 `Scaffold` + `Padding(viewInsets)`
- H5：viewport meta + `el.scrollIntoView({block:'center'})` on focus

## 依赖

- baseline：见 Flutter §Flutter
- brain：`h5-deflavor-interaction-pitfalls` §4、§6

## 实现过程（思路，无代码）

1. 选变体；
2. Flutter viewInsets padding；
3. H5 scrollIntoView；
4. accessory 由壳 swizzle。

## 组件自身需要去风味的点

- 禁 full dispatch 刷新预览（brain §6）。

## 导航

- [[component_kit/baseline]]
- [工具包Flutter产品要求 §5.3 键盘收起](../../../../docs/工具包Flutter产品要求.md)
- 全局大脑：`h5-deflavor-interaction-pitfalls-20260707`
