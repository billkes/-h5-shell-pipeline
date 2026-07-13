#import "{{PREFIX_CAP}}WebViewDeflavor.h"
#import <WebKit/WebKit.h>
#import <objc/runtime.h>

static NSMutableSet<NSString *> *g{{PREFIX_CAP}}PatchedClasses;

static UIView *{{PREFIX}}NilInputAccessoryView(id self, SEL _cmd) {
    return nil;
}

static void {{PREFIX}}PatchInputAccessoryForClass(Class cls) {
    if (!cls) return;
    if (!g{{PREFIX_CAP}}PatchedClasses) {
        g{{PREFIX_CAP}}PatchedClasses = [NSMutableSet set];
    }
    NSString *key = NSStringFromClass(cls);
    if ([g{{PREFIX_CAP}}PatchedClasses containsObject:key]) return;

    Method method = class_getInstanceMethod(cls, @selector(inputAccessoryView));
    if (!method) return;

    method_setImplementation(method, (IMP){{PREFIX}}NilInputAccessoryView);
    [g{{PREFIX_CAP}}PatchedClasses addObject:key];
}

static void {{PREFIX}}PatchKnownContentViewClasses(void) {
    NSArray<NSString *> *names = @[
        @"WKContentView",
        @"WKCompositingView",
    ];
    for (NSString *name in names) {
        {{PREFIX}}PatchInputAccessoryForClass(NSClassFromString(name));
    }

    unsigned int count = 0;
    Class *classes = objc_copyClassList(&count);
    if (!classes) return;
    for (unsigned int i = 0; i < count; i++) {
        NSString *name = NSStringFromClass(classes[i]);
        if ([name hasPrefix:@"WK"] && [name containsString:@"ContentView"]) {
            {{PREFIX}}PatchInputAccessoryForClass(classes[i]);
        }
    }
    free(classes);
}

static void {{PREFIX}}PatchViewTree(UIView *view) {
    if (!view) return;
    {{PREFIX}}PatchInputAccessoryForClass([view class]);
    for (UIView *sub in view.subviews) {
        {{PREFIX}}PatchViewTree(sub);
    }
}

@implementation {{PREFIX_CAP}}WebViewDeflavor

+ (void)install {
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        {{PREFIX}}PatchKnownContentViewClasses();
    });
}

+ (void)patchWebView:(WKWebView *)webView {
    if (!webView) return;
    [self install];
    {{PREFIX}}PatchViewTree(webView);
    dispatch_async(dispatch_get_main_queue(), ^{
        {{PREFIX}}PatchViewTree(webView);
    });
}

@end
