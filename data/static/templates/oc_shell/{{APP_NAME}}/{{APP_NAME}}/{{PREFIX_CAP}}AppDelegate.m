#import "{{PREFIX_CAP}}AppDelegate.h"
#import "{{PREFIX_CAP}}HostController.h"
#import "{{PREFIX_CAP}}WebViewDeflavor.h"

@implementation {{PREFIX_CAP}}AppDelegate

- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)launchOptions {
    [{{PREFIX_CAP}}WebViewDeflavor install];
    self.window = [[UIWindow alloc] initWithFrame:[UIScreen mainScreen].bounds];
    self.window.backgroundColor = [UIColor colorWithRed:0.980 green:0.961 blue:1.0 alpha:1.0];
    {{PREFIX_CAP}}HostController *root = [[{{PREFIX_CAP}}HostController alloc] init];
    self.window.rootViewController = root;
    [self.window makeKeyAndVisible];
    return YES;
}

@end
