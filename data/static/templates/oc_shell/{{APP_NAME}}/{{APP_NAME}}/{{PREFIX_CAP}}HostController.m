#import "{{PREFIX_CAP}}HostController.h"
#import "{{PREFIX_CAP}}LaneVault.h"
#import "{{PREFIX_CAP}}PulseCredit.h"
#import "{{PREFIX_CAP}}WebViewDeflavor.h"
#import <WebKit/WebKit.h>
#import <Photos/Photos.h>
#import <AVFoundation/AVFoundation.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>
#import <Network/Network.h>

@interface {{PREFIX_CAP}}HostController () <WKScriptMessageHandler, WKNavigationDelegate, UIImagePickerControllerDelegate, UINavigationControllerDelegate>
@property (nonatomic, strong) WKWebView *{{PREFIX}}Surface;
@property (nonatomic, strong) UIImageView *{{PREFIX}}Veil;
@property (nonatomic, strong) UIView *{{PREFIX}}VeilHud;
@property (nonatomic, strong) UIActivityIndicatorView *{{PREFIX}}VeilSpinner;
@property (nonatomic, strong) UILabel *{{PREFIX}}VeilLabel;
@property (nonatomic, strong) UIView *{{PREFIX}}RetryPanel;
@property (nonatomic, strong) UIButton *{{PREFIX}}Retry;
@property (nonatomic, strong) UILabel *{{PREFIX}}RetryLabel;
@property (nonatomic, strong) UILabel *{{PREFIX}}RetryTitle;
@property (nonatomic, strong) {{PREFIX_CAP}}LaneVault *{{PREFIX}}Vault;
@property (nonatomic, strong) {{PREFIX_CAP}}PulseCredit *{{PREFIX}}Credit;
@property (nonatomic, copy) NSString *{{PREFIX}}EntryUrl;
@property (nonatomic, copy) NSString *{{PREFIX}}PickCallbackId;
@property (nonatomic, copy) NSString *{{PREFIX}}LastPickedRelPath;
@property (nonatomic, assign) BOOL {{PREFIX}}ShellReady;
@property (nonatomic, copy) dispatch_block_t {{PREFIX}}VeilTimeoutWork;
@property (nonatomic, strong) nw_path_monitor_t {{PREFIX}}PathMonitor;
@property (nonatomic, assign) BOOL {{PREFIX}}PathSatisfied;
@property (nonatomic, assign) BOOL {{PREFIX}}LoadPending;
@property (nonatomic, assign) BOOL {{PREFIX}}NeedsReload;
@property (nonatomic, assign) NSInteger {{PREFIX}}AutoRetryCount;
@property (nonatomic, copy) dispatch_block_t {{PREFIX}}AutoRetryWork;
@end

@implementation {{PREFIX_CAP}}HostController

- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor = [UIColor colorWithRed:0.980 green:0.961 blue:1.0 alpha:1.0];
    self.{{PREFIX}}Credit = [[{{PREFIX_CAP}}PulseCredit alloc] init];
    self.{{PREFIX}}Vault = [[{{PREFIX_CAP}}LaneVault alloc] init];
    self.{{PREFIX}}PathSatisfied = YES;
    [self {{PREFIX}}LoadRegister];
    [self {{PREFIX}}BuildSurface];
    [self {{PREFIX}}BuildVeil];
    [self {{PREFIX}}BuildRetry];
    [self {{PREFIX}}StartPathMonitor];
    [[NSNotificationCenter defaultCenter] addObserver:self
                                             selector:@selector({{PREFIX}}AppDidBecomeActive)
                                                 name:UIApplicationDidBecomeActiveNotification
                                               object:nil];
    [self {{PREFIX}}OpenEntry];
}

- (void)dealloc {
    [[NSNotificationCenter defaultCenter] removeObserver:self];
    [self {{PREFIX}}CancelAutoRetry];
    if (self.{{PREFIX}}PathMonitor) {
        nw_path_monitor_cancel(self.{{PREFIX}}PathMonitor);
        self.{{PREFIX}}PathMonitor = nil;
    }
}

- (void){{PREFIX}}LoadRegister {
    NSString *path = [[NSBundle mainBundle] pathForResource:@"本包登记信息" ofType:@"json"];
    if (!path) {
        path = [[NSBundle mainBundle] pathForResource:@"register" ofType:@"json"];
    }
    NSData *data = path ? [NSData dataWithContentsOfFile:path] : nil;
    if (data) {
        NSDictionary *json = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
        NSString *url = [json isKindOfClass:[NSDictionary class]] ? json[@"h5EntryUrl"] : nil;
        if ([url isKindOfClass:[NSString class]] && url.length) {
            self.{{PREFIX}}EntryUrl = url;
            return;
        }
    }
    self.{{PREFIX}}EntryUrl = @"https://{{H5_HOST}}/{{APP_SLUG}}/{{PREFIX}}_entry.htm";
}

- (void){{PREFIX}}BuildSurface {
    WKWebViewConfiguration *cfg = [[WKWebViewConfiguration alloc] init];
    cfg.allowsInlineMediaPlayback = YES;
    if (@available(iOS 14.0, *)) {
        cfg.defaultWebpagePreferences.allowsContentJavaScript = YES;
    }
    [cfg setURLSchemeHandler:self.{{PREFIX}}Vault forURLScheme:@"{{ASSET_SCHEME}}"];
    NSString *inject =
    @"(function(){if(window.{{PREFIX}}Native)return;"
    "window.{{PREFIX}}Native={call:function(action,payload){"
    "payload=payload||{};payload.action=action;"
    "try{window.webkit.messageHandlers.{{PREFIX}}.postMessage(payload);}catch(e){}"
    "}};"
    "window.{{PREFIX}}_kit=window.{{PREFIX}}_kit||{};"
    "window.{{PREFIX}}_kit.bridge={call:function(a,p){return window.{{PREFIX}}Native.call(a,p);}};"
    "})();";
    WKUserScript *script = [[WKUserScript alloc] initWithSource:inject
                                                  injectionTime:WKUserScriptInjectionTimeAtDocumentStart
                                               forMainFrameOnly:NO];
    [cfg.userContentController addUserScript:script];
    [cfg.userContentController addScriptMessageHandler:self name:@"{{PREFIX}}"];
    self.{{PREFIX}}Surface = [[WKWebView alloc] initWithFrame:self.view.bounds configuration:cfg];
    self.{{PREFIX}}Surface.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    self.{{PREFIX}}Surface.navigationDelegate = self;
    UIScrollView *scroll = self.{{PREFIX}}Surface.scrollView;
    scroll.bounces = NO;
    scroll.bouncesZoom = NO;
    scroll.minimumZoomScale = 1.0;
    scroll.maximumZoomScale = 1.0;
    scroll.contentInsetAdjustmentBehavior = UIScrollViewContentInsetAdjustmentNever;
    scroll.contentInset = UIEdgeInsetsZero;
    scroll.scrollIndicatorInsets = UIEdgeInsetsZero;
    self.{{PREFIX}}Surface.opaque = NO;
    self.{{PREFIX}}Surface.backgroundColor = self.view.backgroundColor;
    [self {{PREFIX}}StripDoubleTapGestures:self.{{PREFIX}}Surface.scrollView];
    dispatch_async(dispatch_get_main_queue(), ^{
        [self {{PREFIX}}StripDoubleTapGestures:self.{{PREFIX}}Surface.scrollView];
    });
    [self.view addSubview:self.{{PREFIX}}Surface];
    [{{PREFIX_CAP}}WebViewDeflavor patchWebView:self.{{PREFIX}}Surface];
}

- (void)viewSafeAreaInsetsDidChange {
    [super viewSafeAreaInsetsDidChange];
    [self {{PREFIX}}PushSafeAreaInsets];
}

- (void){{PREFIX}}PushSafeAreaInsets {
    if (!self.{{PREFIX}}Surface) return;
    UIEdgeInsets inset = self.view.safeAreaInsets;
    NSString *js = [NSString stringWithFormat:
        @"(function(){var d=document.documentElement;var px=function(v){var n=parseFloat(v);return(isFinite(n)&&n>0)?(n+'px'):'0px';};"
        "d.style.setProperty('--safe-top',px(%f));d.style.setProperty('--safe-bottom',px(%f));"
        "if(window.{{PREFIX}}_kit&&window.{{PREFIX}}_kit.ui&&window.{{PREFIX}}_kit.ui.applySafeArea){"
        "window.{{PREFIX}}_kit.ui.applySafeArea({safeTop:%f,safeBottom:%f});}})();",
        inset.top, inset.bottom, inset.top, inset.bottom];
    dispatch_async(dispatch_get_main_queue(), ^{
        [self.{{PREFIX}}Surface evaluateJavaScript:js completionHandler:nil];
    });
}

- (void){{PREFIX}}StripDoubleTapGestures:(UIView *)view {
    if (!view) return;
    for (UIGestureRecognizer *gr in view.gestureRecognizers) {
        if ([gr isKindOfClass:[UITapGestureRecognizer class]]) {
            UITapGestureRecognizer *tap = (UITapGestureRecognizer *)gr;
            if (tap.numberOfTapsRequired == 2) {
                tap.enabled = NO;
            }
        }
    }
    for (UIView *sub in view.subviews) {
        [self {{PREFIX}}StripDoubleTapGestures:sub];
    }
}

- (UIColor *){{PREFIX}}BrandBlue {
    return [UIColor colorWithRed:0.145 green:0.388 blue:0.922 alpha:1.0];
}

- (UIColor *){{PREFIX}}BrandPink {
    return [UIColor colorWithRed:0.925 green:0.286 blue:0.600 alpha:1.0];
}

- (void){{PREFIX}}BuildVeil {
    self.{{PREFIX}}Veil = [[UIImageView alloc] initWithFrame:self.view.bounds];
    self.{{PREFIX}}Veil.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    self.{{PREFIX}}Veil.contentMode = UIViewContentModeScaleAspectFill;
    UIImage *img = [UIImage imageNamed:@"launch_placeholder"];
    if (!img) {
        NSString *p = [[NSBundle mainBundle] pathForResource:@"launch_placeholder" ofType:@"png"];
        if (p) img = [UIImage imageWithContentsOfFile:p];
    }
    self.{{PREFIX}}Veil.image = img;
    self.{{PREFIX}}Veil.backgroundColor = self.view.backgroundColor;
    [self.view addSubview:self.{{PREFIX}}Veil];

    self.{{PREFIX}}VeilHud = [[UIView alloc] initWithFrame:CGRectZero];
    self.{{PREFIX}}VeilHud.backgroundColor = [UIColor colorWithRed:1.0 green:1.0 blue:1.0 alpha:0.82];
    self.{{PREFIX}}VeilHud.layer.cornerRadius = 16;
    self.{{PREFIX}}VeilHud.layer.borderWidth = 1;
    self.{{PREFIX}}VeilHud.layer.borderColor = [UIColor colorWithRed:0.894 green:0.925 blue:0.992 alpha:1.0].CGColor;
    [self.{{PREFIX}}Veil addSubview:self.{{PREFIX}}VeilHud];

    if (@available(iOS 13.0, *)) {
        self.{{PREFIX}}VeilSpinner = [[UIActivityIndicatorView alloc] initWithActivityIndicatorStyle:UIActivityIndicatorViewStyleLarge];
    } else {
        self.{{PREFIX}}VeilSpinner = [[UIActivityIndicatorView alloc] initWithActivityIndicatorStyle:UIActivityIndicatorViewStyleWhiteLarge];
    }
    self.{{PREFIX}}VeilSpinner.color = [UIColor colorWithRed:0.486 green:0.227 blue:0.929 alpha:1.0];
    [self.{{PREFIX}}VeilHud addSubview:self.{{PREFIX}}VeilSpinner];

    self.{{PREFIX}}VeilLabel = [[UILabel alloc] initWithFrame:CGRectZero];
    self.{{PREFIX}}VeilLabel.text = @"Loading…";
    self.{{PREFIX}}VeilLabel.textColor = [UIColor colorWithRed:0.392 green:0.455 blue:0.545 alpha:1.0];
    self.{{PREFIX}}VeilLabel.font = [UIFont systemFontOfSize:14 weight:UIFontWeightSemibold];
    self.{{PREFIX}}VeilLabel.textAlignment = NSTextAlignmentCenter;
    [self.{{PREFIX}}VeilHud addSubview:self.{{PREFIX}}VeilLabel];
}

- (void){{PREFIX}}BuildRetry {
    self.{{PREFIX}}RetryPanel = [[UIView alloc] initWithFrame:CGRectZero];
    self.{{PREFIX}}RetryPanel.backgroundColor = [UIColor colorWithWhite:0 alpha:0.38];
    self.{{PREFIX}}RetryPanel.layer.cornerRadius = 16;
    self.{{PREFIX}}RetryPanel.layer.borderWidth = 1;
    self.{{PREFIX}}RetryPanel.layer.borderColor = [UIColor colorWithWhite:1 alpha:0.14].CGColor;
    self.{{PREFIX}}RetryPanel.hidden = YES;
    self.{{PREFIX}}RetryPanel.alpha = 0;
    [self.view addSubview:self.{{PREFIX}}RetryPanel];

    self.{{PREFIX}}RetryTitle = [[UILabel alloc] initWithFrame:CGRectZero];
    self.{{PREFIX}}RetryTitle.text = @"Connection issue";
    self.{{PREFIX}}RetryTitle.textColor = [UIColor whiteColor];
    self.{{PREFIX}}RetryTitle.font = [UIFont systemFontOfSize:18 weight:UIFontWeightBold];
    self.{{PREFIX}}RetryTitle.textAlignment = NSTextAlignmentCenter;
    [self.{{PREFIX}}RetryPanel addSubview:self.{{PREFIX}}RetryTitle];

    self.{{PREFIX}}RetryLabel = [[UILabel alloc] initWithFrame:CGRectZero];
    self.{{PREFIX}}RetryLabel.text = @"Unable to load. Check your connection.";
    self.{{PREFIX}}RetryLabel.textColor = [UIColor colorWithWhite:1 alpha:0.82];
    self.{{PREFIX}}RetryLabel.font = [UIFont systemFontOfSize:14 weight:UIFontWeightRegular];
    self.{{PREFIX}}RetryLabel.textAlignment = NSTextAlignmentCenter;
    self.{{PREFIX}}RetryLabel.numberOfLines = 0;
    [self.{{PREFIX}}RetryPanel addSubview:self.{{PREFIX}}RetryLabel];

    self.{{PREFIX}}Retry = [UIButton buttonWithType:UIButtonTypeSystem];
    [self.{{PREFIX}}Retry setTitle:@"Retry" forState:UIControlStateNormal];
    [self.{{PREFIX}}Retry setTitleColor:[UIColor whiteColor] forState:UIControlStateNormal];
    self.{{PREFIX}}Retry.titleLabel.font = [UIFont systemFontOfSize:16 weight:UIFontWeightSemibold];
    self.{{PREFIX}}Retry.backgroundColor = [self {{PREFIX}}BrandPink];
    self.{{PREFIX}}Retry.layer.cornerRadius = 10;
    [self.{{PREFIX}}Retry addTarget:self action:@selector({{PREFIX}}RetryTapped) forControlEvents:UIControlEventTouchUpInside];
    [self.{{PREFIX}}Retry addTarget:self action:@selector({{PREFIX}}RetryTouchDown:) forControlEvents:UIControlEventTouchDown];
    [self.{{PREFIX}}Retry addTarget:self action:@selector({{PREFIX}}RetryTouchUp:) forControlEvents:UIControlEventTouchUpInside | UIControlEventTouchUpOutside | UIControlEventTouchCancel];
    [self.{{PREFIX}}RetryPanel addSubview:self.{{PREFIX}}Retry];
}

- (void){{PREFIX}}RetryTouchDown:(UIButton *)sender {
    [UIView animateWithDuration:0.12 animations:^{
        sender.transform = CGAffineTransformMakeScale(0.97, 0.97);
        sender.alpha = 0.88;
    }];
}

- (void){{PREFIX}}RetryTapped {
    self.{{PREFIX}}AutoRetryCount = 0;
    self.{{PREFIX}}NeedsReload = YES;
    [self {{PREFIX}}OpenEntry];
}

- (void){{PREFIX}}RetryTouchUp:(UIButton *)sender {
    [UIView animateWithDuration:0.18 delay:0 usingSpringWithDamping:0.82 initialSpringVelocity:0.4 options:0 animations:^{
        sender.transform = CGAffineTransformIdentity;
        sender.alpha = 1;
    } completion:nil];
}

- (void)viewDidLayoutSubviews {
    [super viewDidLayoutSubviews];
    CGFloat w = self.view.bounds.size.width;
    CGFloat h = self.view.bounds.size.height;

    CGFloat hudW = MIN(w - 80, 220);
    CGFloat hudH = 108;
    self.{{PREFIX}}VeilHud.frame = CGRectMake((w - hudW) / 2.0, h * 0.56, hudW, hudH);
    self.{{PREFIX}}VeilSpinner.frame = CGRectMake((hudW - 37) / 2.0, 18, 37, 37);
    self.{{PREFIX}}VeilLabel.frame = CGRectMake(12, 62, hudW - 24, 22);

    CGFloat panelW = MIN(w - 48, 320);
    CGFloat panelH = 188;
    self.{{PREFIX}}RetryPanel.frame = CGRectMake((w - panelW) / 2.0, h * 0.38, panelW, panelH);
    self.{{PREFIX}}RetryTitle.frame = CGRectMake(20, 22, panelW - 40, 24);
    self.{{PREFIX}}RetryLabel.frame = CGRectMake(20, 52, panelW - 40, 52);
    self.{{PREFIX}}Retry.frame = CGRectMake(20, panelH - 64, panelW - 40, 48);
}

- (void){{PREFIX}}CancelVeilTimeout {
    if (self.{{PREFIX}}VeilTimeoutWork) {
        dispatch_block_cancel(self.{{PREFIX}}VeilTimeoutWork);
        self.{{PREFIX}}VeilTimeoutWork = nil;
    }
}

- (void){{PREFIX}}CancelAutoRetry {
    if (self.{{PREFIX}}AutoRetryWork) {
        dispatch_block_cancel(self.{{PREFIX}}AutoRetryWork);
        self.{{PREFIX}}AutoRetryWork = nil;
    }
}

- (void){{PREFIX}}ScheduleVeilTimeout {
    [self {{PREFIX}}CancelVeilTimeout];
    __weak typeof(self) weakSelf = self;
    dispatch_block_t work = dispatch_block_create(0, ^{
        __strong typeof(weakSelf) self = weakSelf;
        if (!self || self.{{PREFIX}}ShellReady || self.{{PREFIX}}Veil.hidden) return;
        if (self.{{PREFIX}}LoadPending) {
            self.{{PREFIX}}VeilLabel.text = @"Waiting for network…";
            return;
        }
        self.{{PREFIX}}RetryLabel.text = @"Still loading… Check your connection, then tap Retry.";
        [self {{PREFIX}}ShowRetryPanel];
    });
    self.{{PREFIX}}VeilTimeoutWork = work;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(12 * NSEC_PER_SEC)), dispatch_get_main_queue(), work);
}

- (void){{PREFIX}}ShowRetryPanel {
    self.{{PREFIX}}VeilHud.hidden = YES;
    [self.{{PREFIX}}VeilSpinner stopAnimating];
    self.{{PREFIX}}RetryPanel.hidden = NO;
    self.{{PREFIX}}Veil.hidden = NO;
    self.{{PREFIX}}Veil.alpha = 1;
    [self.view bringSubviewToFront:self.{{PREFIX}}Veil];
    [self.view bringSubviewToFront:self.{{PREFIX}}RetryPanel];
    self.{{PREFIX}}RetryPanel.transform = CGAffineTransformMakeTranslation(0, 12);
    [UIView animateWithDuration:0.32 delay:0 usingSpringWithDamping:0.86 initialSpringVelocity:0.4 options:0 animations:^{
        self.{{PREFIX}}RetryPanel.alpha = 1;
        self.{{PREFIX}}RetryPanel.transform = CGAffineTransformIdentity;
    } completion:nil];
}

- (void){{PREFIX}}StartPathMonitor {
    if (self.{{PREFIX}}PathMonitor) return;
    self.{{PREFIX}}PathMonitor = nw_path_monitor_create();
    nw_path_monitor_set_queue(self.{{PREFIX}}PathMonitor, dispatch_get_main_queue());
    __weak typeof(self) weakSelf = self;
    nw_path_monitor_set_update_handler(self.{{PREFIX}}PathMonitor, ^(nw_path_t path) {
        __strong typeof(weakSelf) self = weakSelf;
        if (!self) return;
        BOOL satisfied = nw_path_get_status(path) == nw_path_status_satisfied;
        BOOL wasSatisfied = self.{{PREFIX}}PathSatisfied;
        self.{{PREFIX}}PathSatisfied = satisfied;
        if (satisfied && (!wasSatisfied || self.{{PREFIX}}LoadPending || self.{{PREFIX}}NeedsReload)) {
            [self {{PREFIX}}OnNetworkReady];
        }
    });
    nw_path_monitor_start(self.{{PREFIX}}PathMonitor);
}

- (void){{PREFIX}}AppDidBecomeActive {
    if (self.{{PREFIX}}ShellReady) return;
    if (self.{{PREFIX}}NeedsReload || self.{{PREFIX}}LoadPending || !self.{{PREFIX}}RetryPanel.hidden) {
        [self {{PREFIX}}ScheduleAutoRetryAfter:0.35];
    }
}

- (void){{PREFIX}}OnNetworkReady {
    if (self.{{PREFIX}}ShellReady) return;
    self.{{PREFIX}}LoadPending = NO;
    if (self.{{PREFIX}}NeedsReload || self.{{PREFIX}}Veil.hidden == NO) {
        [self {{PREFIX}}ScheduleAutoRetryAfter:0.25];
    }
}

- (void){{PREFIX}}ScheduleAutoRetryAfter:(NSTimeInterval)delay {
    if (self.{{PREFIX}}ShellReady) return;
    if (self.{{PREFIX}}AutoRetryCount >= 4) {
        self.{{PREFIX}}RetryLabel.text = @"Unable to load. Check your connection.";
        [self {{PREFIX}}ShowRetryPanel];
        return;
    }
    [self {{PREFIX}}CancelAutoRetry];
    __weak typeof(self) weakSelf = self;
    dispatch_block_t work = dispatch_block_create(0, ^{
        __strong typeof(weakSelf) self = weakSelf;
        if (!self || self.{{PREFIX}}ShellReady) return;
        if (!self.{{PREFIX}}PathSatisfied) {
            self.{{PREFIX}}LoadPending = YES;
            self.{{PREFIX}}VeilHud.hidden = NO;
            [self.{{PREFIX}}VeilSpinner startAnimating];
            self.{{PREFIX}}VeilLabel.text = @"Waiting for network…";
            self.{{PREFIX}}RetryPanel.hidden = YES;
            self.{{PREFIX}}RetryPanel.alpha = 0;
            return;
        }
        self.{{PREFIX}}AutoRetryCount += 1;
        [self {{PREFIX}}OpenEntry];
    });
    self.{{PREFIX}}AutoRetryWork = work;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(delay * NSEC_PER_SEC)), dispatch_get_main_queue(), work);
}

- (BOOL){{PREFIX}}ShouldIgnoreNavigationError:(NSError *)error {
    if (!error) return YES;
    if ([error.domain isEqualToString:NSURLErrorDomain] && error.code == NSURLErrorCancelled) return YES;
    if ([error.domain isEqualToString:@"WebKitErrorDomain"] && error.code == 102) return YES;
    return NO;
}

- (BOOL){{PREFIX}}IsTransientNetworkError:(NSError *)error {
    if (![error.domain isEqualToString:NSURLErrorDomain]) return NO;
    switch (error.code) {
        case NSURLErrorNotConnectedToInternet:
        case NSURLErrorNetworkConnectionLost:
        case NSURLErrorTimedOut:
        case NSURLErrorCannotFindHost:
        case NSURLErrorCannotConnectToHost:
        case NSURLErrorDNSLookupFailed:
        case NSURLErrorInternationalRoamingOff:
        case NSURLErrorDataNotAllowed:
        case NSURLErrorCallIsActive:
            return YES;
        default:
            return NO;
    }
}

- (void){{PREFIX}}HandleLoadFailure:(NSError *)error {
    if ([self {{PREFIX}}ShouldIgnoreNavigationError:error]) return;
    self.{{PREFIX}}NeedsReload = YES;
    if ([self {{PREFIX}}IsTransientNetworkError:error] && self.{{PREFIX}}AutoRetryCount < 4) {
        self.{{PREFIX}}LoadPending = !self.{{PREFIX}}PathSatisfied;
        self.{{PREFIX}}RetryPanel.hidden = YES;
        self.{{PREFIX}}RetryPanel.alpha = 0;
        self.{{PREFIX}}Veil.hidden = NO;
        self.{{PREFIX}}Veil.alpha = 1;
        self.{{PREFIX}}VeilHud.hidden = NO;
        [self.{{PREFIX}}VeilSpinner startAnimating];
        self.{{PREFIX}}VeilLabel.text = self.{{PREFIX}}PathSatisfied ? @"Reconnecting…" : @"Waiting for network…";
        [self.view bringSubviewToFront:self.{{PREFIX}}Veil];
        [self {{PREFIX}}ScheduleAutoRetryAfter:self.{{PREFIX}}PathSatisfied ? 0.8 : 0.4];
        return;
    }
    self.{{PREFIX}}RetryLabel.text = @"Unable to load. Check your connection.";
    [self {{PREFIX}}ShowRetryPanel];
}

- (void){{PREFIX}}OpenEntry {
    [self {{PREFIX}}CancelVeilTimeout];
    [self {{PREFIX}}CancelAutoRetry];
    self.{{PREFIX}}RetryPanel.hidden = YES;
    self.{{PREFIX}}RetryPanel.alpha = 0;
    self.{{PREFIX}}ShellReady = NO;
    self.{{PREFIX}}NeedsReload = NO;
    self.{{PREFIX}}Veil.hidden = NO;
    self.{{PREFIX}}Veil.alpha = 1;
    self.{{PREFIX}}Veil.transform = CGAffineTransformIdentity;
    self.{{PREFIX}}VeilHud.hidden = NO;
    [self.{{PREFIX}}VeilSpinner startAnimating];
    [self.view bringSubviewToFront:self.{{PREFIX}}Veil];

    if (!self.{{PREFIX}}PathSatisfied) {
        self.{{PREFIX}}LoadPending = YES;
        self.{{PREFIX}}VeilLabel.text = @"Waiting for network…";
        [self {{PREFIX}}ScheduleVeilTimeout];
        return;
    }

    self.{{PREFIX}}LoadPending = NO;
    self.{{PREFIX}}VeilLabel.text = @"Loading…";
    [self {{PREFIX}}ScheduleVeilTimeout];
    NSString *entry = self.{{PREFIX}}EntryUrl ?: @"https://{{H5_HOST}}/{{APP_SLUG}}/{{PREFIX}}_entry.htm";
    NSURL *url = [NSURL URLWithString:entry];
    NSURLRequest *req = [NSURLRequest requestWithURL:url cachePolicy:NSURLRequestReloadIgnoringLocalCacheData timeoutInterval:30];
    [self.{{PREFIX}}Surface loadRequest:req];
}

- (void){{PREFIX}}DropVeil {
    if (self.{{PREFIX}}Veil.hidden) return;
    [self {{PREFIX}}CancelVeilTimeout];
    [self {{PREFIX}}CancelAutoRetry];
    self.{{PREFIX}}NeedsReload = NO;
    self.{{PREFIX}}LoadPending = NO;
    self.{{PREFIX}}AutoRetryCount = 0;
    self.{{PREFIX}}RetryPanel.hidden = YES;
    self.{{PREFIX}}RetryPanel.alpha = 0;
    dispatch_async(dispatch_get_main_queue(), ^{
        [UIView animateWithDuration:0.32 delay:0 options:UIViewAnimationOptionCurveEaseOut animations:^{
            self.{{PREFIX}}Veil.alpha = 0;
            self.{{PREFIX}}Veil.transform = CGAffineTransformMakeScale(1.02, 1.02);
        } completion:^(BOOL finished) {
            self.{{PREFIX}}Veil.hidden = YES;
            self.{{PREFIX}}Veil.alpha = 1;
            self.{{PREFIX}}Veil.transform = CGAffineTransformIdentity;
            [self.{{PREFIX}}VeilSpinner stopAnimating];
        }];
    });
}

#pragma mark - WKNavigationDelegate

- (void)webView:(WKWebView *)webView didFinishNavigation:(WKNavigation *)navigation {
    [{{PREFIX_CAP}}WebViewDeflavor patchWebView:webView];
    [self {{PREFIX}}StripDoubleTapGestures:webView.scrollView];
    dispatch_async(dispatch_get_main_queue(), ^{
        [self {{PREFIX}}StripDoubleTapGestures:webView.scrollView];
        [self {{PREFIX}}PushSafeAreaInsets];
    });
}

- (void)webView:(WKWebView *)webView didFailProvisionalNavigation:(WKNavigation *)navigation withError:(NSError *)error {
    [self {{PREFIX}}HandleLoadFailure:error];
}

- (void)webView:(WKWebView *)webView didFailNavigation:(WKNavigation *)navigation withError:(NSError *)error {
    [self {{PREFIX}}HandleLoadFailure:error];
}

- (void)webView:(WKWebView *)webView decidePolicyForNavigationResponse:(WKNavigationResponse *)navigationResponse decisionHandler:(void (^)(WKNavigationResponsePolicy))decisionHandler {
    if ([navigationResponse.response isKindOfClass:[NSHTTPURLResponse class]]) {
        NSInteger status = [(NSHTTPURLResponse *)navigationResponse.response statusCode];
        if (status >= 400) {
            decisionHandler(WKNavigationResponsePolicyCancel);
            self.{{PREFIX}}NeedsReload = YES;
            self.{{PREFIX}}RetryLabel.text = @"Unable to load. Check your connection.";
            [self {{PREFIX}}ShowRetryPanel];
            return;
        }
    }
    decisionHandler(WKNavigationResponsePolicyAllow);
}

#pragma mark - Bridge

- (void)userContentController:(WKUserContentController *)userContentController didReceiveScriptMessage:(WKScriptMessage *)message {
    if (![message.name isEqualToString:@"{{PREFIX}}"]) return;
    NSDictionary *body = nil;
    if ([message.body isKindOfClass:[NSDictionary class]]) {
        body = (NSDictionary *)message.body;
    } else if ([message.body isKindOfClass:[NSString class]]) {
        NSData *d = [(NSString *)message.body dataUsingEncoding:NSUTF8StringEncoding];
        body = [NSJSONSerialization JSONObjectWithData:d options:0 error:nil];
    }
    if (![body isKindOfClass:[NSDictionary class]]) return;
    NSString *action = [NSString stringWithFormat:@"%@", body[@"action"] ?: @""];
    NSString *callbackId = [NSString stringWithFormat:@"%@", body[@"callbackId"] ?: body[@"id"] ?: @""];
    if ([action isEqualToString:@"shellReady"]) {
        self.{{PREFIX}}ShellReady = YES;
        dispatch_async(dispatch_get_main_queue(), ^{
            [self {{PREFIX}}DropVeil];
        });
        [self {{PREFIX}}Callback:callbackId code:0 payload:@{}];
        return;
    }
    if ([action isEqualToString:@"getDeviceInfo"]) {
        UIEdgeInsets inset = self.view.safeAreaInsets;
        [self {{PREFIX}}Callback:callbackId code:0 payload:@{
            @"safeTop": @(inset.top),
            @"safeBottom": @(inset.bottom),
            @"version": [[NSBundle mainBundle] objectForInfoDictionaryKey:@"CFBundleShortVersionString"] ?: @"1.0.0",
            @"mediaScheme": @"{{ASSET_SCHEME}}"
        }];
        return;
    }
    if ([action isEqualToString:@"copyToClipboard"]) {
        UIPasteboard.generalPasteboard.string = [NSString stringWithFormat:@"%@", body[@"text"] ?: @""];
        [self {{PREFIX}}Callback:callbackId code:0 payload:@{}];
        return;
    }
    if ([action isEqualToString:@"readFile"]) {
        [self {{PREFIX}}ReadFile:body callbackId:callbackId];
        return;
    }
    if ([action isEqualToString:@"writeFile"]) {
        [self {{PREFIX}}WriteFile:body callbackId:callbackId];
        return;
    }
    if ([action isEqualToString:@"pickImage"] || [action isEqualToString:@"pickCamera"] || [action isEqualToString:@"pickGallery"]) {
        NSString *source = @"gallery";
        if ([action isEqualToString:@"pickCamera"]) {
            source = @"camera";
        } else if ([action isEqualToString:@"pickGallery"]) {
            source = @"gallery";
        } else {
            source = [[NSString stringWithFormat:@"%@", body[@"source"] ?: @"gallery"] lowercaseString];
        }
        [self {{PREFIX}}PresentImagePicker:source callbackId:callbackId];
        return;
    }
    if ([action isEqualToString:@"saveImage"] || [action isEqualToString:@"saveImageToAlbum"]) {
        [self {{PREFIX}}SaveImage:body callbackId:callbackId];
        return;
    }
    if ([action isEqualToString:@"purchase"]) {
        id rawPid = body[@"productId"] ?: body[@"product_id"];
        NSString *pid = [[NSString stringWithFormat:@"%@", rawPid ?: @""]
            stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
        __weak typeof(self) weakSelf = self;
        [self.{{PREFIX}}Credit {{PREFIX}}BuyProduct:pid callback:^(NSInteger code, NSDictionary *payload) {
            [weakSelf {{PREFIX}}Callback:callbackId code:code payload:payload ?: @{}];
        }];
        return;
    }
    if ([action isEqualToString:@"restorePurchases"]) {
        __weak typeof(self) weakSelf = self;
        [self.{{PREFIX}}Credit {{PREFIX}}Restore:^(NSInteger code, NSDictionary *payload) {
            [weakSelf {{PREFIX}}Callback:callbackId code:code payload:payload ?: @{}];
        }];
        return;
    }
    if ([action isEqualToString:@"mediaServe"]) {
        NSString *rel = [NSString stringWithFormat:@"%@", body[@"path"] ?: @""];
        NSString *url = [NSString stringWithFormat:@"{{ASSET_SCHEME}}://local/%@", rel];
        [self {{PREFIX}}Callback:callbackId code:0 payload:@{@"url": url}];
        return;
    }
    if ([action isEqualToString:@"openLegal"]) {
        [self {{PREFIX}}Callback:callbackId code:0 payload:@{@"ok": @YES}];
        return;
    }
    [self {{PREFIX}}Callback:callbackId code:-1 payload:@{@"message": @"unknown action"}];
}

- (NSString *){{PREFIX}}Docs {
    return NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).firstObject;
}

- (void){{PREFIX}}PresentImagePicker:(NSString *)source callbackId:(NSString *)callbackId {
    self.{{PREFIX}}PickCallbackId = callbackId;
    BOOL wantsCamera = [[source lowercaseString] isEqualToString:@"camera"];
    if (wantsCamera) {
        if (![UIImagePickerController isSourceTypeAvailable:UIImagePickerControllerSourceTypeCamera]) {
            [self {{PREFIX}}Callback:callbackId code:-1 payload:@{@"message": @"Camera unavailable"}];
            return;
        }
        AVAuthorizationStatus auth = [AVCaptureDevice authorizationStatusForMediaType:AVMediaTypeVideo];
        if (auth == AVAuthorizationStatusDenied || auth == AVAuthorizationStatusRestricted) {
            [self {{PREFIX}}Callback:callbackId code:-1 payload:@{@"message": @"PERMISSION_DENIED"}];
            return;
        }
        if (auth == AVAuthorizationStatusNotDetermined) {
            __weak typeof(self) weakSelf = self;
            [AVCaptureDevice requestAccessForMediaType:AVMediaTypeVideo completionHandler:^(BOOL granted) {
                dispatch_async(dispatch_get_main_queue(), ^{
                    if (!granted) {
                        [weakSelf {{PREFIX}}Callback:callbackId code:-1 payload:@{@"message": @"PERMISSION_DENIED"}];
                        return;
                    }
                    [weakSelf {{PREFIX}}ShowImagePicker:YES callbackId:callbackId];
                });
            }];
            return;
        }
        [self {{PREFIX}}ShowImagePicker:YES callbackId:callbackId];
        return;
    }
    [self {{PREFIX}}ShowImagePicker:NO callbackId:callbackId];
}

- (void){{PREFIX}}ShowImagePicker:(BOOL)camera callbackId:(NSString *)callbackId {
    self.{{PREFIX}}PickCallbackId = callbackId;
    UIImagePickerController *picker = [[UIImagePickerController alloc] init];
    picker.delegate = self;
    picker.sourceType = camera ? UIImagePickerControllerSourceTypeCamera : UIImagePickerControllerSourceTypePhotoLibrary;
    if (camera) {
        picker.cameraCaptureMode = UIImagePickerControllerCameraCaptureModePhoto;
        picker.modalPresentationStyle = UIModalPresentationFullScreen;
    }
    [self presentViewController:picker animated:YES completion:nil];
}

- (void){{PREFIX}}ReadFile:(NSDictionary *)body callbackId:(NSString *)callbackId {
    NSString *rel = [NSString stringWithFormat:@"%@", body[@"path"] ?: @""];
    NSString *full = [[self {{PREFIX}}Docs] stringByAppendingPathComponent:rel];
    NSData *data = [NSData dataWithContentsOfFile:full];
    if (!data) {
        [self {{PREFIX}}Callback:callbackId code:-1 payload:@{@"message": @"FILE_NOT_FOUND"}];
        return;
    }
    NSString *b64 = [data base64EncodedStringWithOptions:0];
    [self {{PREFIX}}Callback:callbackId code:0 payload:@{@"path": rel, @"base64": b64}];
}

- (void){{PREFIX}}WriteFile:(NSDictionary *)body callbackId:(NSString *)callbackId {
    NSString *rel = [NSString stringWithFormat:@"%@", body[@"path"] ?: @""];
    NSString *b64 = [NSString stringWithFormat:@"%@", body[@"base64"] ?: body[@"data"] ?: @""];
    NSData *data = [[NSData alloc] initWithBase64EncodedString:b64 options:0];
    if (!data.length || !rel.length) {
        [self {{PREFIX}}Callback:callbackId code:-1 payload:@{@"message": @"bad payload"}];
        return;
    }
    NSString *full = [[self {{PREFIX}}Docs] stringByAppendingPathComponent:rel];
    [[NSFileManager defaultManager] createDirectoryAtPath:full.stringByDeletingLastPathComponent
                              withIntermediateDirectories:YES attributes:nil error:nil];
    BOOL ok = [data writeToFile:full atomically:YES];
    [self {{PREFIX}}Callback:callbackId code:(ok ? 0 : -1) payload:@{@"path": rel}];
}

- (void){{PREFIX}}SaveImage:(NSDictionary *)body callbackId:(NSString *)callbackId {
    NSString *rel = [NSString stringWithFormat:@"%@", body[@"path"] ?: @""];
    if (!rel.length) {
        rel = self.{{PREFIX}}LastPickedRelPath ?: @"";
    }
    NSString *full = rel.length ? [[self {{PREFIX}}Docs] stringByAppendingPathComponent:rel] : @"";
    UIImage *img = full.length ? [UIImage imageWithContentsOfFile:full] : nil;
    if (!img && body[@"base64"]) {
        NSData *d = [[NSData alloc] initWithBase64EncodedString:[NSString stringWithFormat:@"%@", body[@"base64"]] options:0];
        img = [UIImage imageWithData:d];
    }
    if (!img) {
        NSString *bundlePath = [[NSBundle mainBundle] pathForResource:@"launch_placeholder" ofType:@"png"];
        if (bundlePath) {
            img = [UIImage imageWithContentsOfFile:bundlePath];
        }
    }
    if (!img) {
        [self {{PREFIX}}Callback:callbackId code:-1 payload:@{@"message": @"FILE_NOT_FOUND"}];
        return;
    }
    void (^saveBlock)(void) = ^{
        [[PHPhotoLibrary sharedPhotoLibrary] performChanges:^{
            [PHAssetChangeRequest creationRequestForAssetFromImage:img];
        } completionHandler:^(BOOL success, NSError * _Nullable error) {
            dispatch_async(dispatch_get_main_queue(), ^{
                if (success) {
                    [self {{PREFIX}}Callback:callbackId code:0 payload:@{@"saved": @YES, @"path": rel ?: @""}];
                } else {
                    [self {{PREFIX}}Callback:callbackId code:-1 payload:@{@"message": error.localizedDescription ?: @"PERMISSION_DENIED"}];
                }
            });
        }];
    };
    if (@available(iOS 14, *)) {
        PHAuthorizationStatus addAuth = [PHPhotoLibrary authorizationStatusForAccessLevel:PHAccessLevelAddOnly];
        if (addAuth == PHAuthorizationStatusNotDetermined) {
            [PHPhotoLibrary requestAuthorizationForAccessLevel:PHAccessLevelAddOnly handler:^(PHAuthorizationStatus status) {
                dispatch_async(dispatch_get_main_queue(), ^{
                    if (status == PHAuthorizationStatusAuthorized || status == PHAuthorizationStatusLimited) {
                        saveBlock();
                    } else {
                        [self {{PREFIX}}Callback:callbackId code:-1 payload:@{@"message": @"PERMISSION_DENIED"}];
                    }
                });
            }];
            return;
        }
        if (addAuth == PHAuthorizationStatusDenied || addAuth == PHAuthorizationStatusRestricted) {
            [self {{PREFIX}}Callback:callbackId code:-1 payload:@{@"message": @"PERMISSION_DENIED"}];
            return;
        }
    }
    saveBlock();
}

- (void)imagePickerController:(UIImagePickerController *)picker didFinishPickingMediaWithInfo:(NSDictionary<UIImagePickerControllerInfoKey,id> *)info {
    UIImage *img = info[UIImagePickerControllerOriginalImage];
    [picker dismissViewControllerAnimated:YES completion:nil];
    if (!img) {
        [self {{PREFIX}}Callback:self.{{PREFIX}}PickCallbackId code:-2 payload:@{@"message": @"USER_CANCELLED"}];
        return;
    }
    NSData *data = UIImageJPEGRepresentation(img, 0.9);
    NSString *rel = [NSString stringWithFormat:@"poses/pose_%@.jpg", @((NSInteger)[[NSDate date] timeIntervalSince1970])];
    NSString *full = [[self {{PREFIX}}Docs] stringByAppendingPathComponent:rel];
    [[NSFileManager defaultManager] createDirectoryAtPath:full.stringByDeletingLastPathComponent
                              withIntermediateDirectories:YES attributes:nil error:nil];
    [data writeToFile:full atomically:YES];
    self.{{PREFIX}}LastPickedRelPath = rel;
    [self {{PREFIX}}Callback:self.{{PREFIX}}PickCallbackId code:0 payload:@{@"path": rel}];
}

- (void)imagePickerControllerDidCancel:(UIImagePickerController *)picker {
    [picker dismissViewControllerAnimated:YES completion:nil];
    [self {{PREFIX}}Callback:self.{{PREFIX}}PickCallbackId code:-2 payload:@{@"message": @"USER_CANCELLED"}];
}

- (void){{PREFIX}}Callback:(NSString *)callbackId code:(NSInteger)code payload:(NSDictionary *)payload {
    NSMutableDictionary *q = [NSMutableDictionary dictionary];
    q[@"code"] = [NSString stringWithFormat:@"%ld", (long)code];
    if (callbackId.length) q[@"callbackId"] = callbackId;
    for (NSString *k in payload) {
        id v = payload[k];
        if ([v isKindOfClass:[NSString class]] || [v isKindOfClass:[NSNumber class]]) {
            q[k] = [NSString stringWithFormat:@"%@", v];
        }
    }
    NSURLComponents *comp = [[NSURLComponents alloc] init];
    comp.scheme = @"app-callback";
    comp.host = @"{{PREFIX}}";
    NSMutableArray *items = [NSMutableArray array];
    for (NSString *k in q) {
        [items addObject:[NSURLQueryItem queryItemWithName:k value:q[k]]];
    }
    comp.queryItems = items;
    NSString *url = comp.URL.absoluteString ?: @"app-callback://{{PREFIX}}?code=-1";
    NSString *js = [NSString stringWithFormat:
                    @"(function(){var u=%@;try{if(window.{{PREFIX}}Native&&window.{{PREFIX}}Native.onCallback){window.{{PREFIX}}Native.onCallback(u);}else{window.dispatchEvent(new CustomEvent('{{PREFIX}}-callback',{detail:u}));}var a=document.createElement('a');a.href=u;}catch(e){}})();",
                    [self {{PREFIX}}JsonString:url]];
    dispatch_async(dispatch_get_main_queue(), ^{
        [self.{{PREFIX}}Surface evaluateJavaScript:js completionHandler:nil];
    });
}

- (NSString *){{PREFIX}}JsonString:(NSString *)s {
    NSData *d = [NSJSONSerialization dataWithJSONObject:@[s ?: @""] options:0 error:nil];
    NSString *arr = [[NSString alloc] initWithData:d encoding:NSUTF8StringEncoding];
    if (arr.length >= 2) {
        return [arr substringWithRange:NSMakeRange(1, arr.length - 2)];
    }
    return @"\"\"";
}

@end
