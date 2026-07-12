import Foundation

enum {{APP_NAME}}SeedAssets {
    private static let seedFilenames: [String] = []

    /// Copy bundled seed photos into Documents/photos/seed/ (idempotent).
    static func ensureCopied() {
        for filename in seedFilenames {
            let rel = "photos/seed/\(filename)"
            if let url = try? {{APP_NAME}}FileVault.resolve(rel), FileManager.default.fileExists(atPath: url.path) {
                continue
            }
            guard let data = {{APP_NAME}}BundleMedia.data(forRelativePath: rel) else {
                continue
            }
            try? {{APP_NAME}}FileVault.writeData(rel, data: data)
        }
    }
}
