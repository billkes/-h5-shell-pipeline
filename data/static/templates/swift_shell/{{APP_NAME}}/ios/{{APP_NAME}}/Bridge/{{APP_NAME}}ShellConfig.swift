import Foundation

enum {{APP_NAME}}ShellConfig {
    static let assetScheme = "{{ASSET_SCHEME}}"
    /// Vite dev entry — hardcoded in native shell; run `h5-post --sync-dev-url` to refresh LAN IP.
    static let h5EntryUrl = "{{H5_ENTRY_URL}}"
}
