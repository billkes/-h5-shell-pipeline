import AVFoundation
import Photos
import UIKit

final class PermissionManager {
    func status(for type: String) -> String {
        switch type {
        case "camera":
            return mapStatus(AVCaptureDevice.authorizationStatus(for: .video))
        case "photos":
            return mapPhotoStatus(PHPhotoLibrary.authorizationStatus(for: .readWrite))
        case "microphone":
            return mapRecordPermission(AVAudioSession.sharedInstance().recordPermission)
        default:
            return "notDetermined"
        }
    }

    func request(type: String, completion: @escaping (String) -> Void) {
        switch type {
        case "camera":
            AVCaptureDevice.requestAccess(for: .video) { granted in
                DispatchQueue.main.async {
                    completion(granted ? "granted" : "denied")
                }
            }
        case "photos":
            PHPhotoLibrary.requestAuthorization(for: .readWrite) { status in
                DispatchQueue.main.async {
                    completion(self.mapPhotoStatus(status))
                }
            }
        case "microphone":
            AVAudioSession.sharedInstance().requestRecordPermission { granted in
                DispatchQueue.main.async {
                    completion(granted ? "granted" : "denied")
                }
            }
        default:
            completion("denied")
        }
    }

    private func mapRecordPermission(_ permission: AVAudioSession.RecordPermission) -> String {
        switch permission {
        case .granted: return "granted"
        case .denied: return "denied"
        case .undetermined: return "notDetermined"
        @unknown default: return "notDetermined"
        }
    }

    private func mapStatus(_ status: AVAuthorizationStatus) -> String {
        switch status {
        case .authorized: return "granted"
        case .denied, .restricted: return "denied"
        case .notDetermined: return "notDetermined"
        @unknown default: return "notDetermined"
        }
    }

    private func mapPhotoStatus(_ status: PHAuthorizationStatus) -> String {
        switch status {
        case .authorized, .limited: return "granted"
        case .denied, .restricted: return "denied"
        case .notDetermined: return "notDetermined"
        @unknown default: return "notDetermined"
        }
    }
}
