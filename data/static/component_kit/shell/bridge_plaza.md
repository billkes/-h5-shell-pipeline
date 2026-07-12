# Bridge Plaza

## 组件 ID

`shell/bridge_plaza`

## 分类

`shell`（h5_shell 专用）

## 适用包类型

| 包类型 | 使用场景 | 实现要点 |
|--------|---------|---------|
| h5_shell | 隐藏 Bridge 验权页 | `#/plaza`；Settings 长按版本号 3s 进入 |

## 变体

| 变体 | 说明 |
|------|------|
| `standard` | 半硬编码按钮矩阵（按 bridgeCapabilities） |
| `with-video` | 额外 `pickVideo` 按钮 |

## 注意事项

1. **非主路径**：不进 Tab；提审包保留但隐藏入口。
2. 按钮区引用 `primitives/button`；结果区引用 `shell/bridge_toast` + `shell/permission_gate`。
3. 详细规范与按钮矩阵见《H5壳广场页规范.md》。

## 踩坑与规避

| 坑 | 规避 |
|---|---|
| 浏览器开发时 Bridge 报错 | 预期；真机/模拟器经壳 WebView 验权 |
| 审核员看到广场占主导航 | 仅 Settings 长按版本号进入，不进 Tab |

## 依赖

- `primitives/button`
- `shell/bridge_toast`
- `shell/permission_gate`
- `data_display/media_picker`（选图/视频）

## H5 落盘规则

- 路由：`#/plaza`
- render 函数：`renderPlaza` 或 kit 命名空间等价物
- class 前缀：`c-{prefix}-plaza-*`
- Settings 页：版本号 `onLongPress` / 3s timer → navigate plaza

## 实现过程（思路，无代码）

1. 读 `bridgeCapabilities` 决定按钮子集；
2. 每按钮调 Bridge + 三态 UI；
3. 成功时按 `mediaServe` 预览 path；
4. 隐藏入口仅 Settings 长按版本号。

## 导航

- [[component_kit/shell/bridge_toast]]
- [[component_kit/shell/permission_gate]]
- [H5壳广场页规范](../../../../docs/H5壳广场页规范.md)
