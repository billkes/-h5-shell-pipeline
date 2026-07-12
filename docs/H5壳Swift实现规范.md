# H5 壳 Swift 实现规范

> 本文面向 `h5_swift_shell` 的 Swift Programmer。在 `h5_flutter_shell` 文档已覆盖的通用约定基础上，补充 iOS Swift WKWebView 壳的锁定实现细节。
> 
> 本规范基于 `Prepoo-Swift`（标准英文命名、集中式 `Bridge/`、`WKScriptMessageHandler`）与 `Mockoo-Swift`（德国 persona 混淆前缀、`nested_role_leaf`、iframe URL scheme 拦截）两个工程抽象。

---

## 1. 技术站锁定

`pack_type == h5_swift_shell` 时，以下七维由 `pack_type.py` 锁定，**不随 CSV Bridge deck 抽卡变化**：

| 维度 | 锁定值 | 说明 |
|------|--------|------|
| `webviewEngine` | `wkwebview_swift` | `WKWebView` + `WKWebViewConfiguration` |
| `bridgeCallStyle` | `WKScriptMessageHandler.postMessage(JSON)` 或 `iframe URL scheme` | 两种实现均被允许，但 **每包只选一种**；默认推荐 `WKScriptMessageHandler` |
| `bridgeCallbackStyle` | `evaluateJavaScript(callbackId(data))` | Native 回传 H5 统一走 `webView.evaluateJavaScript` |
| `bridgeEnvelope` | `{action,data}` minimal 或版本化信封 | 与 H5 约定一致即可 |
| `mediaServe` | `WKURLSchemeHandler local vault` | 自定义 scheme（如 `prepoo-asset://`、`mockoo-asset://`） |
| `bridgeErrorCode` | `string enum` 或 gRPC 风格 | 与 H5 约定一致 |
| `bridgeInjectTiming` | `WKUserScript atDocumentStart` | 在 `viewDidLoad` 前注入 bridge bootstrap |

`本包登记信息.json` 中的 `bridgeDeckSelections` 须如实填写上述锁定值，`bridgeCapabilities` 须与功能文档勾选子集一致。

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

## 4. Bridge 实现

### 4.1 方式 A：WKScriptMessageHandler（推荐，Prepoo 风格）

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

### 4.3 回调信封

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

## 5. 本地资源服务（WKURLSchemeHandler）

### 5.1 注册

```swift
config.setURLSchemeHandler(assetHandler, forURLScheme: "prepoo-asset")
```

### 5.2 H5 使用

```html
<img src="prepoo-asset://local/selfies/week_1.jpg">
<audio src="prepoo-asset://local/voice/note_1.m4a">
```

### 5.3 Native 解析

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

### 5.4 安全要求

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

1. `LaunchScreen.storyboard` 全屏纯色或占位图，与 H5 首屏背景一致。
2. `App` 启动后立即显示 `{{APP_NAME}}LaunchVeil`（`UIViewController` 或 SwiftUI `View`）。
3. `WebViewController` 创建 WKWebView 时背景透明。
4. `viewDidLoad` 中 `loadRequest(h5EntryUrl)`。
5. Bridge 收到 `shellReady` 后，延迟一帧再撤 Veil。
6. 加载失败显示英文 Retry 页，重新 `loadRequest`。

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

## 8. IAP（StoreKit 2）

### 8.1 职责切分

| 层 | 负责 |
|----|------|
| H5 | 商店页 UI、商品列表、点击购买、Loading 遮罩、余额展示 |
| Swift Bridge | `getProducts`、`purchase`、StoreKit 2 事务监听、幂等去重、回调 H5 |

### 8.2 Swift 流程

1. H5 调用 `getProducts({ productIds })` → Swift 用 `Product.products(for:)` 查询 → 回价格表。
2. H5 点击购买 → 显示全屏不可穿透 Loading → Swift 调用 `product.purchase()`。
3. 成功：验证交易状态、去重（记录 `fulfilledTransactions`）、回调 H5 `purchaseSuccess`。
4. 用户取消：关闭 Loading，**不弹**失败弹窗。
5. 真失败：关闭 Loading，英文 Alert + 可重试。

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
  "bundleEntryPath": "Prepoo.html",
  "h5SiteRoot": "h5_site/",
  "h5SiteEntry": "erbpv_entry.htm",
  "h5EntryUrl": "https://test.darin.beauty/prepoo/erbpv_entry.htm",
  "h5EntryUrlDev": "http://127.0.0.1:5174/",
  "h5EntryUrlProd": "https://test.darin.beauty/prepoo/erbpv_entry.htm",
  "assetScheme": "prepoo-asset",
  "bridgeScheme": "app-bridge",
  "bridgeDeckSelections": { ... },
  "bridgeCapabilities": ["shellReady", "pickImage", "purchase", ...]
}
```

---

## 11. 命名约定

### 11.1 标准风格（美国人 / 英国人 / 中国人）

- 目录语义化：`Bridge/`、`Modules/WebContent/`、`Modules/WebView/`
- 文件/类名 PascalCase：`WebBridgeHandler.swift`、`PrepooWebViewDeflavor.swift`

### 11.2 德国 persona 风格

- 前缀：`{prefix}`（如 `xucfw`）
- 模块目录：`{prefix}_{module_name}/` + `{prefix}_{module_name}_bay/`
- 类名：`Xucfw<Role><Metaphor><Suffix>`，如 `XucfwPrismNestAnchorLayer`、`XucfwHttpSlotAnchorInteractor`

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
- [ ] 自定义 asset scheme 能服务 Documents 和 Bundle seed
- [ ] 权限拒弹窗英文单行，不跳设置
- [ ] IAP 取消购买无失败弹窗，真失败英文 Alert
- [ ] 无 `<input type="file">`、无系统 alert、无 base64 大图
- [ ] H5 首屏底色与 LaunchScreen / LaunchVeil 一致
- [ ] Swift 侧无可见业务 UI（Welcome、TabBar、Shop 等）
