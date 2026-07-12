import Photos
import UIKit
import WebKit

final class WebBridgeHandler: NSObject, WKScriptMessageHandler {
    weak var webView: WKWebView?
    weak var presentingVC: UIViewController?
    var onShellReady: (() -> Void)?

    private let permissionManager = PermissionManager()
    private let imagePicker = ImagePickerCoordinator()
    private let audioRecorder = AudioRecorderManager()
    private let iapManager = IAPManager.shared
    private let mailComposer = FeedbackMailComposer()

    init(presentingVC: UIViewController) {
        self.presentingVC = presentingVC
        super.init()
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard let body = message.body as? [String: Any],
              let id = body["id"] as? String,
              let action = body["action"] as? String else { return }

        let payload = body["payload"]

        switch action {
        case "shellReady":
            DispatchQueue.main.async { [weak self] in
                self?.onShellReady?()
            }
            sendSuccess(id: id, data: ["ready": true])
        case "getPermissionStatus":
            handlePermissionStatus(id: id, payload: payload)
        case "requestPermission":
            handleRequestPermission(id: id, payload: payload)
        case "pickImage":
            handlePickImage(id: id, fromCamera: false)
        case "takePhoto":
            handlePickImage(id: id, fromCamera: true)
        case "startRecording":
            handleStartRecording(id: id)
        case "stopRecording":
            handleStopRecording(id: id)
        case "sendFeedback":
            handleSendFeedback(id: id, payload: payload)
        case "shareText":
            handleShareText(id: id, payload: payload)
        case "getProducts":
            handleGetProducts(id: id)
        case "purchase":
            handlePurchase(id: id, payload: payload)
        case "mediaServe":
            handleMediaServe(id: id, payload: payload)
        case "ensureSeedAssets":
            handleEnsureSeedAssets(id: id)
        default:
            sendError(id: id, message: "Unknown action: \(action)")
        }
    }

    private func handlePermissionStatus(id: String, payload: Any?) {
        guard let dict = payload as? [String: Any],
              let type = dict["type"] as? String else {
            sendError(id: id, message: "Invalid permission type")
            return
        }
        let status = permissionManager.status(for: type)
        sendSuccess(id: id, data: status)
    }

    private func handleRequestPermission(id: String, payload: Any?) {
        guard let dict = payload as? [String: Any],
              let type = dict["type"] as? String else {
            sendError(id: id, message: "Invalid permission type")
            return
        }

        permissionManager.request(type: type) { [weak self] status in
            self?.sendSuccess(id: id, data: status)
        }
    }

    private func handlePickImage(id: String, fromCamera: Bool) {
        guard presentingVC != nil else {
            sendError(id: id, message: "No presenting view controller")
            return
        }

        let permType = fromCamera ? "camera" : "photos"
        let status = permissionManager.status(for: permType)

        if status != "granted" {
            permissionManager.request(type: permType) { [weak self] newStatus in
                guard let self = self else { return }
                if newStatus == "granted" {
                    DispatchQueue.main.async {
                        guard let presenter = self.presentingVC?.{{APP_NAME_LOWER}}TopMost else {
                            self.sendError(id: id, message: "No presenting view controller")
                            return
                        }
                        self.presentImagePicker(id: id, fromCamera: fromCamera, on: presenter)
                    }
                } else {
                    self.sendError(id: id, message: "Permission denied")
                }
            }
            return
        }

        DispatchQueue.main.async { [weak self] in
            guard let self = self, let presenter = self.presentingVC?.{{APP_NAME_LOWER}}TopMost else {
                self?.sendError(id: id, message: "No presenting view controller")
                return
            }
            self.presentImagePicker(id: id, fromCamera: fromCamera, on: presenter)
        }
    }

    private func presentImagePicker(id: String, fromCamera: Bool, on vc: UIViewController) {
        imagePicker.present(from: vc, useCamera: fromCamera) { [weak self] result in
            guard let self = self else { return }
            switch result {
            case .success(let imageResult):
                self.sendSuccess(id: id, data: [
                    "path": imageResult.path,
                ])
            case .failure(let error):
                self.sendError(id: id, message: error.localizedDescription)
            }
        }
    }

    // MARK: - Audio

    private func handleStartRecording(id: String) {
        let status = permissionManager.status(for: "microphone")
        if status != "granted" {
            permissionManager.request(type: "microphone") { [weak self] newStatus in
                guard let self = self else { return }
                if newStatus == "granted" {
                    self.startRecordingInternal(id: id)
                } else {
                    self.sendError(id: id, message: "Microphone permission denied")
                }
            }
            return
        }
        startRecordingInternal(id: id)
    }

    private func startRecordingInternal(id: String) {
        do {
            try audioRecorder.start()
            sendSuccess(id: id, data: NSNull())
        } catch {
            sendError(id: id, message: error.localizedDescription)
        }
    }

    private func handleStopRecording(id: String) {
        audioRecorder.stop { [weak self] result in
            guard let self = self else { return }
            switch result {
            case .success(let audioResult):
                self.sendSuccess(id: id, data: [
                    "base64": audioResult.base64,
                    "mimeType": audioResult.mimeType,
                    "duration": audioResult.duration,
                ])
            case .failure(let error):
                self.sendError(id: id, message: error.localizedDescription)
            }
        }
    }

    private func handleSendFeedback(id: String, payload: Any?) {
        guard let dict = payload as? [String: Any],
              let vc = presentingVC else {
            sendError(id: id, message: "Invalid feedback payload")
            return
        }

        mailComposer.send(from: vc.{{APP_NAME_LOWER}}TopMost, payload: dict) { [weak self] success in
            self?.sendSuccess(id: id, data: ["success": success])
        }
    }

    private func handleShareText(id: String, payload: Any?) {
        guard let dict = payload as? [String: Any],
              let text = dict["text"] as? String,
              let filename = dict["filename"] as? String,
              let vc = presentingVC else {
            sendError(id: id, message: "Invalid share payload")
            return
        }

        let url = FileManager.default.temporaryDirectory.appendingPathComponent(filename)
        do {
            try text.write(to: url, atomically: true, encoding: .utf8)
            let activity = UIActivityViewController(activityItems: [url], applicationActivities: nil)
            if let popover = activity.popoverPresentationController {
                popover.sourceView = vc.view
                popover.sourceRect = CGRect(x: vc.view.bounds.midX, y: vc.view.bounds.midY, width: 0, height: 0)
            }
            DispatchQueue.main.async { [weak self] in
                vc.{{APP_NAME_LOWER}}TopMost.present(activity, animated: true) {
                    self?.sendSuccess(id: id, data: ["success": true])
                }
            }
        } catch {
            sendError(id: id, message: error.localizedDescription)
        }
    }

    private func handleGetProducts(id: String) {
        Task { @MainActor [weak self] in
            guard let self = self else { return }
            do {
                let products = try await self.iapManager.fetchProducts()
                self.sendSuccess(id: id, data: products)
            } catch let error as IAPError {
                self.sendBridgeError(id: id, code: error.errorCode, message: error.localizedDescription ?? "IAP error")
            } catch {
                self.sendBridgeError(id: id, code: "UNKNOWN", message: error.localizedDescription)
            }
        }
    }

    private func handleMediaServe(id: String, payload: Any?) {
        guard let dict = payload as? [String: Any],
              let path = dict["path"] as? String, !path.isEmpty else {
            sendError(id: id, message: "Invalid media path")
            return
        }
        let url = "\({{APP_NAME}}ShellConfig.assetScheme)://local/\(path)"
        sendSuccess(id: id, data: ["url": url])
    }

    private func handleEnsureSeedAssets(id: String) {
        {{APP_NAME}}SeedAssets.ensureCopied()
        sendSuccess(id: id, data: ["ok": true])
    }

    private func handlePurchase(id: String, payload: Any?) {
        guard let dict = payload as? [String: Any],
              let productId = dict["productId"] as? String else {
            sendError(id: id, message: "Invalid purchase payload")
            return
        }

        Task { @MainActor [weak self] in
            guard let self = self else { return }
            do {
                let result = try await self.iapManager.purchase(productId: productId)
                self.sendSuccess(id: id, data: [
                    "productId": result.productId,
                    "transactionId": result.transactionId,
                ])
            } catch let error as IAPError {
                self.sendBridgeError(id: id, code: error.errorCode, message: error.localizedDescription ?? "Purchase failed")
            } catch {
                self.sendBridgeError(id: id, code: "UNKNOWN", message: error.localizedDescription)
            }
        }
    }

    private func sendSuccess(id: String, data: Any) {
        let json = jsonString(from: ["id": id, "data": data])
        let script = "window.{{APP_NAME_LOWER}}BridgeCallback('\(id)', \(json));"
        DispatchQueue.main.async { [weak self] in
            self?.webView?.evaluateJavaScript(script)
        }
    }

    private func sendBridgeError(id: String, code: String, message: String) {
        let json = jsonString(from: [
            "id": id,
            "error": [
                "code": code,
                "message": message,
            ],
        ])
        let script = "window.{{APP_NAME_LOWER}}BridgeCallback('\(id)', \(json));"
        DispatchQueue.main.async { [weak self] in
            self?.webView?.evaluateJavaScript(script)
        }
    }

    private func sendError(id: String, message: String) {
        let escaped = message.replacingOccurrences(of: "'", with: "\\'")
        let script = "window.{{APP_NAME_LOWER}}BridgeCallback('\(id)', { error: '\(escaped)' });"
        DispatchQueue.main.async { [weak self] in
            self?.webView?.evaluateJavaScript(script)
        }
    }

    private func jsonString(from object: Any) -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: object, options: []),
              let str = String(data: data, encoding: .utf8) else {
            return "null"
        }
        return str
    }
}
