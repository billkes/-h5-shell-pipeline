import MessageUI
import UIKit

final class FeedbackMailComposer: NSObject {
    func send(from vc: UIViewController, payload: [String: Any], completion: @escaping (Bool) -> Void) {
        DispatchQueue.main.async { [weak self] in
            guard let self = self else {
                completion(false)
                return
            }

            if MFMailComposeViewController.canSendMail() {
                self.presentMail(from: vc, payload: payload, completion: completion)
            } else {
                self.shareFallback(from: vc, payload: payload, completion: completion)
            }
        }
    }

    private func presentMail(
        from vc: UIViewController,
        payload: [String: Any],
        completion: @escaping (Bool) -> Void
    ) {
        let mail = MFMailComposeViewController()
        mail.mailComposeDelegate = self

        let type = payload["type"] as? String ?? "general"
        mail.setToRecipients(["support@{{APP_NAME_LOWER}}.app"])
        mail.setSubject("[{{APP_NAME}} Feedback] \(type.capitalized)")

        var body = payload["description"] as? String ?? ""
        if let email = payload["email"] as? String, !email.isEmpty {
            body += "\n\nContact Email: \(email)"
        }
        mail.setMessageBody(body, isHTML: false)

        if let attachments = payload["attachments"] as? [[String: Any]] {
            for (index, att) in attachments.enumerated() {
                guard let base64 = att["data"] as? String,
                      let data = Data(base64Encoded: base64) else { continue }
                let mimeType = att["mimeType"] as? String ?? "application/octet-stream"
                let name = att["name"] as? String ?? "attachment_\(index)"
                mail.addAttachmentData(data, mimeType: mimeType, fileName: name)
            }
        }

        vc.present(mail, animated: true) {
            completion(true)
        }
    }

    private func shareFallback(
        from vc: UIViewController,
        payload: [String: Any],
        completion: @escaping (Bool) -> Void
    ) {
        let type = payload["type"] as? String ?? "general"
        let description = payload["description"] as? String ?? ""
        let email = payload["email"] as? String ?? "N/A"
        let text = "[{{APP_NAME}} Feedback - \(type)]\n\n\(description)\n\nEmail: \(email)"

        let activity = UIActivityViewController(activityItems: [text], applicationActivities: nil)
        if let popover = activity.popoverPresentationController {
            popover.sourceView = vc.view
            popover.sourceRect = CGRect(x: vc.view.bounds.midX, y: vc.view.bounds.midY, width: 0, height: 0)
        }

        vc.present(activity, animated: true) {
            completion(true)
        }
    }
}

extension FeedbackMailComposer: MFMailComposeViewControllerDelegate {
    func mailComposeController(
        _ controller: MFMailComposeViewController,
        didFinishWith result: MFMailComposeResult,
        error: Error?
    ) {
        controller.dismiss(animated: true)
    }
}
