# H5 壳 Objective-C 实现规范

> 面向 `h5_oc_shell` 的 OC Programmer。参考实现：`data/static/templates/oc_shell/`。

---

## 1. 技术站锁定与 Bridge 抽卡

`pack_type == h5_oc_shell` 时：

| 维度 | 来源 | 说明 |
|------|------|------|
| webviewEngine | **pack_type 锁定** | 恒为 `wkwebview_oc` |
| bridgeCallStyle | **task.csv / bridgeDeckSelections 抽卡** | 见 §4 卡面矩阵 |
| bridgeCallbackStyle | 抽卡 | 见 §4 卡面矩阵 |
| bridgeEnvelope | 抽卡 | 见 §4 卡面矩阵 |
| mediaServe | 抽卡 | 见 §5 卡面矩阵 |
| bridgeErrorCode | 抽卡 | 见 §4 卡面矩阵 |
| bridgeInjectTiming | 抽卡 | 见 §4 卡面矩阵 |

**MUST**：读取 `本包登记信息.json` → `bridgeDeckSelections`，按抽中卡面实现；禁止默认单一 canonical 路径。

> Bridge 通道名仍由 App 名锁定（《H5-Bridge协议.md》§5）。`callAsyncJavaScript Promise resolve (iOS 14+)` **不会**出现在 OC 抽卡池。

### 平台锁定

| 项 | 值 |
|----|-----|
| `IPHONEOS_DEPLOYMENT_TARGET` | **13.0** |
| `TARGETED_DEVICE_FAMILY` | **1**（仅 iPhone） |

---

## 2. 项目骨架（v1 扁平 6 类）

| 类 | 职责 |
|----|------|
| `{{PREFIX_CAP}}AppDelegate` | 启动、安装 Deflavor、挂载 HostController |
| `{{PREFIX_CAP}}HostController` | WKWebView 宿主、Bridge 分发、Launch Veil、权限/IAP 调度 |
| `{{PREFIX_CAP}}LaneVault` | `WKURLSchemeHandler`（`{{PREFIX}}asset://`） |
| `{{PREFIX_CAP}}PulseCredit` | StoreKit IAP |
| `{{PREFIX_CAP}}WebViewDeflavor` | 去键盘辅助栏、禁双击缩放 |

H5 业务在 `h5_site/{{APP_SLUG}}/index.html`（或远程目录 URL `h5EntryUrl`），**禁止** Native 业务 UI。

---

## 3. 冷启动

1. 读 `register.json` / `本包登记信息.json` 的 `h5EntryUrl`
2. `WKWebView` `loadRequest` 该 URL
3. H5 首帧后调 `shellReady` → Native 撤 Launch Veil
4. Launch / Veil：**`UIViewContentModeScaleAspectFill`**；删 App 重装验 **首次**冷启动无缩小弹回（《H5壳启动闪屏规范》）

---

## 4. Bridge 卡面矩阵

### 4.1 bridgeCallStyle

| 抽中卡 | OC 实现要点 |
|--------|-------------|
| `WKScriptMessageHandler.postMessage(JSON)` | `addScriptMessageHandler:name:` → `{appLower}Bridge` |
| `window.webkit.messageHandlers.{prefix}.postMessage(JSON)` | 同上；通道名仍 App 名派生 |
| `WKUserContentController named handler + JSON body` | 独立 handler 类 + `NSDictionary` body |
| `custom URL scheme intercept (app-bridge://)` | `decidePolicyForNavigationAction` 拦截并 cancel |
| `postMessage + CustomEvent bridgeReady` | MessageHandler + 注入 `dispatchEvent(bridgeReady)` |

### 4.2 bridgeCallbackStyle

| 抽中卡 | OC 实现要点 |
|--------|-------------|
| `evaluateJavaScript(callbackId(data))` | `evaluateJavaScript:completionHandler:` |
| `WKWebView.evaluateJavaScript completionHandler` | 同上 + 错误日志 |
| `injected JS dispatchEvent(NativeReply)` | JS 字符串 dispatch CustomEvent |
| `callbackId Map + evaluateJavaScript` | `NSMutableDictionary` pending + evaluateJavaScript |
| `URL scheme callback (app-callback://)` | `loadRequest:` 或 iframe `app-callback://` query |

### 4.3 bridgeEnvelope / bridgeErrorCode / bridgeInjectTiming

与 Swift 规范 §4.4–4.6 同卡面、同字段形状；OC 用 `NSDictionary` / `NSString` 编码。

---

## 5. mediaServe 卡面

| 抽中卡 | OC 实现要点 |
|--------|-------------|
| `loadFileURL bundle resource` | `loadFileURL:allowingReadAccessToURL:` |
| `WKURLSchemeHandler local vault` | `setURLSchemeHandler:forURLScheme:` |
| `custom scheme handler (app-asset://)` | 自定义 scheme + LaneVault |
| `readFile Bridge base64 inline` | Bridge action 读文件 → base64 |
| `NSURL fileURLWithPath vault relative` | Scheme handler 拼 Documents 路径 |

禁止 `file://` 直读沙盒、禁止 base64 大图传图。

---

## 6. 命名约定（深度混淆）

`transform_identifier` 须覆盖 class / method / property / ivar / 局部变量 / `#define` 常量名（非 SDK 协议签名）。

| 示例 | 混淆前 | 混淆后 |
|------|--------|--------|
| 常量 | `static const NSTimeInterval kLoadTimeout = 30;` | `static const NSTimeInterval kSapLoadTimeoutMdm = 28;` |
| 属性 | `@property NWPathMonitor *pathMonitor;` | `@property NWPathMonitor *zsrPathMonitorFzx;` |

每包须重写英文 UI 文案与注释。详见《命名混淆规则.md》§Native shell。

---

## 7. 产包方式

| 模式 | 命令 |
|------|------|
| 模板构建 | `./run.sh build-all` |
| Agent 产包 | `./run.sh --name {App}` |

---

## 相关文档

- [H5-Bridge协议.md](H5-Bridge协议.md)
- [H5壳业务流程文字版.md](H5壳业务流程文字版.md)
- [H5壳Swift实现规范.md](H5壳Swift实现规范.md)（Bridge 卡面细节可对照）
- [data/static/templates/oc_shell/README.md](../data/static/templates/oc_shell/README.md)
