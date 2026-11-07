import Combine
import Foundation
import CornettaCore

/// Esito di un controllo manuale degli aggiornamenti.
enum UpdateCheckResult {
    case upToDate(current: String)
    case available(version: String, url: URL)
    case failed
}

private struct GitHubRelease: Decodable {
    let tagName: String
    let htmlURL: URL

    enum CodingKeys: String, CodingKey {
        case tagName = "tag_name"
        case htmlURL = "html_url"
    }
}

/// Controllo manuale delle release su GitHub. Non parte niente all'avvio e non c'è nessun timer:
/// la richiesta esiste solo dopo «Controlla gli aggiornamenti…». Non scarica e non installa nulla.
@MainActor
final class UpdateManager: ObservableObject {
    static let shared = UpdateManager()

    @Published private(set) var isChecking = false
    private let session: URLSession

    private init() {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.httpShouldSetCookies = false
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.timeoutIntervalForRequest = 15
        configuration.timeoutIntervalForResource = 20
        session = URLSession(configuration: configuration)
    }

    func check() async -> UpdateCheckResult {
        guard !isChecking else { return .failed }
        isChecking = true
        defer { isChecking = false }

        var request = URLRequest(url: AppInfo.latestReleaseAPIURL)
        request.httpMethod = "GET"
        request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        request.setValue("Cornetta/\(AppInfo.version)", forHTTPHeaderField: "User-Agent")
        request.setValue("no-cache", forHTTPHeaderField: "Cache-Control")

        do {
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                Diagnostics.log("Controllo aggiornamenti: HTTP \((response as? HTTPURLResponse)?.statusCode ?? 0)")
                return .failed
            }
            let release = try JSONDecoder().decode(GitHubRelease.self, from: data)
            guard let version = ReleaseVersion.normalized(release.tagName) else {
                Diagnostics.log("Controllo aggiornamenti: tag non riconosciuto")
                return .failed
            }
            let current = AppInfo.version == "dev" ? "0.0.0" : AppInfo.version
            if ReleaseVersion.isNewer(release.tagName, than: current) {
                Diagnostics.log("Aggiornamento disponibile su GitHub: \(version)")
                return .available(version: version, url: safeReleaseURL(release.htmlURL) ?? AppInfo.latestReleaseURL)
            }
            return .upToDate(current: AppInfo.version)
        } catch {
            Diagnostics.log("Controllo aggiornamenti non riuscito: \(error.localizedDescription)")
            return .failed
        }
    }

    /// L'URL apre solo una release del repository fork: il resto non viene mai passato al browser.
    private func safeReleaseURL(_ url: URL) -> URL? {
        guard url.scheme == "https", url.host == "github.com",
              url.path.hasPrefix("/\(AppInfo.githubRepository)/releases/") else { return nil }
        return url
    }
}
