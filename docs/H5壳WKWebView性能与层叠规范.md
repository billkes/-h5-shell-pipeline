# H5 壳 · WKWebView 性能与层叠规范

> 跨包通用 · 20260714  

> 产包 Agent：**只读本文件与封闭语料内关联文档**；加工侧 pitfalls 笔记不在产包工作区。

真机 WKWebView 与桌面模拟器体感差异大：**发热、Tab 点不动、子页返回卡死、弹层挡点击、系统音频控件露馅** 均须在本规范覆盖。

---

## 1. 常驻 ambient 与 GPU

| 现象 | 根因 |
|------|------|
| 不操作也发热 | 全局 `ambient` 多层 `filter:blur` + 无限 `animation` + `will-change` |
| 切 Tab 更卡 | 动画与 Tab 切换 DOM 尖峰叠加 |

**要求（功能页）**：

- Splash / Welcome 可保留动效；**其余 `data-dnmrl-scene` 停掉** aurora/mesh/orb/spark 无限动画（静态渐变即可）。
- 禁止功能页常驻 `dice-float` 等装饰 infinite（Hub/Compare 等）。

```css
/* 示例：除 splash/welcome 外静态 ambient */
html:not([data-dnmrl-scene='splash']):not([data-dnmrl-scene='welcome']) .u-*-ambient__aurora,
/* … mesh / orb / spark … */ { animation: none !important; }
```

---

## 2. `backdrop-filter` 毛玻璃

| 位置 | 风险 |
|------|------|
| Dock / TabBar | 固定层每帧重采样 |
| Subpage TopBar | 滚动掉帧 |
| Modal 遮罩 + `blur(4px)` | 真机合成贵 |

**要求**：改为**不透明渐变 / 略加深 `rgba` 遮罩**，肉眼无差别：

- Dock：`--pill-bg` 实色 + `game-pop` 阴影，**禁** `backdrop-filter`
- TopBar：97% 实色渐变顶栏
- Media / picker 遮罩：`rgba` 0.52（暗色 0.58）替代 blur

---

## 3. Tab 与子页路由（点不动高发区）

### 3.1 Tab 互切

| 反模式 | 修复 |
|--------|------|
| `transition mode="out-in"` + 大 DOM（40 格棋盘） | 去掉 `out-in`；`keep-alive :max="3"` 缓存三 Tab |
| 每次切 Tab 全量 mount Hub | 同上 |

### 3.2 子页（`/board/setup` 等）离开 TabLayout

| 反模式 | 修复 |
|--------|------|
| 子页路由与 TabLayout 平级 → 进子页 **卸载** 整个 TabLayout | **`App.vue` 根 `keep-alive :include="['TabLayout']"`** + `defineOptions({ name: 'TabLayout' })` |
| 返回 Hub 重挂 40 格 → 主线程数秒无响应 | 同上；`HubView.onActivated` → `refresh()` |

### 3.3 首屏重页

- `BoardLiveView`：`hydrate()` 延后 `nextTick` + `requestAnimationFrame`，避免与首帧绘制抢主线程。

---

## 4. Teleport 弹层残留

| 场景 | 修复 |
|------|------|
| Compare `picker-sheet` 打开后切 Tab/子页 | `ListView.onDeactivated` → `pickerOpen = false` |
| 挑战内 `MediaSourceSheet` / 录音 | `ChallengeMomentCapture.onDeactivated` 关 sheet、停录音 |
| Live 挑战/商店/骰子 overlay | `BoardLiveView.dismissLiveOverlays()` on `onBeforeUnmount` / `onDeactivated` |

---

## 5. Overlay z-index 阶梯（强制）

**子组件 Teleport 到 `body` 时，必须高于父级 `event-veil`。**

在 `global.css` `:root` 定义并全站引用：

| Token | 值 | 用途 |
|-------|-----|------|
| `--dnmrl-z-dock` | 100 | 底部 Tab |
| `--dnmrl-z-sheet` | 130 | picker、confirm、legal、dice-overlay |
| `--dnmrl-z-event` | 140 | 挑战 / 商店 / 结算 / 离开确认 |
| `--dnmrl-z-snack` | 150 | Toast（高于 event，便于报错可见） |
| `--dnmrl-z-media` | 200 | **拍照/选图 MediaSourceSheet（最高交互层）** |

**典型 bug**：`media-sheet: 130` < `event-veil: 140` → 挑战里点 Snap photo，Take Photo 菜单被挡。

---

## 6. 音频控件去风味

| 反模式 | 修复 |
|--------|------|
| `<audio controls>` | **禁**；用自定义 `AudioPlayer.vue`（隐藏原生 `<audio>` + 品牌播放条） |
| 列表多段同时播 | `audioPlayerSession` 单例互斥暂停 |

组件要求：播放/暂停、进度条（click + touch）、`mm:ss`、与 `moment-btn` / `game-pop` 同系视觉。

---

## 7. `router.afterEach` scene

统一映射，避免 `board/live` 等碎 scene 导致 ambient 规则漏网：

```ts
if (raw === 'list') scene = 'compare';
else if (raw.startsWith('board/')) scene = 'board';
```

子页 `onBeforeUnmount` **勿**再手写 `data-dnmrl-scene='hub'`（与 router 竞态）。

---

## 8. 加工自检（真机 · 模拟器）

| # | 路径 | 预期 |
|---|------|------|
| 1 | Home ↔ Compare ↔ More | 第二次起近即时；Compare 首进可接受 |
| 2 | Home → Board setup → 返回 | 按钮可点，无 2s+ 冻结 |
| 3 | 挑战 → Snap photo | Take Photo / Library **在** challenge 卡片之上 |
| 4 | 录完音播放 | 自定义播放条，**非** iOS 系统 audio UI |
| 5 | 连续玩 3 局 | 无明显发热加剧（ambient 已静化） |

---

## 9. 流水线检测

```bash
cd h5-shell-pipeline
# 去风味 + 音频（硬）
PYTHONPATH=scripts python3 -c "
from pathlib import Path
from batch.h5_deflavor_audit import collect_h5_deflavor_violations
for i in collect_h5_deflavor_violations(Path('output/{AppName}-Swift/{AppName}')):
    print(i)
"

# 性能/层叠（软警告，加工阶段人工处理）
PYTHONPATH=scripts python3 -c "
from pathlib import Path
from batch.h5_perf_audit import collect_h5_perf_warnings
for w in collect_h5_perf_warnings(Path('output/{AppName}-Swift/{AppName}')):
    print(w)
"
```

---

## 10. 关联文档

| 文档 | 关系 |
|------|------|
| 《H5去风味规范.md》 | §6 组件禁原生样式 · 音频扩展 |
| 《H5壳Swift实现规范.md》 | CDN 加载 / shellReady |
| 《H5壳H5实现检查清单.md》 | Implementer 勾选 |
