# H5 字体图标 Kit（仅限 h5_shell）

> 从 Mockoo 参考项目提取的 FontAwesome 字体图标方案，**仅**供 h5_shell 产包直接复用。
>
> 因 H5 没有差异化限制，字体图标 kit 可直接作为公共资产下发；Flutter 壳侧仍按原规则使用 `Icon(IconData)` 或 Flutter 生态 FontAwesome package，**不**复用本 kit。

## 来源

- 参考项目：`Mockoo-Swift/Mockoo/h5/src/assets/fontawesome`
- 字体库：Font Awesome Free 7.1.0
- 许可证：Icons CC BY 4.0 / Fonts SIL OFL 1.1 / Code MIT

## 包内容

```
h5_icon_font_kit/
├── css/
│   ├── fontawesome.min.css   # 核心样式 + 全部 solid 图标 class
│   └── solid.min.css         # solid 字体 face 声明
└── webfonts/
    └── fa-solid-900.woff2    # solid 字重字体文件
```

## 使用方式

### 1. 拷贝到 H5 项目

产包脚本将本 kit 复制到目标 H5 项目的 `src/assets/fontawesome/`：

```
src/assets/fontawesome/css/*      <- kit/css/*
src/assets/fontawesome/webfonts/* <- kit/webfonts/*
```

### 2. 入口引入

在 `src/main.ts` 顶部引入：

```ts
import '@/assets/fontawesome/css/fontawesome.min.css'
import '@/assets/fontawesome/css/solid.min.css'
```

### 3. 组件中使用

```vue
<template>
  <i class="fa-solid fa-book-open" aria-hidden="true"></i>
  <i :class="['fa-solid', iconClass, 'c-{prefix}-icon']" aria-hidden="true"></i>
</template>
```

尺寸、颜色必须引用本包 token，禁止硬编码：

```css
.c-{prefix}-icon {
  font-size: var(--{prefix}-icon-md);
  color: var(--{prefix}-on-surface);
}
```

## 与 Vite 单文件产物的兼容性

本 kit 配合 `vite-plugin-singlefile` 使用时，字体文件会作为 base64 inline asset 内联到 HTML；若产包体积敏感，可在 `vite.config.ts` 中调大 `assetsInlineLimit` 或单独保留 `webfonts/` 目录由壳通过 `loadFileURL` 加载。

## 与组件规范的关系

- 默认规范仍优先使用 `component_kit/primitives/icon.md` 的 SVG sprite 方案。
- 当本包视觉锁 `iconography.package = "font-awesome"` 时，方可启用本 kit。
- 禁止裸 PNG 图标；禁止将 icon-class 作为独立图片资源（assetBrief 规则不变）。
