import Foundation
import Network

final class {{APP_NAME}}WebShellViewModel {
    weak var view: WebShellViewing?

    private var pathMonitor: NWPathMonitor?
    private let monitorQueue = DispatchQueue(label: "com.{{APP_NAME_LOWER}}.network.shell")

    private var loadTimeoutWorkItem: DispatchWorkItem?
    private var shellReadyFallbackWorkItem: DispatchWorkItem?

    private let loadTimeout: TimeInterval = 12
    private let shellReadyFallback: TimeInterval = 4
    private var shellReadyReceived = false

    func attachView(_ view: WebShellViewing) {
        self.view = view
    }

    func viewDidLoad() {
        startNetworkMonitor()
        reloadContent()
    }

    func tearDown() {
        pathMonitor?.cancel()
        loadTimeoutWorkItem?.cancel()
        shellReadyFallbackWorkItem?.cancel()
    }

    func retryLoading() {
        reloadContent()
    }

    func handleNavigationFinished() {
        scheduleShellReadyFallback()
    }

    func handleNavigationFailed() {
        loadTimeoutWorkItem?.cancel()
        shellReadyFallbackWorkItem?.cancel()
        view?.showConnectionErrorState()
    }

    func handleHttpError(statusCode: Int) {
        loadTimeoutWorkItem?.cancel()
        shellReadyFallbackWorkItem?.cancel()
        let copy = Self.httpErrorCopy(statusCode: statusCode)
        view?.showLoadErrorState(title: copy.title, message: copy.message)
    }

    private static func httpErrorCopy(statusCode: Int) -> (title: String, message: String) {
        switch statusCode {
        case 404:
            return (
                "Page Not Found",
                "The app content is not available at this address.\nPlease try again later."
            )
        case 500...599:
            return (
                "Server Error",
                "Something went wrong on the server.\nPlease try again later."
            )
        default:
            return (
                "Unable to Load",
                "The server returned an error (HTTP \(statusCode)).\nPlease try again."
            )
        }
    }

    func handleShellReady() {
        guard !shellReadyReceived else { return }
        shellReadyReceived = true
        loadTimeoutWorkItem?.cancel()
        shellReadyFallbackWorkItem?.cancel()
        view?.revealShellContent()
    }

    func handleSafeAreaInsets(top: CGFloat, bottom: CGFloat) {
        view?.injectSafeAreaInsets(top: top, bottom: bottom)
    }

    // MARK: - Loading

    private func reloadContent() {
        loadTimeoutWorkItem?.cancel()
        shellReadyFallbackWorkItem?.cancel()
        shellReadyReceived = false

        guard let source = WebContentResolver.resolve() else {
            view?.showConfigurationErrorState(
                message: "{{APP_NAME}}ShellConfig.h5EntryUrl is invalid."
            )
            return
        }

        view?.beginLoadingShell()
        view?.requestLoad(source: source)
        scheduleLoadTimeout()
    }

    private func scheduleLoadTimeout() {
        let timeout = DispatchWorkItem { [weak self] in
            guard let self = self, !self.shellReadyReceived else { return }
            print("[{{APP_NAME}}] Load timeout, showing retry")
            self.view?.showConnectionErrorState()
        }
        loadTimeoutWorkItem = timeout
        DispatchQueue.main.asyncAfter(deadline: .now() + loadTimeout, execute: timeout)
    }

    private func scheduleShellReadyFallback() {
        shellReadyFallbackWorkItem?.cancel()
        let fallback = DispatchWorkItem { [weak self] in
            guard let self = self, !self.shellReadyReceived else { return }
            print("[{{APP_NAME}}] shellReady fallback after page finish")
            self.handleShellReady()
        }
        shellReadyFallbackWorkItem = fallback
        DispatchQueue.main.asyncAfter(deadline: .now() + shellReadyFallback, execute: fallback)
    }

    // MARK: - Network

    private func startNetworkMonitor() {
        pathMonitor = NWPathMonitor()
        pathMonitor?.pathUpdateHandler = { [weak self] path in
            guard let self = self, path.status == .satisfied else { return }
            DispatchQueue.main.async {
                if self.view?.isErrorOverlayVisible == true {
                    self.reloadContent()
                }
            }
        }
        pathMonitor?.start(queue: monitorQueue)
    }
}
