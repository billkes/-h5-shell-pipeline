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

### Swift 壳锁定值

`pack_type == h5_swift_shell` 时，七维由 `pack_type.py` 锁定，**不随 CSV 抽卡变化**：

| 维度 | 锁定值 |
|------|--------|
| `webviewEngine` | `wkwebview_swift` |
| `bridgeCallStyle` | `WKScriptMessageHandler.postMessage(JSON)`（默认）或 `iframe URL scheme` 拦截 |
| `bridgeCallbackStyle` | `evaluateJavaScript(callbackId(data))` |
| `bridgeEnvelope` | 与 H5 约定一致（minimal 或版本化） |
| `mediaServe` | `WKURLSchemeHandler local vault`（自定义 scheme，如 `{appslug}-asset://`） |
| `bridgeErrorCode` | 与 H5 约定一致（string enum 或 gRPC 风格） |
| `bridgeInjectTiming` | `WKUserScript atDocumentStart` |

详细实现见《H5壳Swift实现规范.md》；逐步流程见《H5壳业务流程文字版.md》。

### 通道命名（LOCKED · native ↔ H5 必须逐字一致）

WebView 只注册 **一个** message handler。H5 与壳的 **通道名 / 回调名 / 信封** 必须完全一致，否则壳收不到消息，bridge 调用会 **静默回落到 H5 stub**（IAP / 设备信息 / 存图全部失效，且无任何报错）。

| 项 | 值 | 说明 |
|----|----|------|
| 通道名 | `{appNameLower}Bridge` | `appNameLower = appName.lower()`（如 `Monthio` → `monthioBridge`）。**禁止**由代码前缀派生（`{prefix}Bridge` ❌） |
| H5 发送 | `window.{appNameLower}Bridge.postMessage({ id, action, payload })` | 壳在 `atDocumentStart` 注入 `window.{appNameLower}Bridge`；亦可 `window.webkit.messageHandlers.{appNameLower}Bridge.postMessage(...)` |
| 壳回调 | `window.{appNameLower}BridgeCallback(id, envelope)` | H5 须 **定义** 该全局函数以接收回执 |
| 请求信封 | `{ id, action, payload }`（对象，**非** JSON 字符串） | 壳按 `body["id"] / ["action"] / ["payload"]` 读取 |
| 成功回执 | `{ id, data }` | H5 以 `id` 匹配 pending，`resolve(data)` |
| 失败回执 | `{ id, error: { code, message } }` | H5 `reject(error)` |

Swift / OC 壳由模板锁定该命名（`{{APP_NAME_LOWER}}Bridge`）；**H5（Agent 产出）与 Flutter 壳（Agent 产出）须对齐同一命名，禁止各层各自造名**。产后 `native.shell.naming` 校验会对比 native 注册名与 h5/src 引用名，不一致即报违规。

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


**h5_shell 协议展示（同一入口 · 运行时二选一）**

| 分支 | 条件 | 主路径 |
|------|------|--------|
| **A 弹层**（产包默认） | 无有效 HTTPS（空串 / 未配置） | H5 `LegalOverlay` + bundled 英文正文 |
| **B 外开**（产包后填链） | `privacyUrl` / `termsUrl` 为真实 `https://` | Bridge **`openExternalUrl`** → 系统浏览器 |

**禁止**主 WKWebView 裸跳第三方域；**禁止**逻辑内写 example/TODO 等假链。流水线不产出在线 URL。细则见《H5壳Legal弹层规范》。B07 为外开能力；有在线链时真机验证。

**录音闭环**：启用 B03（`startRecord`/`stopRecord`）则须同时具备可听的 B04（`playAudio`）或 H5 `AudioPlayer` 读沙盒回放；录完不能播 = 未完成。

---

## 7. 浏览器 DEV 回落（非协议能力 · 不替代真机）

无 WKWebView / Flutter handler 时，H5 须接入 `tryBrowserBridgeMock`（snippet：`data/static/h5_snippets/bridge/browserMock.ts`）：

- 对 B01–B06 等媒体与设备类调用 **resolve** 假数据，避免 Vite 浏览器调试卡死
- **禁止**在生产壳路径执行 mock
- 真机 Plaza 仍为原生验权唯一验收

细则见《H5壳Vite工程规范.md》§Browser Bridge mock · 《H5壳广场页规范.md》。

