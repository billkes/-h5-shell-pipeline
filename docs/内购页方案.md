# 内购页实现规范（固定规则 + 主题差异化）

全程保留项目原有主题色不变，风格轻调适配欧洲 18–30 岁女性简约精致审美；内购页视觉与布局按本包主题差异化，但商品数据、编码、展示与购买流程强制规则不变。

## 用法注意（执行前必检）

**批量流水线工作区**已自带 `iap-products.json` + `iap-catalog.generated.md`（由 CSV 首个商品Code 生成），此时商品配置与编码以工作区这两份文件为准，无需再传。

**手动维护或单包调试时**：若工作区无上述文件，则须用户提供：
1. **商品配置**（或路径 `iap-products.json`）
2. **首个商品编码**（自增起点，如 `Lattice00` 或 `00Lattice`）

**实现内购页时硬性禁止 App 侧超时检测**（商品查询与真实支付均适用）：不得生成 `Timer`、`Future.timeout()`、Watchdog、`_purchaseTimeout`、`_purchaseTimer`、`_opTimeout` 等任何超时强制结束逻辑。支付 loading 只能等 Store 回调解除；商品查询失败用 `try/catch` + 重试按钮，不用超时。详见下方「禁止写法清单」。

## 商品编码自增规则

- 编码中的 **`00` 为两位自增位**，从 `00` 起连续递增，非促销商品排完后顺延促销商品，两位数连贯不断号
- **后缀式**（数字在末尾）：`Twin00` → `Twin01` → `Twin02` …
- **前缀式**（数字在开头）：`00Twin` → `01Twin` → `02Twin` …
- **优先非促销商品**按顺序自增排序，非促销排完再接续促销商品

## iOS 工程级 IAP 配置（实现与排查必检）

> **原则：先查「这个仓库有什么特殊配置」，再查「Apple 后台有没有配」。** 勿一看到 `Missing SKUs` 就默认 Connect / 商品 ID 未配；若工程绑了本地 StoreKit，真机也会按 `.storekit` 校验，与沙箱无关。用户说包「比较特别」「走 Xcode 不走沙箱」时，**首轮即 grep 工程差异**，少做通用科普。

### 实现内购页时同步检查（改内购页 / 商品 ID / catalog 时必做）

| 步骤 | 检查项 |
|------|--------|
| 1 | `grep -r storekit\|StoreKitConfiguration ios/` — 是否存在 `.storekit`、Scheme 是否引用 |
| 2 | 读代码 / 用户传入 **商品配置** 中的 `productId` |
| 3 | 读 `ios/**/*.storekit` 内各商品的 `productID`（若存在） |
| 4 | 读 `PRODUCT_BUNDLE_IDENTIFIER`（`project.pbxproj` / `Info.plist`） |
| 5 | **三方对齐**：代码 `productId` ↔ `.storekit`（若有）↔ App Store Connect |
| 6 | **向用户确认**当前测试环境：Xcode 本地 StoreKit / 沙箱 / 正式 |

若 `.storekit` 与代码不一致（例如文件里是 `00Slide`、代码是 `311400`），**必须先对齐或解绑 Scheme**，再改 UI；禁止只改 Dart 内购页而忽略工程配置。

### IAP 异常排查固定顺序（`Missing SKUs`、商品拉不到等）

1. `ios/**/*.xcscheme` → `LaunchAction` / `Run` 是否含 `StoreKitConfigurationFileReference`（误绑则走 **Xcode 本地 StoreKit**，非 Apple 沙箱）
2. `ios/**/*.storekit` → 本地 `productID` 是否与代码 / catalog **完全一致**
3. 代码 `productId` ↔ App Store Connect ↔ Bundle ID 是否一致
4. 再排查沙箱账号、网络、删 App 重装、StoreKit 缓存等常规项

**修改 Scheme / `.storekit` / 商品 ID 后**：完整停止运行 → 删 App 重装 → 再测，避免旧配置缓存。

### 易错点：Scheme 误绑本地 StoreKit 导致 `Missing SKUs`（事故复盘）

> **现象**：真机内购报 `Missing SKUs [311400]`（或类似），该包「走 Xcode 不走沙箱」，与同仓库其他包行为不一致。
>
> **根因**：`Runner.xcscheme` 绑定了 `*.storekit`，运行时只认本地配置文件中的商品；`.storekit` 内 ID（如 `00Slide`）与代码请求的 `311400` 不一致 → StoreKit 报 Missing SKUs。**不在** Connect 未配或沙箱账号本身。
>
> **Agent 易犯错误（禁止重复）**：
> - 先入为主把 `Missing SKUs` 归因于 Connect / 沙箱，延迟查 Scheme
> - 仓库已有 `.storekit` 却未与 catalog 交叉比对
> - 只改内购 UI，未同步检查 `.storekit` 与 `productId` 冲突
> - 先前改过商品 ID，后续代码又变回旧 ID，未追问用户「当前测哪套环境」
>
> **落地动作**：
> - 需要沙箱 / 真机连 Apple：在 Scheme 中**移除** `StoreKitConfigurationFileReference`，或把 `.storekit` 内 `productID` 改成与代码一致
> - 需要本地 StoreKit 调试：保留绑定，但**保证** `.storekit` 与代码 / 用户商品配置一致
> - 给出结论前必须说明当前是 **本地 StoreKit** 还是 **沙箱/正式** 两种模式之一，勿混谈

## 强制固定规则（所有方案统一执行）

1. 页面拆分**非促销专区、限时促销专区**两大独立区块，绝不合并同列表，两类专区排版格式完全不同
2. 商品编码起始：由用户传递（如 `Twin00`），**优先非促销商品顺序自增排序**，非促销排完再接续顺延促销商品，两位数尾数/前缀位连贯不断号
3. 非促销商品：仅显示现价，隐藏全部原价，UI 界面全程不展示任何商品 Code
4. 促销商品：清晰展示原价+优惠价，标配促销角标/折扣标签
5. 两个专区禁止全部使用普通竖向单列表布局

## 布局规则（与 `component_kit/patterns/gem_store_layout` 对齐）

> 实现代码规范见 [Flutter UI规范.md](Flutter%20UI规范.md) §8；组件级约束见 [`component_kit/patterns/gem_store_layout.md`](../data/static/component_kit/patterns/gem_store_layout.md)。

1. **必含三区**：balance hero + **Regular 区** + **Promo rail**；禁止纯 `ListTile` / 无结构单列商店。
2. **Regular 区**：默认 2 列网格；`ledger-promo-rail` 变体可用 case-ledger-list 单列台账。
3. **Promo rail**：横向滑动的限时促销 rail，与非促销区视觉区分。
4. **deal badge**：使用 `Stack(clipBehavior: Clip.none)`，允许角标溢出父容器。
5. **purchase overlay**：使用 `ModalBarrier` 覆盖，支付中禁止返回/点击关闭。
6. **H5 tile**：必须加 scroll-aware tap guard，防止滑动浏览误拉起购买。
7. **购买回调**：`refreshView` 仅做局部刷新，**禁止 full dispatch** 导致页面回顶。
8. **落盘约定**：
   - Flutter：`{architectureFolders.views}/shared/{Prefix}StoreLayout.dart`
   - H5：`c-{prefix}-store-*`；tile 用 `bindStoreProductTapGuard`

## Loading 状态与异常路径强制规范（合规与体验底线，所有方案统一执行）

> **总原则**：商品列表加载与真实支付流程采用**不同** loading 策略，禁止混用同一套锁定 / 可取消规则。支付流程遵循 **「支付全链路锁定、仅 Store 终态可解除」** —— 加载态只能由 Store 回调结束，App 侧不得强行打断真实交易。

### ⛔ 禁止写法清单（实现内购页时不得生成以下任何代码）

> **Agent 常见误用**：为满足「loading 不能卡死」而自行添加 `Timer` / `.timeout()`。**本命令明确禁止此做法**—— 内购是真实扣款交易，App 侧超时误判比 loading 卡住危害更大。

**以下写法一律禁止（❌），无论用于商品查询还是支付流程：**

```dart
// ❌ 禁止：常量 + 定时器
static const _opTimeout = Duration(seconds: 15);
static const _purchaseTimeout = Duration(seconds: 30);
Timer? _purchaseTimer;
Timer(_purchaseTimeout, () { ... _endPurchaseFlow(); });

// ❌ 禁止：Future.timeout 包裹 StoreKit 调用
await InAppPurchase.instance.buyConsumable(...).timeout(_purchaseTimeout);
await InAppPurchase.instance.queryProductDetails(...).timeout(_opTimeout);

// ❌ 禁止：Watchdog / 兜底超时函数
void _startPurchaseWaitTimer() { ... }
void _startPurchaseWatchdog() { ... }

// ❌ 禁止：超时后强制结束支付 + 提示
_toast('The purchase took too long. Please try again.');
_toast('Network is slow. ...');
```

**应使用的写法（✅）：**

```dart
// ✅ 商品查询：try/catch/finally + 重试按钮，无 Timer
try {
  setState(() => _querying = true);
  final response = await InAppPurchase.instance.queryProductDetails(ids);
  // ...
} catch (_) {
  // 页面内嵌错误提示 + 「重新加载」按钮
} finally {
  if (mounted) setState(() => _querying = false);
}

// ✅ 支付：只等 purchaseStream 终态，无 .timeout()
await InAppPurchase.instance.buyConsumable(purchaseParam: param, autoConsume: true);
// loading 仅由 purchaseStream → purchased/canceled/error 或 PlatformException 解除
```

**交付前自检（必做）**：在内购页 Dart 文件中搜索以下关键词，**出现即视为违规，必须删除后再交付**：
`Timer(`、`.timeout(`、`Watchdog`、`_purchaseTimeout`、`_purchaseTimer`、`_opTimeout`、`took too long`、`Network is slow`

### 加载状态分层（实现时必须区分）

| 状态 | 作用 | 控制方式 |
|------|------|----------|
| `_querying` | 拉商品列表 | 顶部 `LinearProgressIndicator` 或骨架屏 |
| `_buying` / `_buyingId` | 支付进行中 | 全部商品按钮 disabled，当前项可显示 `…` |
| `_purchaseLoaderShown` | 全屏支付弹窗 | 「Processing purchase…」对话框 |

三者职责分离：`_querying` 只管商品拉取；`_buying` 锁定交互防重复下单；`_purchaseLoaderShown` 仅覆盖支付等待阶段。

### A. 商品列表加载（可重试、异常兜底）

1. **异常兜底（强制）**：商品查询 / `queryProductDetails` 用 `try/catch/finally` 处理，`finally` 必须释放 `_querying`；失败时在页面内嵌友好提示 +「重新加载」按钮，禁止空白页或永久转圈
2. **禁止超时检测（强制）**：不得对商品查询设置 `Timer`、`.timeout()` 或任何 App 侧超时逻辑
3. **可取消 / 可离开（强制）**：商品加载阶段用户可正常关闭内购页、可重试，不受支付锁定约束

### B. 真实支付流程（禁止 App 侧超时检测，仅 Store 终态解除）

#### 核心原则

- **加载态只能由 Store 回调结束**，用户不能在 App 内手动关弹窗、不能离开商店、不能触发其他购买操作
- **禁止 App 侧超时检测**：不得设置 `_purchaseTimeout`、`_purchaseTimer`、`_purchaseWatchdog`，不得对 `buyConsumable` 或 `purchaseStream` 等待加 `.timeout()` / `Timer` —— 一旦误判，会把 Store 里已扣款、正在进行的真实交易当成失败处理
- **只等 Store 给结果**：正常支付几秒内即结束；若 `purchaseStream` 长期无回调，界面保持锁定，**不得** App 侧强制 `_endPurchaseFlow()` 或弹出「 took too long / network slow」类提示

#### 支付弹窗与交互锁定（强制）

| 项目 | 行为 |
|------|------|
| 支付弹窗 | **无 Cancel**、**不可点遮罩关闭**、**不可返回键关闭** |
| 弹窗生命周期 | 从点击购买到 `purchaseStream` 终态（成功 / 失败 / 取消）才关闭 |
| 关闭商店按钮 | 支付中 **disabled** + 拦截系统返回 + toast 提示「Purchase in progress」 |
| 离开确认 | **禁止**提供「仍要离开」—— 不允许人为中断支付流程 |
| 刷新 / 重载 | 支付中 **disabled** |
| 商品按钮 | 支付中 **全部 disabled** |
| `PurchaseStatus.pending` | **保持锁定**（如 Ask to Buy 待家长批准），等 stream 终态再解除 |
| `dispose` | 支付进行中 **不得取消** `purchaseStream` 订阅，避免到账丢失 |

用户**只能**在 Apple 系统支付页自行取消；App 内无法打断已发起的 Store 交易。

#### 唯一解除支付 loading 的路径（强制）

```
purchaseStream → purchased / restored → 发货 → _endPurchaseFlow()
              → canceled            → _endPurchaseFlow()
              → error               → _endPurchaseFlow()
buyConsumable  → PlatformException   → _endPurchaseFlow()（仅发起失败）
```

所有路径必须走**同一终态清理函数**（如 `_endPurchaseFlow()`）：关弹窗 + `_buying = false` + 清除 `_buyingId` / `_busyProductId`。

#### StoreKit 全状态覆盖（强制）

`purchasing / purchased / failed / restored / deferred / cancelled / pending / error` 均须正确处理；必须调用 `completePurchase` / `finishTransaction`，防止残留事务；恢复购买无可恢复项时明确提示，不可静默。

#### 并发与防连点（强制）

同一时间仅允许一笔交易在途；`_buying` / `_busyProductId` 在**任何**购买终态都必须清零，禁止「只 dismiss loader、不清 busy id」。

#### 无障碍与视觉（强制）

支付 HUD 使用项目主题色 + 半透明蒙层（建议 `alpha 0.3~0.5`）；VoiceOver 朗读「正在处理购买」及结果。

### 易错点：误用 App 侧超时导致支付成功仍报失败（事故复盘，禁止复现）

> **现象**：用户在系统支付页输入密码较久，App 弹出 “The purchase took too long. Please try again.”，但支付实际成功，token 仍通过 `purchaseStream` 到账。
>
> **根因（历史反例，禁止写回代码）**：曾用 App 侧计时器从点击购买开始覆盖整个 `_buying` 周期，与 Store 异步回调不同步。
>
> **禁止采用的任何超时方案（全部 ❌）**：
> - 从点击购买开始计时
> - `buyConsumable(...).timeout(...)`
> - `Timer` / Watchdog 覆盖支付等待
> - 在 `buyConsumable` 返回后再启动计时
> - 任意秒数的兜底超时（含 30s / 90s）
>
> **唯一正确做法（强制）**：
> 1. 购买流程**零** App 侧超时检测 — 不写 `Timer`、不写 `.timeout()`、不写 Watchdog
> 2. 支付 loading **仅**由 Store 终态回调（或 `buyConsumable` 发起失败）解除
> 3. 自测：在系统支付页故意多停留 → 确认**不会**出现 took too long / network slow 类提示，成功后仅显示 token 到账

### 易错点：支付弹窗 Cancel 导致状态与真实交易不一致（事故复盘）

> **现象**：用户点 App 内 Cancel / 点遮罩关闭 “Processing purchase…” 弹窗后，`_buying` 被清零、按钮恢复可点，但 Store 交易仍在进行 → 可能重复下单；或 stream 稍后到账时 UI 状态已乱。
>
> **根因**：关弹窗 ≠ 取消 Apple 支付；弹窗与 `_buying` 生命周期错误绑定，允许 App 侧手动 `_endPurchaseFlow()`。
>
> **落地检查（实现内购页时必做）**：
> 1. 支付弹窗**无 Cancel**、**不可 dismiss**、**不可返回键关闭**
> 2. 禁止「关弹窗即 `_endPurchaseFlow()`」—— 只有 Store 终态或 `buyConsumable` 发起失败才可结束
> 3. 支付中关闭商店按钮 disabled，不提供「仍要离开」
> 4. `buyConsumable` 返回后**不要**提前关弹窗并重置 `_buying`（旧错误改法）；弹窗应持续到 stream 终态

### 易错点：取消支付后购买按钮永久变灰（事故复盘）

> **现象**：用户在 App Store 支付弹窗点「取消」后，内购页所有商品购买按钮变灰且无法再次点击；部分机型/系统版本可复现、部分不能（iOS 取消回调路径不固定）。
>
> **根因**：点击购买时设置了 `_busyProductId`（或等价字段）用于防连点/禁用按钮，但**部分取消回调**（如 `purchase.error` 含 `cancelled` / `userCancelled` 等）只调用了关闭 loading 的逻辑，**未清除** `_busyProductId`，按钮 `disabled` 条件一直为真。
>
> **落地检查（实现内购页时必做）**：
> 1. 梳理所有会结束购买的出口：`purchased`、`failed`、`restored`、`deferred`、`cancelled`、`purchaseStream` 的 error、`PlatformException`（发起失败）、`dispose`（非支付中）
> 2. 每个出口都必须经过**同一终态清理函数**（`_endPurchaseFlow()`），在其中**无条件**清除 `_buying` / `_buyingId` / `_busyProductId`
> 3. 禁止在多个分支里各自只关 loader 且遗漏 busy id
> 4. 自测：发起购买 → App Store 弹窗取消 → 确认所有商品按钮恢复可点；再测网络错误、重复点击、恢复购买结束后的按钮状态

> **进阶说明**：若用户强行杀 App 或支付中离开页面，`purchaseStream` 订阅在 `dispose` 被取消可能导致 token 延迟到下次进商店才补发。彻底避免需将 stream 监听提升到 App 级；当前流水线默认页面级实现，但 **支付进行中不得 cancel 订阅**。

## 通用差异化自由设定

可随应用主题搭配不同页面质感、按钮弧度、选中动效、价格字体样式、板块分割线样式、进入页面过渡动画，整体温柔高级简约耐看，贴合海外女性用户审美，功能逻辑、商品排序、价格展示规则完全不变，仅视觉版式与交互形态按主题差异化。

