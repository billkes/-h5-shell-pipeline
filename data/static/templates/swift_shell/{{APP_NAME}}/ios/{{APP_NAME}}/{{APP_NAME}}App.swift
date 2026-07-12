import SwiftUI
import UIKit

enum {{APP_NAME}}LaunchStyle {
    static let backgroundColor = UIColor(red: 253 / 255, green: 251 / 255, blue: 247 / 255, alpha: 1)
}

@main
struct {{APP_NAME}}App: App {
    init() {
        {{APP_NAME}}WebViewDeflavor.install()
        _ = {{APP_NAME}}LaunchStyle.backgroundColor
    }

    var body: some Scene {
        WindowGroup {
            {{APP_NAME}}HostContainer()
                .ignoresSafeArea()
                .background(Color(uiColor: {{APP_NAME}}LaunchStyle.backgroundColor))
        }
    }
}

struct {{APP_NAME}}HostContainer: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> {{APP_NAME}}WebViewController {
        {{APP_NAME}}WebViewController()
    }

    func updateUIViewController(_ uiViewController: {{APP_NAME}}WebViewController, context: Context) {}
}
