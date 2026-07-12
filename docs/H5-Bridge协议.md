# H5-Bridge 协议

`h5_shell` 包 H5 ↔ Flutter 能力契约。每包 **实际调用/回调/封装/回显** 以 `task.csv` 抽到的七维为准；本文定义能力清单与字段约定。

---

## 1. 能力清单

| ID | 方法名 | 方向 | 说明 |
|----|--------|------|------|
| B01 | `pickImage` | H5→壳 | 相机/相册选图，落盘 Documents，回相对路径 |
| B02 | `saveImageToAlbum` | H5→壳 | 将 Documents 内图片保存到系统相册 |
| B03 | `startRecord` / `stopRecord` | H5→壳 | 录音起止，回相对路径 |
| B04 | `playAudio` | H5→壳 | 播放 Documents 内音频 |
| B05 | `readFile` / `writeFile` | H5→壳 | 读写 Documents（相对路径） |
| B06 | `getDeviceInfo` | H5→壳 | safeArea、版本、语言等 |
| B07 | `openExternalUrl` | H5→壳 | 外链（SFSafariViewController / 系统浏览器） |
| B08 | `copyToClipboard` | H5→壳 | 剪贴板 |
| B09 | `purchase` | H5→壳 | 拉起 StoreKit（见《H5壳IAP协议.md》） |
| B10 | `getLegalText` | H5→壳（可选） | 返回与 MD 同步的全文；**优先** H5 vault `app_legal_bundled.js`（由 `sync_h5_legal_bundled.py` 生成；H5 站点统一文件名，不随壳 prefix 变化） |
| B11 | `reload` / `goBack` | H5→壳 | WebView 导航控制 |
| B12 | `shellReady` | H5→壳 | H5 splash 首帧绘制后上报；Flutter 撤 LaunchVeil（**每包必实现**） |

PM 在 `功能文档.md` 勾选本包启用子集；未启用能力 **不得** 实现空桩以外的业务逻辑。`shellReady` 为 h5_shell 启动时序**固定能力**，不随 CSV 抽卡省略。

---

## 2. 路径约定

- 仅存 **`getApplicationDocumentsDirectory()` 下相对路径**（如 `selfies/week_1_1719000000.jpg`）。
- **禁止** 向 H5 回传绝对路径。
- **禁止** 用 `file://` 让 H5 直接读沙盒（须走 `mediaServe` 方案）。

---

## 3. 回调信封（按 `bridgeEnvelope` 维度实现）

实现时从 CSV 抽到的一种为准，示例（版本化信封）：

```json
{
  "v": 1,
  "action": "imageSelected",
  "callbackId": "cb_42",
  "payload": { "path": "selfies/week_1_1719000000.jpg" },
  "error": null
}
```

错误时：

```json
{
  "v": 1,
  "action": "pickImage",
  "callbackId": "cb_42",
  "payload": null,
  "error": { "code": "PERMISSION_DENIED", "message": "No camera permission" }
}
```

---

## 4. 错误码（按 `bridgeErrorCode` 维度）

| 场景 | 建议 code |
|------|-----------|
| 用户取消 | `USER_CANCELLED` |
| 相机权限拒 | `PERMISSION_DENIED` |
| 相册权限拒 | `PERMISSION_DENIED` |
| 无相机硬件 | `CAMERA_UNAVAILABLE` |
| 文件不存在 | `FILE_NOT_FOUND` |
| IAP 不可用 | `IAP_UNAVAILABLE` |
| 未知错误 | `UNKNOWN` |

权限拒弹窗文案：**英文单行**，不跳设置（对齐工具包 §7）。

---

## 5. 七维与实现映射

| 维度 | Programmer 须 |
|------|----------------|
| `webviewEngine` | 选定主 WebView 插件及初始化方式 |
| `bridgeCallStyle` | H5 侧调用入口（如 `callHandler` / `postMessage`） |
| `bridgeCallbackStyle` | 壳侧回传 H5 的方式 |
| `bridgeEnvelope` | 序列化/反序列化规则 |
| `mediaServe` | 图片/音频 URL 供 H5 `<img>` / `<audio>` 使用 |
| `bridgeErrorCode` | 错误对象形态 |
| `bridgeInjectTiming` | `bridge.js` 或 handler 注册时机 |

详细逐步流程见《H5壳业务流程文字版.md》。

---

## 6. 登记

`本包登记信息.json` 须含：

```json
{
  "bridgeDeckSelections": {
    "webviewEngine": "...",
    "bridgeCallStyle": "...",
    "bridgeCallbackStyle": "...",
    "bridgeEnvelope": "...",
    "mediaServe": "...",
    "bridgeErrorCode": "...",
    "bridgeInjectTiming": "..."
  },
  "bridgeCapabilities": ["pickImage", "purchase", "..."]
}
```


**h5_shell 协议展示**：Privacy/Terms 须在 **H5 弹窗或全屏页** 展示内置英文正文；禁止 `openExternalUrl` / 外链 HTTPS 作为协议主路径。
