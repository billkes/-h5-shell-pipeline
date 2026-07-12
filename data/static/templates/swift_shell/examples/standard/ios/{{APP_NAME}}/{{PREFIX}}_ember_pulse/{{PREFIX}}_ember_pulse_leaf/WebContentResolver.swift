import Foundation

enum WebContentResolver {
    static func resolve() -> WebContentSource? {
        guard let url = URL(string: {{APP_NAME}}ShellConfig.h5EntryUrl) else {
            return nil
        }
        print("[{{APP_NAME}}] Loading remote H5: \(url.absoluteString)")
        return .remote(url)
    }
}
