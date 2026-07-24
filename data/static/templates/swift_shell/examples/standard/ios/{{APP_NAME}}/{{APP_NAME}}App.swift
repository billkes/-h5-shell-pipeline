import UIKit

enum {{APP_NAME}}LaunchStyle {
    static let backgroundColor = UIColor(red: 253 / 255, green: 251 / 255, blue: 247 / 255, alpha: 1)
}

@main
final class {{APP_NAME}}AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        {{APP_NAME}}WebViewDeflavor.install()
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.backgroundColor = {{APP_NAME}}LaunchStyle.backgroundColor
        window.rootViewController = {{APP_NAME}}WebViewController()
        window.makeKeyAndVisible()
        self.window = window
        return true
    }
}
