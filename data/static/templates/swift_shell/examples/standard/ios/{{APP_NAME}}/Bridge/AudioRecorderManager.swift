import AVFoundation
import Foundation

struct AudioResult {
    let base64: String
    let mimeType: String
    let duration: Double
}

final class AudioRecorderManager {
    private var recorder: AVAudioRecorder?
    private var fileURL: URL?
    private var startTime: Date?

    func start() throws {
        let session = AVAudioSession.sharedInstance()
        switch session.recordPermission {
        case .denied:
            throw NSError(
                domain: "{{APP_NAME}}",
                code: 12,
                userInfo: [NSLocalizedDescriptionKey: "Microphone permission denied"]
            )
        case .undetermined:
            break
        case .granted:
            break
        @unknown default:
            break
        }

        try session.setCategory(
            .playAndRecord,
            mode: .default,
            options: [.defaultToSpeaker, .allowBluetooth]
        )
        try session.setActive(true)

        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("{{APP_NAME_LOWER}}_recording_\(Date().timeIntervalSince1970).m4a")
        fileURL = url

        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
        ]

        recorder = try AVAudioRecorder(url: url, settings: settings)
        recorder?.prepareToRecord()
        recorder?.record()
        startTime = Date()
    }

    func stop(completion: @escaping (Result<AudioResult, Error>) -> Void) {
        guard let recorder = recorder, let url = fileURL else {
            completion(.failure(NSError(
                domain: "{{APP_NAME}}",
                code: 10,
                userInfo: [NSLocalizedDescriptionKey: "No active recording"]
            )))
            return
        }

        let duration = Date().timeIntervalSince(startTime ?? Date())
        recorder.stop()

        do {
            let data = try Data(contentsOf: url)
            guard data.count >= 256 else {
                throw NSError(
                    domain: "{{APP_NAME}}",
                    code: 11,
                    userInfo: [NSLocalizedDescriptionKey: "Recording too short — hold Stop after speaking."]
                )
            }
            let base64 = data.base64EncodedString()
            try? FileManager.default.removeItem(at: url)
            self.recorder = nil
            self.fileURL = nil
            try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
            completion(.success(AudioResult(base64: base64, mimeType: "audio/mp4", duration: duration)))
        } catch {
            completion(.failure(error))
        }
    }
}
