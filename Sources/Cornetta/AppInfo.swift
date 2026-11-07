import Foundation

enum AppInfo {
    static var version: String { Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "dev" }
    static var build: String { Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "dev" }

    static let githubRepository = "VVG-web/cornetta-en"

    static var latestReleaseURL: URL {
        URL(string: "https://github.com/\(githubRepository)/releases/latest")!
    }

    static var latestReleaseAPIURL: URL {
        URL(string: "https://api.github.com/repos/\(githubRepository)/releases/latest")!
    }

    static var newIssueURL: URL {
        URL(string: "https://github.com/\(githubRepository)/issues/new")!
    }
}
