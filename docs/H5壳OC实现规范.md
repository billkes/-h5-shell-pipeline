# H5 壳 Objective-C 实现规范

> 面向 `h5_oc_shell` 的 OC Programmer。参考实现：**Hathoo-OC**（已抽取为 `data/static/templates/oc_shell/`）。

---

## 1. 技术站锁定

`pack_type == h5_oc_shell` 时 Bridge 七维锁定（不随 deck 抽卡变化）：

| 维度 | 锁定值 |
|------|--------|
| webviewEngine | `wkwebview_oc` |
| bridgeCallStyle | `window.webkit.messageHandlers.{prefix}.postMessage(JSON)` |
| bridgeCallbackStyle | `URL scheme callback (app-callback://)` |
| bridgeEnvelope | `URL query flattened` |
| mediaServe | `WKURLSchemeHandler local vault` |
| bridgeErrorCode | `numeric codes (0/-1/-2)` |
| bridgeInjectTiming | `WKUserScript atDocumentStart` |

---

## 2. 项目骨架（v1 扁平 6 类）

| 类 | 职责 |
|----|------|
| `{{PREFIX_CAP}}AppDelegate` | 启动、安装 Deflavor、挂载 HostController |
| `{{PREFIX_CAP}}HostController` | WKWebView 宿主、Bridge 分发、Launch Veil、权限/IAP 调度 |
| `{{PREFIX_CAP}}LaneVault` | `WKURLSchemeHandler`（`{{PREFIX}}asset://`） |
| `{{PREFIX_CAP}}PulseCredit` | StoreKit IAP |
| `{{PREFIX_CAP}}WebViewDeflavor` | 去键盘辅助栏、禁双击缩放 |

H5 业务在 `h5_site/{{PREFIX}}_entry.htm`（或远程 `h5EntryUrl`），**禁止** Native 业务 UI。

---

## 3. 冷启动

1. 读 `register.json` / `本包登记信息.json` 的 `h5EntryUrl`
2. `WKWebView` `loadRequest` 该 URL
3. H5 首帧后调 `shellReady` → Native 撤 Launch Veil

---

## 4. Native→H5 回调

使用 **URL scheme** `app-callback://`（非 `evaluateJavaScript`）：

```objc
// 示例：HostController 内构造 app-callback://{prefix}?code=0&action=...
```

H5 侧监听 `hahv-callback` CustomEvent 或 `onCallback`。

---

## 5. 本地资源

- 自定义 scheme：`{{PREFIX}}asset`（如 `hahvasset://`）
- 禁止 `file://`、禁止 base64 大图传图

---

## 6. 产包方式

| 模式 | 命令 |
|------|------|
| 模板构建 | `./run.sh build-all` |
| Agent 产包 | `./run.sh --name {App}` |

---

## 相关文档

- [H5-Bridge协议.md](H5-Bridge协议.md)
- [H5壳业务流程文字版.md](H5壳业务流程文字版.md)
- [data/static/templates/oc_shell/README.md](../data/static/templates/oc_shell/README.md)
