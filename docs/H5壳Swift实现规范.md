# H5 壳 Swift 实现规范

> 本文面向 `h5_swift_shell` 的 Swift Programmer。在 `h5_flutter_shell` 文档已覆盖的通用约定基础上，补充 iOS Swift WKWebView 壳的锁定实现细节。
> 
> 本规范基于 `Prepoo-Swift`（标准英文命名、集中式 `Bridge/`、`WKScriptMessageHandler`）与 `Mockoo-Swift`（德国 persona 混淆前缀、`nested_role_leaf`、iframe URL scheme 拦截）两个工程抽象。

---

## 1. 技术站锁定与 Bridge 抽卡

`pack_type == h5_swift_shell` 时：

| 维度 | 来源 | 说明 |
|------|------|------|
| `webviewEngine` | **pack_type 锁定** | 恒为 `wkwebview_swift` |
| `bridgeCallStyle` | **task.csv / bridgeDeckSelections 抽卡** | 见 §4.1 卡面矩阵 |
| `bridgeCallbackStyle` | 抽卡 | 见 §4.3 卡面矩阵 |
| `bridgeEnvelope` | 抽卡 | 见 §4.4 卡面矩阵 |
| `mediaServe` | 抽卡 | 见 §5 卡面矩阵 |
| `bridgeErrorCode` | 抽卡 | 见 §4.5 卡面矩阵 |
| `bridgeInjectTiming` | 抽卡 | 见 §4.6 卡面矩阵 |

**MUST**：读取 `本包登记信息.json` → `bridgeDeckSelections`，按抽中卡面实现；禁止默认回退到单一 canonical 路径。H5 `bridge.ts` 须与抽中 `bridgeEnvelope` / `bridgeCallStyle` 对齐。

> Bridge **通道名**（`{appLower}Bridge` / `{appLower}BridgeCallback`）仍由 App 名锁定，见《H5-Bridge协议.md》§5 — 与 `bridgeCallStyle` 机制选择正交。

### 平台锁定

| 项 | 值 | 说明 |
|----|-----|------|
| `IPHONEOS_DEPLOYMENT_TARGET` | **13.0** | 厂包 `project.yml` 与交付脚本强制 |
| `TARGETED_DEVICE_FAMILY` | **1** | 仅 iPhone；禁止 iPad |
| App 入口 | UIKit `AppDelegate` | **禁止** SwiftUI `App`/`WindowGroup`（最低 iOS 14） |
| IAP | StoreKit 1 | 兼容 iOS 13；禁止裸用 StoreKit 2 |
| 相册 | `UIImagePickerController` | 兼容 iOS 13；禁止裸用 PHPicker |

---

## 2. 项目骨架

### 2.1 基础夹板（直接拷贝）

见 `data/static/templates/swift_shell/`。基础夹板只包含**不受编程风格与命名规则影响**的资产：

- `Assets.xcassets/`（图标、启动背景、占位图）
- `Info.plist`
- `{{APP_NAME}}.html`（H5 入口占位，含锁定 Bridge 的 JS bootstrap）
- `本包登记信息.json`

### 2.2 需场包生成的 Swift 代码

拷贝夹板后，Programmer Agent 根据 `task.csv` 的 **编程风格** 与 **命名规则** 生成：

- `{{APP_NAME}}App.swift`
- WebViewController / View / Presenter / ViewModel
- Bridge Handler / Interactor
- Asset Scheme Handler
- File Vault / Permission Manager / IAP Manager
- 模块目录（如 `Bridge/`、`Modules/` 或 `{prefix}_module_a/{prefix}_module_a_bay/` 等）

参考实现见 `data/static/templates/swift_shell/examples/standard/`（Prepoo 风格）与 `examples/german_persona/`（Mockoo 风格文档）。

---

## 3. WKWebView 配置

```swift
let config = WKWebViewConfiguration()
config.allowsInlineMediaPlayback = true

// 1. 注册自定义 asset scheme
let assetHandler = {{APP_NAME}}AssetScheme()
config.setURLSchemeHandler(assetHandler, forURLScheme: {{APP_NAME}}ShellConfig.assetScheme)

// 2. 注入 bridge bootstrap（atDocumentStart）
let bridgeBootstrap = """
window.__{{APP_NAME_LOWER}}Native = true;
window.{{APP_NAME_LOWER}}Bridge = {
    postMessage: function(msg) {
        window.webkit.messageHandlers.{{APP_NAME_LOWER}}Bridge.postMessage(msg);
    }
};
"""
let userScript = WKUserScript(
    source: bridgeBootstrap,
    injectionTime: .atDocumentStart,
    forMainFrameOnly: true
)
config.userContentController.addUserScript(userScript)

// 3. 注册 message handler（WKScriptMessageHandler 风格）
let bridgeHandler = WebBridgeHandler(presentingVC: self)
config.userContentController.add(bridgeHandler, name: "{{APP_NAME_LOWER}}Bridge")

webView = WKWebView(frame: .zero, configuration: config)
```

### 3.1 关键配置项

| 项 | 要求 |
|----|------|
| `allowsInlineMediaPlayback` | `true`，支持内联播放 |
| `mediaTypesRequiringUserActionForPlayback` | 按需设为 `[]`，避免视频必须全屏 |
| `userContentController` | 注入 bridge + 可能的 viewport/safe-area 脚本 |
| `scrollView.bounces` | 按产品需求；通常关闭或仅底部反弹 |
| `scrollView.showsVerticalScrollIndicator` | `false`（配合 H5 去风味） |
| `backgroundColor` | `.clear` 或与首屏同色 |

---

## 4. Bridge 实现（按 bridgeDeckSelections 抽卡）

### 4.1 bridgeCallStyle 卡面

| 抽中卡 | Swift 实现要点 |
|--------|----------------|
| `WKScriptMessageHandler.postMessage(JSON)` | `userContentController.add(handler, name: "{appLower}Bridge")`；H5 `window.webkit.messageHandlers.{appLower}Bridge.postMessage({ id, action, payload })` |
| `window.webkit.messageHandlers.{prefix}.postMessage(JSON)` | 同上；handler name 仍用 App 名派生通道，**不用** dartCodePrefix |
| `WKUserContentController named handler + JSON body` | 同上 + handler 类独立文件；body 统一 `[String: Any]` 解析 |
| `custom URL scheme intercept (app-bridge://)` | `decidePolicyFor navigationAction` 拦截 `app-bridge://` query；取消导航；解析 `callbackId/action/data` |
| `postMessage + CustomEvent bridgeReady` | WKScriptMessageHandler 为主路径；注入脚本在 bootstrap 末尾 `dispatchEvent(new CustomEvent('bridgeReady'))` |

### 4.2 方式 A 示例：WKScriptMessageHandler（Prepoo 风格）

H5 → Native：

```javascript
window.webkit.messageHandlers.prepBridge.postMessage({
    id: 'cb_1',
    action: 'pickImage',
    payload: { source: 'camera' }
});
```

Native 处理：

```swift
func userContentController(_ userContentController: WKUserContentController,
                           didReceive message: WKScriptMessage) {
    guard let body = message.body as? [String: Any],
          let id = body["id"] as? String,
          let action = body["action"] as? String else { return }
    let payload = body["payload"]
    // route by action
}
```

Native → H5：

```swift
func sendSuccess(id: String, data: [String: Any]) {
    let script = "window.prepBridgeCallback('\(id)', { data: \(json(data)) })"
    webView.evaluateJavaScript(script, completionHandler: nil)
}
```

### 4.2 方式 B：iframe URL Scheme 拦截（Mockoo 风格）

H5 → Native：

```javascript
function callNative(action, data) {
    return new Promise((resolve, reject) => {
        const callbackId = 'cb_' + (++seq);
        pending[callbackId] = { resolve, reject };
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = 'app-bridge://invoke?callbackId=' + callbackId
            + '&action=' + encodeURIComponent(action)
            + '&data=' + encodeURIComponent(JSON.stringify(data));
        document.body.appendChild(iframe);
        setTimeout(() => iframe.remove(), 100);
    });
}
```

Native 拦截：

```swift
func webView(_ webView: WKWebView,
             decidePolicyFor navigationAction: WKNavigationAction,
             decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
    if let url = navigationAction.request.url, url.scheme == "app-bridge" {
        // parse callbackId / action / data from URL query
        decisionHandler(.cancel)
        return
    }
    decisionHandler(.allow)
}
```

Native → H5 同样走 `evaluateJavaScript("window.__xucKitReply(callbackId, envelope)")`。

### 4.3 bridgeCallbackStyle 卡面

| 抽中卡 | Swift 实现要点 |
|--------|----------------|
| `evaluateJavaScript(callbackId(data))` | `webView.evaluateJavaScript("window.{appLower}BridgeCallback('\(id)', \(json))")` |
| `WKWebView.evaluateJavaScript completionHandler` | 同上 + `completionHandler` 记录失败日志 |
| `callAsyncJavaScript Promise resolve (iOS 14+)` | `webView.callAsyncJavaScript("window.{appLower}BridgeCallback", arguments: [id, envelope], ...)` |
| `injected JS dispatchEvent(NativeReply)` | 注入 `window.dispatchEvent(new CustomEvent('NativeReply', { detail: { id, data } }))` |
| `callbackId Map + evaluateJavaScript` | Native 侧 `pendingCallbacks: [String: (Result) -> Void]` + evaluateJavaScript 触发 H5 全局回调 |
| `URL scheme callback (app-callback://)` | `loadRequest(URL(string: "app-callback://\(id)?payload=..."))` 或 iframe 导航；H5 监听 hash/iframe |

### 4.4 bridgeEnvelope 卡面

| 抽中卡 | 字段形状 |
|--------|----------|
| `{action,data} minimal` | 请求 `{ id, action, payload }`；回复 `{ id, data }` / `{ id, error }` |
| `RPC {jsonrpc,method,params,id}` | `{ jsonrpc: "2.0", method, params, id }` |
| `versioned envelope {v,action,payload,callbackId}` | `{ v: 1, action, payload, callbackId }` |
| `method+args split fields` | `{ id, method, args: [...] }` |
| `URL query flattened` | scheme 拦截时 query `action` / `data` / `callbackId` 扁平键值 |

### 4.5 bridgeErrorCode 卡面

| 抽中卡 | 示例 |
|--------|------|
| `numeric codes (0/-1/-2)` | `{ code: -1, message: "..." }` |
| `string enum (PERMISSION_DENIED)` | `{ code: "PERMISSION_DENIED" }` |
| `HTTP-like (400/403/500)` | `{ code: 403, message: "..." }` |
| `gRPC-style (INVALID_ARGUMENT)` | `{ code: "INVALID_ARGUMENT" }` |
| `short prefix+number (E101)` | `{ code: "E101" }` |

### 4.6 bridgeInjectTiming 卡面

| 抽中卡 | 注入点 |
|--------|--------|
| `WKUserScript atDocumentStart` | `injectionTime: .atDocumentStart` |
| `WKUserScript atDocumentEnd` | `injectionTime: .atDocumentEnd` |
| `didFinish navigation inject polyfill` | `webView(_:didFinish:)` 内 `evaluateJavaScript` 一次性注入 |
| `configuration.userContentController before first load` | `WKWebViewConfiguration` 创建后、`loadRequest` 前 `addUserScript` |
| `bundled bridge.js in main bundle preload` | Bundle 读 `bridge.js` → `WKUserScript` atDocumentStart |

### 4.7 回调信封（与 envelope 卡面对齐）

成功：

```json
{ "data": { "path": "selfies/week_1.jpg" } }
```

错误：

```json
{ "error": { "code": "PERMISSION_DENIED", "message": "No camera permission" } }
```

> 注意：Mockoo 实际使用 `{ data, error }` 顶层字段；Prepoo 使用 `{ id, data }` / `{ id, error }`。新包须与 `bridgeEnvelope` 维度及 H5 `bridge.ts` 对齐。

---

## 5. 本地资源服务（mediaServe 抽卡）

### 5.1 mediaServe 卡面

| 抽中卡 | Swift 实现要点 |
|--------|----------------|
| `loadFileURL bundle resource` | `webView.loadFileURL(bundleURL, allowingReadAccessTo: bundleRoot)` 仅 seed；用户媒体仍走 Bridge |
| `WKURLSchemeHandler local vault` | `config.setURLSchemeHandler(handler, forURLScheme: "{appSlug}-asset")` |
| `custom scheme handler (app-asset://)` | 同上；scheme 名写入 `本包登记信息.json` → `assetScheme` |
| `readFile Bridge base64 inline` | Bridge `readFile` action 读 Documents → base64 回 H5（小文件 only） |
| `NSURL fileURLWithPath vault relative` | Scheme handler 内 `FileManager` 拼 Documents 相对路径 |

### 5.2 注册（WKURLSchemeHandler 卡面）

```swift
config.setURLSchemeHandler(assetHandler, forURLScheme: "prepoo-asset")
```

### 5.3 H5 使用

```html
<img src="prepoo-asset://local/selfies/week_1.jpg">
<audio src="prepoo-asset://local/voice/note_1.m4a">
```

### 5.4 Native 解析

```swift
class {{APP_NAME}}AssetScheme: NSObject, WKURLSchemeHandler {
    func webView(_ webView: WKWebView, start urlSchemeTask: WKURLSchemeTask) {
        guard let url = urlSchemeTask.request.url,
              url.scheme == {{APP_NAME}}ShellConfig.assetScheme else {
            urlSchemeTask.didFailWithError(URLError(.badURL))
            return
        }
        let relPath = url.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        // 1. 先读 Documents
        if let data = {{APP_NAME}}FileVault.read(relPath) {
            urlSchemeTask.didReceive(HTTPURLResponse(...))
            urlSchemeTask.didReceive(data)
            urlSchemeTask.didFinish()
            return
        }
        // 2. fallback 读 Bundle seed
        if let data = {{APP_NAME}}BundleMedia.read(relPath) {
            // ...
            return
        }
        urlSchemeTask.didFailWithError(URLError(.fileDoesNotExist))
    }
}
```

### 5.5 安全要求

- 必须做路径穿越校验（禁止 `../` 超出 Documents）。
- 禁止直接回传绝对路径给 H5。
- 禁止 H5 用 `file://` 读沙盒。

---

## 6. 启动闪屏时序

目标时序：

```
iOS LaunchScreen（纯色 / 1125×2436 占位图）
  → Swift 首帧 LaunchVeil（与 LaunchScreen 同色/同图）
  → WKWebView 挂载（透明，在 Veil 下 loadRequest(h5EntryUrl)）
  → 远程 H5 splash 双 rAF → bridge shellReady
  → 撤 LaunchVeil，露出已绘制的 WebView
```

### 6.1 Swift 壳必做

1. `LaunchScreen.storyboard` 全屏 **1125×2436** 图（加工后换真图），与 H5 首屏背景一致。
2. `AppDelegate`（`{{APP_NAME}}App.swift`）启动后立即挂载根 `UIViewController` 并显示 `{{APP_NAME}}LaunchVeil`。
3. Launch / Veil `UIImageView`：**`contentMode = .scaleAspectFill`** + clipsToBounds；**禁止** `scaleToFill` / `scaleAspectFit`。
4. `WebViewController` 创建 WKWebView 时背景透明。
5. `viewDidLoad` 中 `loadRequest(h5EntryUrl)`。
6. Bridge 收到 `shellReady` 后，延迟一帧再撤 Veil。
7. **CDN-safe 加载**（`WebShellViewModel`）：`loadTimeout=30s` 仅用于 provisional；`didFinish` 后取消 provisional 定时器并启用 `shellReadyFallback=8s`；`mainFrameDidFinish` 防误报 offline；`WebViewController` 忽略 `NSURLErrorCancelled(-999)`；远程 `useProtocolCachePolicy`。
8. 加载失败显示英文 Retry 页，重新 `loadRequest`。
9. **验收**：删 App 重装 → **首次**冷启动无缩小弹回（见《H5壳启动闪屏规范》）。

### 6.2 H5 必做

1. entry 内联 bridge bootstrap。
2. `boot()` 立即执行，禁止 `setTimeout(boot, ...)`。
3. splash `afterMount` 双 `requestAnimationFrame` 后调用 `shellReady`。

---

## 7. 去风味（Deflavor）

Swift 侧负责**容器级**去浏览器味，H5 侧负责**交互级**去风味。

### 7.1 Swift 侧常见处理

| 问题 | 实现 |
|------|------|
| 双击缩放 | 注入 JS `document.documentElement.style.touchAction = 'manipulation'`；或 swizzle 禁用双击手势 |
| 键盘辅助栏 | swizzle `WKWebView` / `WKContentView` 的 `inputAccessoryView` 返回 `nil` |
| 滚动条 | `webView.scrollView.showsVerticalScrollIndicator = false` |
| 链接长按菜单 | H5 侧 `oncontextmenu="return false"` |
| 输入框拼写红线 | H5 侧 `spellcheck="false" autocorrect="off"` |

> 警告：Mockoo 使用 method swizzle 修改 `WKWebView.init` 与 `UIView.addGestureRecognizer`，具有侵入性，可能影响全部 WKWebView 实例。新包若使用 swizzle，须评估范围。

---

## 8. IAP（StoreKit 1）

### 8.1 职责切分

| 层 | 负责 |
|----|------|
| H5 | 商店页 UI、商品列表、点击购买、Loading 遮罩、余额展示 |
| Swift Bridge | `getProducts`、`purchase`、StoreKit 1（`SKProductsRequest` / `SKPaymentQueue`）事务监听、幂等去重、回调 H5 |

### 8.2 Swift 流程

1. H5 调用 `getProducts({ productIds })` → Swift 用 `SKProductsRequest` 查询 → 回价格表。
2. H5 点击购买 → 显示全屏不可穿透 Loading → Swift `SKPaymentQueue.add(SKPayment(product:))`。
3. 成功：`finishTransaction`、去重（记录 `fulfilledTransactions`）、回调 H5 `purchaseSuccess`。
4. 用户取消：关闭 Loading，**不弹**失败弹窗。
5. 真失败：关闭 Loading，英文 Alert + 可重试。

> **禁止**裸用 StoreKit 2（`Product` / `Transaction`）— 最低系统为 iOS 13。

### 8.3 去重

```swift
private var fulfilledTransactions: Set<String> {
    get { Set(UserDefaults.standard.stringArray(forKey: "fulfilled_tx") ?? []) }
    set { UserDefaults.standard.set(Array(newValue), forKey: "fulfilled_tx") }
}
```

> 当前 Prepoo / Mockoo 均**未做服务端 receipt 验证**，仅本地去重。若业务需要服务端验单，须额外实现。

---

## 9. 文件与权限

### 9.1 文件沙盒

- 用户媒体写入 `Documents/` 子目录（如 `photos/`、`voice/`）。
- H5 只保存相对路径。
- Swift 读写时做路径穿越校验。

### 9.2 权限

| 能力 | Info.plist key |
|------|----------------|
| 相机 | `NSCameraUsageDescription` |
| 相册读取 | `NSPhotoLibraryUsageDescription` |
| 相册写入 | `NSPhotoLibraryAddUsageDescription`（iOS 14+） |
| 麦克风 | `NSMicrophoneUsageDescription` |

权限被拒时：英文单行弹窗，不跳设置。

**权限必须接到功能（20260721）**：plist 有 key 不够；H5/Bridge 须有对应入口（选图/拍照/录音），且能走完授权流。启用录音则 **录完可回放**（`playAudio` / AudioPlayer）。禁止「声明三大权限但无 UI」。

```bash
rg 'NSCamera|NSPhoto|NSMicrophone' <工作区> --glob '**/Info.plist'
rg 'pickImage|takePhoto|startRecord|playAudio' <工作区>/h5/src --glob '*.{ts,vue}'
```

---

## 10. 登记信息字段

`本包登记信息.json` 须包含：

```json
{
  "appName": "Prepoo",
  "bundleId": "test.duckegg.ios",
  "appSlug": "prepoo",
  "packType": "h5_swift_shell",
  "shellRuntime": "swift",
  "dartCodePrefix": "erbpv",
  "bundleEntryPath": "h5_site/prepoo/index.html",
  "h5SiteRoot": "h5_site/prepoo/",
  "h5SiteEntry": "index.html",
  "h5EntryUrl": "https://test.darin.beauty/prepoo/",
  "h5EntryUrlDev": "http://127.0.0.1:5174/",
  "h5EntryUrlProd": "https://test.darin.beauty/prepoo/",
  "assetScheme": "prepoo-asset",
  "bridgeScheme": "app-bridge",
  "bridgeDeckSelections": { ... },
  "bridgeCapabilities": ["shellReady", "pickImage", "purchase", ...]
}
```

---

## 11. 命名约定（深度混淆）

### 11.1 标准风格（美国人 / 英国人 / 中国人）

- 目录语义化：`Bridge/`、`Modules/WebContent/`、`Modules/WebView/`
- 文件/类名 PascalCase：`WebBridgeHandler.swift`、`PrepooWebViewDeflavor.swift`

### 11.2 德国 persona 风格

- 前缀：`{prefix}`（如 `xucfw`）
- 模块目录：`{prefix}_{module_name}/` + `{prefix}_{module_name}_bay/`
- 类名：`Xucfw<Role><Metaphor><Suffix>`，如 `XucfwPrismNestAnchorLayer`、`XucfwHttpSlotAnchorInteractor`

### 11.3 深度命名（所有 persona — MANDATORY）

`transform_identifier(ruleKey, meta, entity, semantic, salt)` 须覆盖 **每一个可命名位置**，不仅是 class/file：

| entity | 示例 semantic | 混淆前（禁止留 canonical） | 混淆后示例 |
|--------|---------------|---------------------------|------------|
| field | loadTimeout | `private let loadTimeout: TimeInterval = 30` | `private let sapLoadTimeoutMdm: TimeInterval = 28` |
| field | pathMonitor | `private var pathMonitor: NWPathMonitor?` | `private var zsrPathMonitorFzx: NWPathMonitor?` |
| local | timeout | `let timeout = loadTimeout` | `let mdmTimeoutSap = sapLoadTimeoutMdm` |
| method | scheduleLoadTimeout | `func scheduleLoadTimeout()` | `func yejScheduleLoadTimeoutDb()` |
| param | decisionHandler | 仅当非 SDK 协议签名时可改内名 | — |

- **常量取值**可与语义名一起差异化（如 `30` → `28`，`8` → `6`），但须保持行为等价。
- **英文 UI 文案 / 注释**：每包须重写，禁止跨包复制 `"Page Not Found"`、`~450KB` 等共享字符串。
- 完整规则见《命名混淆规则.md》§Native shell identifier scope。

---

## 12. H5 monolith 构建

- Vite + `vite-plugin-singlefile`，`inlineDynamicImports: true`。
- 构建产物 `dist/index.html` 复制为 `ios/{{APP_NAME}}/{{APP_NAME}}.html`。
- 线上环境壳通常 `loadRequest(h5EntryUrl)` 加载远程 URL；本地包作为 fallback / 离线备用。

---

## 13. 交付自检

- [ ] `packType` 写为 `h5_swift_shell`
- [ ] `webviewEngine` 锁定为 `wkwebview_swift`
- [ ] Bridge handler 注册先于 `loadRequest`
- [ ] `shellReady` 收到后才撤 LaunchVeil
- [ ] Launch/Veil **`scaleAspectFill`**；删 App 重装首次冷启动无缩小弹回
- [ ] 自定义 asset scheme 能服务 Documents 和 Bundle seed
- [ ] Seed / 品牌图在 `ios/` 工程内可见（非仅对话目录）
- [ ] 权限拒弹窗英文单行，不跳设置；**权限 key ↔ 功能入口对齐**
- [ ] 录音（若启用）录完可回放
- [ ] IAP 取消购买无失败弹窗，真失败英文 Alert
- [ ] 无 `<input type="file">`、无系统 alert、无 base64 大图
- [ ] H5 首屏底色与 LaunchScreen / LaunchVeil 一致
- [ ] Swift 侧无可见业务 UI（Welcome、TabBar、Shop 等）
- [ ] 协议有在线链时走 `openExternalUrl` 外开（见 Legal 弹层规范模式 B）
