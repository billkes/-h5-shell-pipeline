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

@MainActor
final class IAPManager {
    static let shared = IAPManager()

    static let productIds: Set<String> = []

    private let fulfilledKey = "{{APP_NAME_LOWER}}_iap_fulfilled_tx_v1"
    private var fulfilledTransactions = Set<String>()
    private var listenerTask: Task<Void, Never>?
    private var isInitialized = false

    private init() {}

    func initializeIfNeeded() {
        guard !isInitialized else { return }
        isInitialized = true
        loadFulfilledTransactions()
        listenerTask = Task { await listenForTransactions() }
    }

    func fetchProducts() async throws -> [[String: Any]] {
        initializeIfNeeded()
        let products = try await Product.products(for: Array(Self.productIds))
        return products.map { product in
            [
                "productId": product.id,
                "price": product.displayPrice,
                "title": product.displayName,
            ]
        }
    }

    func purchase(productId: String) async throws -> IAPPurchaseResult {
        initializeIfNeeded()
        guard AppStore.canMakePayments else {
            throw IAPError.unavailable
        }
        let products = try await Product.products(for: [productId])
        guard let product = products.first else {
            throw IAPError.productNotFound
        }

        let result = try await product.purchase()
        switch result {
        case .success(let verification):
            let transaction = try checkVerified(verification)
            let txId = String(transaction.id)
            await transaction.finish()
            return IAPPurchaseResult(productId: product.id, transactionId: txId)
        case .userCancelled:
            throw IAPError.userCancelled
        case .pending:
            throw IAPError.pending
        @unknown default:
            throw IAPError.unknown("Unknown purchase result")
        }
    }

    private func listenForTransactions() async {
        for await result in Transaction.updates {
            do {
                let transaction = try checkVerified(result)
                let txId = String(transaction.id)
                _ = markFulfilled(txId)
                await transaction.finish()
            } catch {
                continue
            }
        }
    }

    private func checkVerified<T>(_ result: VerificationResult<T>) throws -> T {
        switch result {
        case .unverified:
            throw IAPError.unknown("Transaction verification failed")
        case .verified(let safe):
            return safe
        }
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
