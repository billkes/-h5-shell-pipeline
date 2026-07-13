# OC H5 Shell 厂包夹板（v1）

基于 **Hathoo-OC** 参考实现抽取，扁平 6 类结构（非模块化 Bridge/ 子目录）。

## 适用

- `task.csv` **pack_type** = `h5_oc_shell`
- **webviewEngine** = `wkwebview_oc`（锁定）

## 目录结构

```
{{APP_NAME}}/
├── {{APP_NAME}}/                    # OC 源码（6 类 + main.m）
│   ├── {{PREFIX_CAP}}AppDelegate.h/m
│   ├── {{PREFIX_CAP}}HostController.h/m   # WebView + Bridge + Veil
│   ├── {{PREFIX_CAP}}LaneVault.h/m        # WKURLSchemeHandler
│   ├── {{PREFIX_CAP}}PulseCredit.h/m      # StoreKit IAP
│   ├── {{PREFIX_CAP}}WebViewDeflavor.h/m
│   ├── main.m
│   ├── Info.plist
│   ├── Base.lproj/LaunchScreen.storyboard
│   ├── Assets.xcassets/          # AppIcon + launch_placeholder（apply 时生成水印占位，非厂包真图）
│   └── register.json
├── {{APP_NAME}}.xcodeproj/
├── h5/                              # H5 源码（Vite；dev.h5.build 产出 h5_site/，不提交）
└── 本包登记信息.json
```

## Bridge 七维（锁定）

| 维度 | 值 |
|------|-----|
| webviewEngine | `wkwebview_oc` |
| bridgeCallStyle | `window.webkit.messageHandlers.{prefix}.postMessage(JSON)` |
| bridgeCallbackStyle | `URL scheme callback (app-callback://)` |
| bridgeEnvelope | `URL query flattened` |
| mediaServe | `WKURLSchemeHandler local vault` |
| bridgeErrorCode | `numeric codes (0/-1/-2)` |
| bridgeInjectTiming | `WKUserScript atDocumentStart` |

## 应用模板

```bash
python data/static/templates/oc_shell/apply.py \
  --src data/static/templates/oc_shell/{{APP_NAME}} \
  --dst output/MyApp \
  --app-name MyApp \
  --prefix myprx \
  --app-slug myapp \
  --h5-host test.darin.beauty \
  --bundle-id test.duckegg.ios \
  --team-id XXXXX \
  --asset-scheme myprxasset
```

或通过流水线：

```bash
./run.sh build-all   # task.csv pack_type=h5_oc_shell
```

## macOS 编译

```bash
cd output/{AppName}
xcodebuild -project {AppName}.xcodeproj -scheme {AppName} \
  -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' build
```
