#import <Foundation/Foundation.h>
#import <StoreKit/StoreKit.h>

typedef void (^{{PREFIX_CAP}}PulseCreditHandler)(NSInteger code, NSDictionary *payload);

@interface {{PREFIX_CAP}}PulseCredit : NSObject <SKProductsRequestDelegate, SKPaymentTransactionObserver>
- (void){{PREFIX}}BuyProduct:(NSString *)productId callback:({{PREFIX_CAP}}PulseCreditHandler)handler;
- (void){{PREFIX}}Restore:({{PREFIX_CAP}}PulseCreditHandler)handler;
@end
