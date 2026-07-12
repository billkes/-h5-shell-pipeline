# {{APP_NAME}} H5 业务包

> 场包时，用业务包构建产物覆盖本目录。

## 期望产物

```
h5/
├── {{APP_NAME_LOWER}}_entry.htm   # monolith 入口（必须）
└── assets/                        # 静态资源
```

## 接入要求

1. 入口文件名须与 `本包登记信息.json` 中的 `h5EntryUrl` 保持一致。
2. H5 首帧绘制完成后须调用：
   ```js
   window.webkit.messageHandlers.{{APP_NAME_LOWER}}Bridge.postMessage({
     action: 'shellReady',
     data: {}
   });
   ```
3. Bridge 调用统一使用：
   ```js
   window.webkit.messageHandlers.{{APP_NAME_LOWER}}Bridge.postMessage({
     action: 'pickImage',
     data: { fromCamera: false }
   });
   ```
4. 回调通过全局函数接收（由壳注入）：
   ```js
   window.{{APP_NAME_LOWER}}BridgeCallback(id, envelope);
   ```
5. 本地媒体 URL 使用自定义 Scheme：
   ```
   {{ASSET_SCHEME}}://local/photos/seed/example.jpg
   ```

## 禁止项

- 禁止在入口或资源路径中使用 `h5`、`web`、`bridge`、`webview` 等公共符号。
- 禁止将业务源码、私密配置提交到流水线模板仓库。
