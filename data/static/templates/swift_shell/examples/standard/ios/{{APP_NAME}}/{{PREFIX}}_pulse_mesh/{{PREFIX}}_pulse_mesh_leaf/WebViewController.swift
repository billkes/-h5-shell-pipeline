import SwiftUI
import WebKit

final class {{APP_NAME}}WebViewController: UIViewController {
    private let viewModel = {{APP_NAME}}WebShellViewModel()

    private var webView: WKWebView!
    private var bridgeHandler: WebBridgeHandler!
    private var assetHandler: {{APP_NAME}}AssetScheme!
    private var launchVeilView: UIView!
    private var launchVeilImageView: UIImageView!
    private var errorView: UIView!
    private var errorTitleLabel: UILabel!
    private var errorMessageLabel: UILabel!
    private var progressObservation: NSKeyValueObservation?

    var isErrorOverlayVisible: Bool {
        errorView?.isHidden == false
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = {{APP_NAME}}LaunchStyle.backgroundColor

        setupLaunchVeil()
        setupErrorOverlay()
        setupWebView()

        viewModel.attachView(self)
        viewModel.viewDidLoad()
    }

    deinit {
        progressObservation?.invalidate()
        viewModel.tearDown()
    }

    // MARK: - Setup

    private func setupWebView() {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []

        assetHandler = {{APP_NAME}}AssetScheme()
        config.setURLSchemeHandler(assetHandler, forURLScheme: {{APP_NAME}}ShellConfig.assetScheme)
        {{APP_NAME}}SeedAssets.ensureCopied()

        let bridgeBootstrap = """
        window.__{{APP_NAME_LOWER}}Native = true;
        window.{{APP_NAME_LOWER}}Bridge = window.{{APP_NAME_LOWER}}Bridge || { isNative: function() { return true; } };
        """
        config.userContentController.addUserScript(
            WKUserScript(source: bridgeBootstrap, injectionTime: .atDocumentStart, forMainFrameOnly: true)
        )

        let handler = WebBridgeHandler(presentingVC: self)
        handler.onShellReady = { [weak self] in
            self?.viewModel.handleShellReady()
        }
        bridgeHandler = handler
        config.userContentController.add(handler, name: "{{APP_NAME_LOWER}}Bridge")

        webView = WKWebView(frame: .zero, configuration: config)
        {{APP_NAME}}WebViewDeflavor.apply(to: webView)
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.scrollView.bounces = true
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.scrollView.automaticallyAdjustsScrollIndicatorInsets = false
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.backgroundColor = .clear
        webView.alpha = 0
        webView.translatesAutoresizingMaskIntoConstraints = false

        if #available(iOS 16.4, *) {
            webView.isInspectable = true
        }

        view.insertSubview(webView, at: 0)

        NSLayoutConstraint.activate([
            webView.topAnchor.constraint(equalTo: view.topAnchor),
            webView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            webView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
        ])

        progressObservation = webView.observe(\.estimatedProgress, options: [.new]) { _, _ in }
        handler.webView = webView
    }

    private func setupLaunchVeil() {
        launchVeilView = UIView()
        launchVeilView.backgroundColor = {{APP_NAME}}LaunchStyle.backgroundColor
        launchVeilView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(launchVeilView)

        launchVeilImageView = UIImageView(image: UIImage(named: "LaunchPlaceholder"))
        launchVeilImageView.contentMode = .scaleAspectFill
        launchVeilImageView.clipsToBounds = true
        launchVeilImageView.translatesAutoresizingMaskIntoConstraints = false
        launchVeilView.addSubview(launchVeilImageView)

        NSLayoutConstraint.activate([
            launchVeilView.topAnchor.constraint(equalTo: view.topAnchor),
            launchVeilView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            launchVeilView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            launchVeilView.trailingAnchor.constraint(equalTo: view.trailingAnchor),

            launchVeilImageView.topAnchor.constraint(equalTo: launchVeilView.topAnchor),
            launchVeilImageView.bottomAnchor.constraint(equalTo: launchVeilView.bottomAnchor),
            launchVeilImageView.leadingAnchor.constraint(equalTo: launchVeilView.leadingAnchor),
            launchVeilImageView.trailingAnchor.constraint(equalTo: launchVeilView.trailingAnchor),
        ])
    }

    private func setupErrorOverlay() {
        errorView = UIView()
        errorView.backgroundColor = .clear
        errorView.isHidden = true
        errorView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(errorView)

        let backdropView = UIView()
        backdropView.backgroundColor = {{APP_NAME}}LaunchStyle.backgroundColor
        backdropView.translatesAutoresizingMaskIntoConstraints = false

        let cardView = UIView()
        cardView.backgroundColor = UIColor.white.withAlphaComponent(0.9)
        cardView.layer.cornerRadius = 24
        cardView.layer.shadowColor = UIColor.black.cgColor
        cardView.layer.shadowOpacity = 0.08
        cardView.layer.shadowRadius = 16
        cardView.layer.shadowOffset = CGSize(width: 0, height: 8)
        cardView.translatesAutoresizingMaskIntoConstraints = false

        let iconContainer = UIView()
        iconContainer.backgroundColor = UIColor(red: 224 / 255, green: 242 / 255, blue: 254 / 255, alpha: 1)
        iconContainer.layer.cornerRadius = 36
        iconContainer.translatesAutoresizingMaskIntoConstraints = false

        let iconConfig = UIImage.SymbolConfiguration(pointSize: 36, weight: .semibold)
        let iconView = UIImageView(
            image: UIImage(systemName: "wifi.exclamationmark", withConfiguration: iconConfig)
        )
        iconView.tintColor = UIColor(red: 14 / 255, green: 165 / 255, blue: 233 / 255, alpha: 1)
        iconView.contentMode = .scaleAspectFit
        iconView.translatesAutoresizingMaskIntoConstraints = false

        let titleLabel = UILabel()
        titleLabel.text = "Unable to Connect"
        titleLabel.font = .systemFont(ofSize: 22, weight: .semibold)
        titleLabel.textColor = UIColor(red: 51 / 255, green: 65 / 255, blue: 85 / 255, alpha: 1)
        titleLabel.textAlignment = .center
        titleLabel.translatesAutoresizingMaskIntoConstraints = false
        errorTitleLabel = titleLabel

        let messageLabel = UILabel()
        messageLabel.text = "Please check your internet connection\nand try again."
        messageLabel.font = .systemFont(ofSize: 15)
        messageLabel.textColor = UIColor(red: 0.392, green: 0.455, blue: 0.545, alpha: 1)
        messageLabel.textAlignment = .center
        messageLabel.numberOfLines = 0
        messageLabel.translatesAutoresizingMaskIntoConstraints = false
        errorMessageLabel = messageLabel

        let retryButton = UIButton(type: .system)
        retryButton.setTitle("Retry", for: .normal)
        retryButton.titleLabel?.font = .systemFont(ofSize: 17, weight: .semibold)
        retryButton.setTitleColor(.white, for: .normal)
        retryButton.backgroundColor = UIColor(red: 14 / 255, green: 165 / 255, blue: 233 / 255, alpha: 1)
        retryButton.layer.cornerRadius = 14
        retryButton.translatesAutoresizingMaskIntoConstraints = false
        retryButton.addTarget(self, action: #selector(retryTapped), for: .touchUpInside)

        errorView.addSubview(backdropView)
        errorView.addSubview(cardView)
        iconContainer.addSubview(iconView)
        cardView.addSubview(iconContainer)
        cardView.addSubview(titleLabel)
        cardView.addSubview(messageLabel)
        cardView.addSubview(retryButton)

        NSLayoutConstraint.activate([
            errorView.topAnchor.constraint(equalTo: view.topAnchor),
            errorView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            errorView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            errorView.trailingAnchor.constraint(equalTo: view.trailingAnchor),

            backdropView.topAnchor.constraint(equalTo: errorView.topAnchor),
            backdropView.bottomAnchor.constraint(equalTo: errorView.bottomAnchor),
            backdropView.leadingAnchor.constraint(equalTo: errorView.leadingAnchor),
            backdropView.trailingAnchor.constraint(equalTo: errorView.trailingAnchor),

            cardView.centerXAnchor.constraint(equalTo: errorView.centerXAnchor),
            cardView.centerYAnchor.constraint(equalTo: errorView.centerYAnchor),
            cardView.leadingAnchor.constraint(greaterThanOrEqualTo: errorView.leadingAnchor, constant: 32),
            cardView.trailingAnchor.constraint(lessThanOrEqualTo: errorView.trailingAnchor, constant: -32),
            cardView.widthAnchor.constraint(lessThanOrEqualToConstant: 320),

            iconContainer.topAnchor.constraint(equalTo: cardView.topAnchor, constant: 32),
            iconContainer.centerXAnchor.constraint(equalTo: cardView.centerXAnchor),
            iconContainer.widthAnchor.constraint(equalToConstant: 72),
            iconContainer.heightAnchor.constraint(equalToConstant: 72),

            iconView.centerXAnchor.constraint(equalTo: iconContainer.centerXAnchor),
            iconView.centerYAnchor.constraint(equalTo: iconContainer.centerYAnchor),
            iconView.widthAnchor.constraint(equalToConstant: 44),
            iconView.heightAnchor.constraint(equalToConstant: 44),

            titleLabel.topAnchor.constraint(equalTo: iconContainer.bottomAnchor, constant: 20),
            titleLabel.leadingAnchor.constraint(equalTo: cardView.leadingAnchor, constant: 24),
            titleLabel.trailingAnchor.constraint(equalTo: cardView.trailingAnchor, constant: -24),

            messageLabel.topAnchor.constraint(equalTo: titleLabel.bottomAnchor, constant: 10),
            messageLabel.leadingAnchor.constraint(equalTo: cardView.leadingAnchor, constant: 24),
            messageLabel.trailingAnchor.constraint(equalTo: cardView.trailingAnchor, constant: -24),

            retryButton.topAnchor.constraint(equalTo: messageLabel.bottomAnchor, constant: 28),
            retryButton.centerXAnchor.constraint(equalTo: cardView.centerXAnchor),
            retryButton.widthAnchor.constraint(equalToConstant: 160),
            retryButton.heightAnchor.constraint(equalToConstant: 48),
            retryButton.bottomAnchor.constraint(equalTo: cardView.bottomAnchor, constant: -32),
        ])
    }

    @objc private func retryTapped() {
        viewModel.retryLoading()
    }

    override func viewSafeAreaInsetsDidChange() {
        super.viewSafeAreaInsetsDidChange()
        let insets = view.safeAreaInsets
        viewModel.handleSafeAreaInsets(top: insets.top, bottom: insets.bottom)
    }
}

// MARK: - WebShellViewing

extension {{APP_NAME}}WebViewController: WebShellViewing {
    func beginLoadingShell() {
        errorView.isHidden = true
        launchVeilView.isHidden = false
        launchVeilView.alpha = 1
        webView.alpha = 0
    }

    func requestLoad(source: WebContentSource) {
        switch source {
        case .bundled(let url):
            let readAccess = url.deletingLastPathComponent()
            webView.loadFileURL(url, allowingReadAccessTo: readAccess)
        case .remote(let url):
            webView.load(URLRequest(url: url, cachePolicy: .useProtocolCachePolicy))
        }
    }

    func showConnectionErrorState() {
        showLoadErrorState(
            title: "Unable to Connect",
            message: "Please check your internet connection\nand try again."
        )
    }

    func showLoadErrorState(title: String, message: String) {
        webView.stopLoading()
        launchVeilView.isHidden = true
        errorView.isHidden = false
        errorTitleLabel.text = title
        errorMessageLabel.text = message
        webView.alpha = 0
    }

    func showConfigurationErrorState(message: String) {
        showLoadErrorState(title: "Configuration Error", message: message)
    }

    func revealShellContent() {
        UIView.animate(withDuration: 0.25, delay: 0, options: .curveEaseOut) {
            self.webView.alpha = 1
            self.launchVeilView.alpha = 0
        } completion: { _ in
            self.launchVeilView.isHidden = true
            self.errorView.isHidden = true
        }
    }

    func injectSafeAreaInsets(top: CGFloat, bottom: CGFloat) {
        let script = """
        document.documentElement.style.setProperty('--safe-top', '\(top)px');
        document.documentElement.style.setProperty('--safe-bottom', '\(bottom)px');
        """
        webView?.evaluateJavaScript(script)
    }
}

extension {{APP_NAME}}WebViewController: WKNavigationDelegate {
    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationResponse: WKNavigationResponse,
        decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void
    ) {
        guard navigationResponse.isForMainFrame else {
            decisionHandler(.allow)
            return
        }
        if let http = navigationResponse.response as? HTTPURLResponse, http.statusCode >= 400 {
            print("[{{APP_NAME}}] HTTP \(http.statusCode) for \(navigationResponse.response.url?.absoluteString ?? "")")
            let statusCode = http.statusCode
            DispatchQueue.main.async { [weak self] in
                self?.viewModel.handleHttpError(statusCode: statusCode)
            }
            decisionHandler(.cancel)
            return
        }
        decisionHandler(.allow)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        guard errorView?.isHidden ?? true else { return }
        {{APP_NAME}}WebViewDeflavor.apply(to: webView)
        DispatchQueue.main.async {
            {{APP_NAME}}WebViewDeflavor.apply(to: webView)
        }
        let insets = view.safeAreaInsets
        viewModel.handleSafeAreaInsets(top: insets.top, bottom: insets.bottom)
        let script = """
        window.__{{APP_NAME_LOWER}}Native = true;
        window.{{APP_NAME_LOWER}}Bridge = window.{{APP_NAME_LOWER}}Bridge || {};
        window.{{APP_NAME_LOWER}}Bridge.isNative = function() { return true; };
        """
        webView.evaluateJavaScript(script)
        viewModel.handleNavigationFinished()
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        if Self.isBenignNavigationCancel(error) { return }
        print("[{{APP_NAME}}] Navigation failed: \(error.localizedDescription)")
        viewModel.handleNavigationFailed()
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        if Self.isBenignNavigationCancel(error) { return }
        print("[{{APP_NAME}}] Provisional navigation failed: \(error.localizedDescription)")
        viewModel.handleNavigationFailed()
    }

    private static func isBenignNavigationCancel(_ error: Error) -> Bool {
        let ns = error as NSError
        // stopLoading() after timeout/retry surfaces -999; not a real connectivity failure.
        return ns.domain == NSURLErrorDomain && ns.code == NSURLErrorCancelled
    }
}

extension {{APP_NAME}}WebViewController: WKUIDelegate {
    func webView(
        _ webView: WKWebView,
        runJavaScriptAlertPanelWithMessage message: String,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping () -> Void
    ) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in completionHandler() })
        {{APP_NAME_LOWER}}TopMost.present(alert, animated: true)
    }

    func webView(
        _ webView: WKWebView,
        runJavaScriptConfirmPanelWithMessage message: String,
        initiatedByFrame frame: WKFrameInfo,
        completionHandler: @escaping (Bool) -> Void
    ) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel) { _ in completionHandler(false) })
        let confirmTitle = message.lowercased().contains("delete") ? "Delete" : "OK"
        let style: UIAlertAction.Style = confirmTitle == "Delete" ? .destructive : .default
        alert.addAction(UIAlertAction(title: confirmTitle, style: style) { _ in completionHandler(true) })
        {{APP_NAME_LOWER}}TopMost.present(alert, animated: true)
    }
}
