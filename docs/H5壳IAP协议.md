# H5 壳 IAP 协议

**业务在 H5，支付在壳。** 金币商店 UI、商品列表、免费额度、Loading 动效均在 H5；Flutter 仅提供 `purchase` Bridge 对接 StoreKit。

---

## 1. 职责切分

| 层 | 负责 |
|----|------|
| **H5** | 商店页 UI、商品展示、点击购买、全屏 Loading 遮罩、余额展示、免费额度计数（localStorage/IndexedDB） |
| **Flutter Bridge** | `queryProductDetails`、`buyConsumable`、`purchaseStream`、`completePurchase`、幂等去重、加币后回调 H5 |
| **Swift Bridge** | `getProducts`、`purchase`、StoreKit 2 事务监听、幂等去重、回调 H5 |

---

## 2. Bridge：`purchase`

### H5 → 壳（示例）

按本包 `bridgeCallStyle` / `bridgeEnvelope` 实现，语义等价于：

```json
{
  "action": "purchase",
  "payload": { "productId": "Lattice00" }
}
```

### Flutter 执行

1. 用户进入 H5 商店页后，壳侧 **延迟初始化** IAP（不得在 `main()` 启动）。
2. `queryProductDetails` → 回传价格表给 H5（可选 `getProducts` Bridge）。
3. H5 点击购买 → 壳展示 **全屏不可穿透 Loading** → `buyConsumable`。
4. 成功：去重加币 → 回调 H5 `purchaseSuccess` + 新余额。
5. 用户取消：关 Loading，**不弹** Purchase failed。
6. 真失败：关 Loading，英文 Alert + 可重试。

幂等、 `completePurchase` 全分支、交易去重等 — 在 Flutter / Swift Bridge 模块按《H5壳IAP协议.md》本文 + 《H5-Bridge协议.md》`purchase` 实现；H5 不直接碰 StoreKit。

### Swift 执行（StoreKit 2）

1. H5 调用 `getProducts({ productIds })` → Swift `Product.products(for: productIds)` 查询 → 回价格表。
2. H5 点击购买 → 显示全屏不可穿透 Loading → Swift `product.purchase()`。
3. 成功：验证交易状态、本地 `fulfilledTransactions` 去重 → 回调 H5 `purchaseSuccess` + 新余额。
4. 用户取消：关 Loading，**不弹** Purchase failed。
5. 真失败：关 Loading，英文 Alert + 可重试。

> 当前厂包模板均**未做服务端 receipt 验证**，仅本地去重。若业务需要服务端验单，须额外实现。

### 壳 → H5 回调（示例）

```json
{
  "action": "purchaseSuccess",
  "payload": { "productId": "Lattice00", "coinsAdded": 100, "balance": 500 }
}
```

```json
{
  "error": { "code": "USER_CANCELLED" }
}
```

---

## 3. H5 商店 UI 要求

- 商品列表、价格、badge 展示在 H5 完成。
- 商店页打开后再初始化 IAP 监听；离开页面可暂停 UI 层监听（壳侧事务队列仍须 `completePurchase`）。
- Loading 由 H5 触发购买时显示；壳在 StoreKit 回调后通知 H5 关闭。

---

## 4. 免费额度

- 计数存 **H5 本地**（localStorage / IndexedDB）；壳不参与业务额度逻辑。
- 耗尽后 H5 引导至商店；购买走 `purchase` Bridge。

---

## 5. 自检

- [ ] H5 有完整商店 UI，壳无独立 IAP 全屏页（除非 Welcome 合规所需）
- [ ] 取消购买无失败弹窗
- [ ] 同一笔交易不重复加币
- [ ] `completePurchase` 全 `PurchaseStatus` 分支覆盖
