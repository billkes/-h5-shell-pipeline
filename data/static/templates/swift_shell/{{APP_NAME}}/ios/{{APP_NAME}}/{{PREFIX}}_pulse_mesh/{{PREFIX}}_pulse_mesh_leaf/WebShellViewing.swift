import Foundation

protocol WebShellViewing: AnyObject {
    var isErrorOverlayVisible: Bool { get }

    func beginLoadingShell()
    func requestLoad(source: WebContentSource)
    func showConnectionErrorState()
    func showLoadErrorState(title: String, message: String)
    func showConfigurationErrorState(message: String)
    func revealShellContent()
    func injectSafeAreaInsets(top: CGFloat, bottom: CGFloat)
}
