#import <Foundation/Foundation.h>

@class WKWebView;

@interface {{PREFIX_CAP}}WebViewDeflavor : NSObject

+ (void)install;
+ (void)patchWebView:(WKWebView *)webView;

@end
