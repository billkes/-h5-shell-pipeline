import Foundation
import StoreKit

enum IAPError: LocalizedError {
    case unavailable
    case productNotFound
    case userCancelled
    case pending
    case unknown(String)

    var errorCode: String {
        switch self {
        case .unavailable: return "IAP_UNAVAILABLE"
        case .productNotFound: return "PRODUCT_NOT_FOUND"
        case .userCancelled: return "USER_CANCELLED"
        case .pending: return "PENDING"
        case .unknown: return "UNKNOWN"
        }
    }

    var errorDescription: String? {
        switch self {
        case .unavailable: return "In-app purchases are not available"
        case .productNotFound: return "Product not found"
        case .userCancelled: return "Purchase cancelled"
        case .pending: return "Purchase pending approval"
        case .unknown(let message): return message
        }
    }
}

struct IAPPurchaseResult {
    let productId: String
    let transactionId: String
}

/// StoreKit 1 implementation — compatible with iOS 13+.
final class IAPManager: NSObject, SKProductsRequestDelegate, SKPaymentTransactionObserver {
    static let shared = IAPManager()

    static let productIds: Set<String> = []

    private let fulfilledKey = "{{APP_NAME_LOWER}}_iap_fulfilled_tx_v1"
    private var fulfilledTransactions = Set<String>()
    private var isInitialized = false

    private var productsRequest: SKProductsRequest?
    private var productsContinuation: CheckedContinuation<[SKProduct], Error>?
    private var purchaseContinuation: CheckedContinuation<IAPPurchaseResult, Error>?
    private var pendingProductId: String?

    private override init() {
        super.init()
    }

    func initializeIfNeeded() {
        guard !isInitialized else { return }
        isInitialized = true
        loadFulfilledTransactions()
        SKPaymentQueue.default().add(self)
    }

    func fetchProducts() async throws -> [[String: Any]] {
        initializeIfNeeded()
        let ids = Self.productIds
        guard !ids.isEmpty else { return [] }
        let products = try await requestProducts(identifiers: ids)
        return products.map { product in
            [
                "productId": product.productIdentifier,
                "price": product.localizedPriceString,
                "title": product.localizedTitle,
            ]
        }
    }

    func purchase(productId: String) async throws -> IAPPurchaseResult {
        initializeIfNeeded()
        guard SKPaymentQueue.canMakePayments() else {
            throw IAPError.unavailable
        }
        let products = try await requestProducts(identifiers: Set([productId]))
        guard let product = products.first(where: { $0.productIdentifier == productId }) else {
            throw IAPError.productNotFound
        }
        return try await enqueuePurchase(product: product)
    }

    private func requestProducts(identifiers: Set<String>) async throws -> [SKProduct] {
        try await withCheckedThrowingContinuation { continuation in
            DispatchQueue.main.async {
                if self.productsContinuation != nil {
                    continuation.resume(throwing: IAPError.unknown("Products request already in progress"))
                    return
                }
                self.productsContinuation = continuation
                let request = SKProductsRequest(productIdentifiers: identifiers)
                self.productsRequest = request
                request.delegate = self
                request.start()
            }
        }
    }

    private func enqueuePurchase(product: SKProduct) async throws -> IAPPurchaseResult {
        try await withCheckedThrowingContinuation { continuation in
            DispatchQueue.main.async {
                if self.purchaseContinuation != nil {
                    continuation.resume(throwing: IAPError.unknown("Purchase already in progress"))
                    return
                }
                self.purchaseContinuation = continuation
                self.pendingProductId = product.productIdentifier
                SKPaymentQueue.default().add(SKPayment(product: product))
            }
        }
    }

    // MARK: - SKProductsRequestDelegate

    func productsRequest(_ request: SKProductsRequest, didReceive response: SKProductsResponse) {
        let products = response.products
        let cont = productsContinuation
        productsContinuation = nil
        productsRequest = nil
        cont?.resume(returning: products)
    }

    func request(_ request: SKRequest, didFailWithError error: Error) {
        if request === productsRequest {
            let cont = productsContinuation
            productsContinuation = nil
            productsRequest = nil
            cont?.resume(throwing: error)
        }
    }

    // MARK: - SKPaymentTransactionObserver

    func paymentQueue(_ queue: SKPaymentQueue, updatedTransactions transactions: [SKPaymentTransaction]) {
        for tx in transactions {
            switch tx.transactionState {
            case .purchased, .restored:
                let productId = tx.payment.productIdentifier
                let txId = tx.transactionIdentifier ?? "\(productId)-\(Date().timeIntervalSince1970)"
                _ = markFulfilled(txId)
                queue.finishTransaction(tx)
                if let cont = purchaseContinuation, pendingProductId == productId || pendingProductId == nil {
                    purchaseContinuation = nil
                    pendingProductId = nil
                    cont.resume(returning: IAPPurchaseResult(productId: productId, transactionId: txId))
                }
            case .failed:
                queue.finishTransaction(tx)
                let cancelled = (tx.error as? SKError)?.code == .paymentCancelled
                let cont = purchaseContinuation
                purchaseContinuation = nil
                pendingProductId = nil
                cont?.resume(throwing: cancelled ? IAPError.userCancelled : IAPError.unknown(tx.error?.localizedDescription ?? "Purchase failed"))
            case .deferred:
                let cont = purchaseContinuation
                purchaseContinuation = nil
                pendingProductId = nil
                cont?.resume(throwing: IAPError.pending)
            case .purchasing:
                break
            @unknown default:
                break
            }
        }
    }

    func paymentQueue(_ queue: SKPaymentQueue, shouldAddStorePayment payment: SKPayment, for product: SKProduct) -> Bool {
        false
    }

    private func loadFulfilledTransactions() {
        if let saved = UserDefaults.standard.array(forKey: fulfilledKey) as? [String] {
            fulfilledTransactions = Set(saved)
        }
    }

    @discardableResult
    private func markFulfilled(_ key: String) -> Bool {
        guard !fulfilledTransactions.contains(key) else { return false }
        fulfilledTransactions.insert(key)
        UserDefaults.standard.set(Array(fulfilledTransactions), forKey: fulfilledKey)
        return true
    }
}

private extension SKProduct {
    var localizedPriceString: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.locale = priceLocale
        return formatter.string(from: price) ?? "\(price)"
    }
}
