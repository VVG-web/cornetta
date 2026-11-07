import Foundation

enum AppInfo {
    static var version: String { Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "dev" }
    static var build: String { Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "dev" }

    static let githubRepository = "VVG-web/cornetta-en"
    static let updateFeedURL = URL(string: "https://vvg-web.github.io/cornetta-en/update/feed.json")!
    static let updateFeedSignatureURL = URL(string: "https://vvg-web.github.io/cornetta-en/update/feed.json.sig")!
    static let updateFeedPublicKey = "BCcSn9flFlqQeVWQqoM9iFr8xKhtsy5juX9CJO70Or3aPgQVJyZOfnWeJTTYImxkxm9U20bgDWVqM5BO/NNvi60="

    static var latestReleaseURL: URL {
        URL(string: "https://github.com/\(githubRepository)/releases/latest")!
    }

    static var newIssueURL: URL {
        URL(string: "https://github.com/\(githubRepository)/issues/new")!
    }
}
