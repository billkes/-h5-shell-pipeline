import UIKit

struct ImageResult {
    let path: String
}

final class ImagePickerCoordinator: NSObject {
    private var completion: ((Result<ImageResult, Error>) -> Void)?

    func present(from vc: UIViewController, useCamera: Bool, completion: @escaping (Result<ImageResult, Error>) -> Void) {
        self.completion = completion

        let source: UIImagePickerController.SourceType = useCamera ? .camera : .photoLibrary
        guard UIImagePickerController.isSourceTypeAvailable(source) else {
            let message = useCamera ? "Camera not available" : "Photo library not available"
            completion(.failure(NSError(domain: "{{APP_NAME}}", code: 1, userInfo: [NSLocalizedDescriptionKey: message])))
            return
        }
        let picker = UIImagePickerController()
        picker.sourceType = source
        picker.delegate = self
        picker.allowsEditing = false
        if useCamera {
            picker.cameraCaptureMode = .photo
        }
        vc.present(picker, animated: true)
    }

    private func finish(with result: Result<ImageResult, Error>) {
        completion?(result)
        completion = nil
    }

    private func processImage(_ image: UIImage) {
        guard let data = image.jpegData(compressionQuality: 0.8) else {
            finish(with: .failure(NSError(domain: "{{APP_NAME}}", code: 2, userInfo: [NSLocalizedDescriptionKey: "Failed to process image"])))
            return
        }
        let rel = "photos/item_\(Int(Date().timeIntervalSince1970)).jpg"
        do {
            let path = try {{APP_NAME}}FileVault.writeData(rel, data: data)
            finish(with: .success(ImageResult(path: path)))
        } catch {
            finish(with: .failure(error))
        }
    }
}

extension ImagePickerCoordinator: UIImagePickerControllerDelegate, UINavigationControllerDelegate {
    func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
        picker.dismiss(animated: true)
        if let image = info[.originalImage] as? UIImage {
            processImage(image)
        } else {
            finish(with: .failure(NSError(domain: "{{APP_NAME}}", code: 3, userInfo: [NSLocalizedDescriptionKey: "No image captured"])))
        }
    }

    func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
        picker.dismiss(animated: true)
        finish(with: .failure(NSError(domain: "{{APP_NAME}}", code: 4, userInfo: [NSLocalizedDescriptionKey: "Cancelled"])))
    }
}
