#import "{{PREFIX_CAP}}LaneVault.h"

@implementation {{PREFIX_CAP}}LaneVault

- (void)webView:(WKWebView *)webView startURLSchemeTask:(id<WKURLSchemeTask>)urlSchemeTask {
    NSURL *url = urlSchemeTask.request.URL;
    NSString *path = url.path ?: @"";
    if ([path hasPrefix:@"/"]) {
        path = [path substringFromIndex:1];
    }
    NSString *docs = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).firstObject;
    NSString *filePath = [docs stringByAppendingPathComponent:path];
    NSData *data = [NSData dataWithContentsOfFile:filePath];
    if (!data) {
        NSString *bundlePath = [[NSBundle mainBundle] pathForResource:[path lastPathComponent].stringByDeletingPathExtension
                                                               ofType:path.pathExtension
                                                          inDirectory:[path stringByDeletingLastPathComponent]];
        if (!bundlePath) {
            bundlePath = [[NSBundle mainBundle] pathForResource:path.lastPathComponent.stringByDeletingPathExtension
                                                         ofType:path.pathExtension];
        }
        if (bundlePath) {
            data = [NSData dataWithContentsOfFile:bundlePath];
        }
    }
    if (!data) {
        NSError *err = [NSError errorWithDomain:@"{{PREFIX}}.media" code:-1 userInfo:nil];
        [urlSchemeTask didFailWithError:err];
        return;
    }
    NSString *mime = @"application/octet-stream";
    if ([path.pathExtension.lowercaseString isEqualToString:@"png"]) mime = @"image/png";
    if ([path.pathExtension.lowercaseString isEqualToString:@"jpg"] ||
        [path.pathExtension.lowercaseString isEqualToString:@"jpeg"]) mime = @"image/jpeg";
    NSDictionary *headers = @{
        @"Content-Type": mime,
        @"Access-Control-Allow-Origin": @"*",
        @"Access-Control-Allow-Methods": @"GET, OPTIONS",
        @"Cache-Control": @"no-store"
    };
    NSHTTPURLResponse *resp = [[NSHTTPURLResponse alloc] initWithURL:url
                                                          statusCode:200
                                                         HTTPVersion:@"HTTP/1.1"
                                                        headerFields:headers];
    [urlSchemeTask didReceiveResponse:resp];
    [urlSchemeTask didReceiveData:data];
    [urlSchemeTask didFinish];
}

- (void)webView:(WKWebView *)webView stopURLSchemeTask:(id<WKURLSchemeTask>)urlSchemeTask {
}

@end
