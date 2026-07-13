#import "{{PREFIX_CAP}}PulseCredit.h"

@interface {{PREFIX_CAP}}PulseCredit ()
@property (nonatomic, copy) {{PREFIX_CAP}}PulseCreditHandler pending;
@property (nonatomic, copy) NSString *pendingProductId;
@end

@implementation {{PREFIX_CAP}}PulseCredit

- (instancetype)init {
    self = [super init];
    if (self) {
        [[SKPaymentQueue defaultQueue] addTransactionObserver:self];
    }
    return self;
}

- (void)dealloc {
    [[SKPaymentQueue defaultQueue] removeTransactionObserver:self];
}

- (void){{PREFIX}}BuyProduct:(NSString *)productId callback:({{PREFIX_CAP}}PulseCreditHandler)handler {
    NSString *raw = productId.length ? productId : @"";
    NSString *pid = [raw stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
    if (!pid.length) {
        if (handler) handler(-1, @{@"message": @"productId is required"});
        return;
    }
    self.pending = handler;
    self.pendingProductId = pid;
    if (![SKPaymentQueue canMakePayments]) {
        if (handler) handler(-1, @{@"message": @"IAP unavailable"});
        self.pending = nil;
        self.pendingProductId = nil;
        return;
    }
    NSSet *ids = [NSSet setWithObject:pid];
    SKProductsRequest *req = [[SKProductsRequest alloc] initWithProductIdentifiers:ids];
    req.delegate = self;
    [req start];
}

- (void){{PREFIX}}Restore:({{PREFIX_CAP}}PulseCreditHandler)handler {
    self.pending = handler;
    self.pendingProductId = nil;
    [[SKPaymentQueue defaultQueue] restoreCompletedTransactions];
}

- (SKProduct *){{PREFIX}}ProductMatchingId:(NSString *)productId inResponse:(SKProductsResponse *)response {
    for (SKProduct *product in response.products) {
        if ([product.productIdentifier isEqualToString:productId]) {
            return product;
        }
    }
    return nil;
}

- (void)productsRequest:(SKProductsRequest *)request didReceiveResponse:(SKProductsResponse *)response {
    NSString *pid = self.pendingProductId ?: @"";
    SKProduct *product = [self {{PREFIX}}ProductMatchingId:pid inResponse:response];
    if (!product) {
        NSArray *invalid = response.invalidProductIdentifiers ?: @[];
        NSString *invalidText = invalid.count ? [invalid componentsJoinedByString:@","] : @"none";
        NSString *msg = [NSString stringWithFormat:@"Product not found: %@ (invalid: %@). Check Scheme StoreKit config or ASC sandbox SKU.",
                         pid, invalidText];
        if (self.pending) self.pending(-1, @{@"message": msg, @"productId": pid, @"invalidProductIds": invalidText});
        self.pending = nil;
        self.pendingProductId = nil;
        return;
    }
    SKPayment *pay = [SKPayment paymentWithProduct:product];
    [[SKPaymentQueue defaultQueue] addPayment:pay];
}

- (void)request:(SKRequest *)request didFailWithError:(NSError *)error {
    if (self.pending) {
        self.pending(-1, @{
            @"message": error.localizedDescription ?: @"Product request failed",
            @"productId": self.pendingProductId ?: @""
        });
    }
    self.pending = nil;
    self.pendingProductId = nil;
}

- (void)paymentQueue:(SKPaymentQueue *)queue updatedTransactions:(NSArray<SKPaymentTransaction *> *)transactions {
    for (SKPaymentTransaction *tx in transactions) {
        switch (tx.transactionState) {
            case SKPaymentTransactionStatePurchased:
            case SKPaymentTransactionStateRestored: {
                [[SKPaymentQueue defaultQueue] finishTransaction:tx];
                if (self.pending) {
                    self.pending(0, @{
                        @"productId": tx.payment.productIdentifier ?: @"",
                        @"transactionId": tx.transactionIdentifier ?: @""
                    });
                }
                self.pending = nil;
                self.pendingProductId = nil;
                break;
            }
            case SKPaymentTransactionStateFailed: {
                [[SKPaymentQueue defaultQueue] finishTransaction:tx];
                NSInteger code = (tx.error.code == SKErrorPaymentCancelled) ? -2 : -1;
                if (self.pending) {
                    self.pending(code, @{@"message": tx.error.localizedDescription ?: @"failed"});
                }
                self.pending = nil;
                self.pendingProductId = nil;
                break;
            }
            default:
                break;
        }
    }
}

- (void)paymentQueueRestoreCompletedTransactionsFinished:(SKPaymentQueue *)queue {
    if (self.pending) self.pending(0, @{@"restored": @YES});
    self.pending = nil;
    self.pendingProductId = nil;
}

- (void)paymentQueue:(SKPaymentQueue *)queue restoreCompletedTransactionsFailedWithError:(NSError *)error {
    if (self.pending) self.pending(-1, @{@"message": error.localizedDescription ?: @"restore failed"});
    self.pending = nil;
    self.pendingProductId = nil;
}

@end
