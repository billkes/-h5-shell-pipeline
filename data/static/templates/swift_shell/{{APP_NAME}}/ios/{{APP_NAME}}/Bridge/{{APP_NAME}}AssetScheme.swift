import Foundation
import WebKit

final class {{APP_NAME}}AssetScheme: NSObject, WKURLSchemeHandler {
    func webView(_ webView: WKWebView, start urlSchemeTask: WKURLSchemeTask) {
        guard let url = urlSchemeTask.request.url else {
            urlSchemeTask.didFailWithError(NSError(domain: "{{APP_NAME}}Asset", code: 400))
            return
        }
        let path = relativePath(for: url)

        func finish(with data: Data, mime: String) {
            DispatchQueue.main.async {
                self.respond(task: urlSchemeTask, data: data, mime: mime)
            }
        }

        if let fileURL = try? {{APP_NAME}}FileVault.resolve(path),
           FileManager.default.fileExists(atPath: fileURL.path),
           let data = try? Data(contentsOf: fileURL) {
            finish(with: data, mime: mime(for: path))
            return
        }

        if let data = {{APP_NAME}}BundleMedia.data(forRelativePath: path) {
            finish(with: data, mime: mime(for: path))
            return
        }

        DispatchQueue.main.async {
            urlSchemeTask.didFailWithError(
                NSError(domain: "{{APP_NAME}}Asset", code: 404, userInfo: [NSLocalizedDescriptionKey: path])
            )
        }
    }

    func webView(_ webView: WKWebView, stop urlSchemeTask: WKURLSchemeTask) {}

    private func respond(task: WKURLSchemeTask, data: Data, mime: String) {
        guard let url = task.request.url else { return }
        let headers = [
            "Content-Type": mime,
            "Content-Length": "\(data.count)",
            "Cache-Control": "no-store",
        ]
        guard let response = HTTPURLResponse(
            url: url,
            statusCode: 200,
            httpVersion: "HTTP/1.1",
            headerFields: headers
        ) else {
            task.didFailWithError(NSError(domain: "{{APP_NAME}}Asset", code: 500))
            return
        }
        task.didReceive(response)
        task.didReceive(data)
        task.didFinish()
    }

    private func mime(for path: String) -> String {
        let ext = (path as NSString).pathExtension.lowercased()
        switch ext {
        case "png": return "image/png"
        case "jpg", "jpeg": return "image/jpeg"
        case "m4a", "mp4", "aac": return "audio/mp4"
        case "js": return "application/javascript"
        case "css": return "text/css"
        case "html", "htm": return "text/html"
        default: return "application/octet-stream"
        }
    }

    private func relativePath(for url: URL) -> String {
        var path = url.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        if path.isEmpty, let host = url.host, !host.isEmpty, host != "local" {
            path = host
        }
        if path.hasPrefix("local/") {
            path = String(path.dropFirst(6))
        } else if path == "local" {
            path = ""
        }
        if let q = path.firstIndex(of: "?") {
            path = String(path[..<q])
        }
        if path.isEmpty, let host = url.host, host != "local", host.contains(".") || host.contains("/") {
            path = host
        }
        return path
    }
}
