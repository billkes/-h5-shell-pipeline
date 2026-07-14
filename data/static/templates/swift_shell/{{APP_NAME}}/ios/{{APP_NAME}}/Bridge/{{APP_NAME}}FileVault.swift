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
        let trimmed = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        let filename = (trimmed as NSString).lastPathComponent
        guard !filename.isEmpty else { return nil }
        if let data = data(forBundledFilename: filename) {
            return data
        }
        if trimmed != filename, let data = data(forBundledFilename: trimmed) {
            return data
        }
        return nil
    }

    static func data(forBundledFilename filename: String) -> Data? {
        let base = (filename as NSString).deletingPathExtension
        let ext = (filename as NSString).pathExtension
        guard !base.isEmpty, !ext.isEmpty else { return nil }

        let parent = (filename as NSString).deletingLastPathComponent
        // Scaffold: "SeedBundle" is fixed (编组 I); do not rename to {prefix}_*.
        var subdirs: [String?] = ["SeedBundle", "assets/img"]
        if !parent.isEmpty, parent != "." {
            subdirs.insert(parent, at: 0)
        }
        subdirs.append(nil)

        for directory in subdirs {
            if let directory {
                if let url = Bundle.main.url(forResource: base, withExtension: ext, subdirectory: directory),
                   let data = try? Data(contentsOf: url) {
                    return data
                }
            } else if let url = Bundle.main.url(forResource: base, withExtension: ext),
                      let data = try? Data(contentsOf: url) {
                return data
            }
        }

        guard let resourceURL = Bundle.main.resourceURL else { return nil }
        let leaf = (filename as NSString).lastPathComponent
        let candidates = [
            resourceURL.appendingPathComponent(filename),
            resourceURL.appendingPathComponent("SeedBundle").appendingPathComponent(leaf),
            resourceURL.appendingPathComponent("assets/img").appendingPathComponent(leaf),
            resourceURL.appendingPathComponent(leaf),
        ]
        for url in candidates {
            if FileManager.default.fileExists(atPath: url.path),
               let data = try? Data(contentsOf: url) {
                return data
            }
        }
        return nil
    }
}
