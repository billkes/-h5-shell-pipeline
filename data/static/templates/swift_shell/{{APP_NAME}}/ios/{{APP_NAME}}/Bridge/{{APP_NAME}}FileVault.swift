import Foundation

enum {{APP_NAME}}FileVault {
    static var root: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    }

    static func resolve(_ rel: String) throws -> URL {
        let cleaned = rel.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        var url = root
        for component in cleaned.split(separator: "/") where !component.isEmpty {
            url = url.appendingPathComponent(String(component), isDirectory: false)
        }
        let rootPath = root.standardizedFileURL.path
        guard url.standardizedFileURL.path.hasPrefix(rootPath) else {
            throw NSError(domain: "{{APP_NAME}}FileVault", code: 403)
        }
        return url
    }

    static func readData(_ rel: String) throws -> Data {
        try Data(contentsOf: try resolve(rel))
    }

    @discardableResult
    static func writeData(_ rel: String, data: Data) throws -> String {
        let url = try resolve(rel)
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try data.write(to: url)
        return rel.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
    }
}

enum {{APP_NAME}}BundleMedia {
    static func data(forRelativePath path: String) -> Data? {
        let filename = (path as NSString).lastPathComponent
        let base = (filename as NSString).deletingPathExtension
        let ext = (filename as NSString).pathExtension
        guard !base.isEmpty, !ext.isEmpty else { return nil }

        let directories: [String?] = ["SeedBundle", nil]
        for directory in directories {
            if let directory {
                if let bundlePath = Bundle.main.path(forResource: base, ofType: ext, inDirectory: directory),
                   let data = try? Data(contentsOf: URL(fileURLWithPath: bundlePath)) {
                    return data
                }
                if let url = Bundle.main.url(forResource: base, withExtension: ext, subdirectory: directory),
                   let data = try? Data(contentsOf: url) {
                    return data
                }
            } else if let bundlePath = Bundle.main.path(forResource: base, ofType: ext),
                      let data = try? Data(contentsOf: URL(fileURLWithPath: bundlePath)) {
                return data
            }
        }
        return nil
    }
}
