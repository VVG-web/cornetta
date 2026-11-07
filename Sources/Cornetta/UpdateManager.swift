import Combine
import Foundation
import CornettaCore

/// Esito di un controllo manuale degli aggiornamenti.
enum UpdateCheckResult {
    case upToDate(current: String)
    case available(version: String, url: URL)
    case failed
}

private struct SignedFeed: Decodable {
    let schema: Int
    let version: String
    let releaseURL: URL

    enum CodingKeys: String, CodingKey {
        case schema
        case version
        case releaseURL = "release_url"
    }
}

/// Controllo manuale del feed firmato ospitato su GitHub Pages. Non parte niente all'avvio
/// e non c'è nessun timer: la richiesta esiste solo dopo «Controlla gli aggiornamenti…».
/// La firma ECDSA P-256 viene verificata prima di leggere la versione. Non scarica e non installa nulla.
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

        do {
            let feedData = try await fetch(AppInfo.updateFeedURL, accept: "application/json")
            let signatureData = try await fetch(AppInfo.updateFeedSignatureURL, accept: "text/plain")
            guard let signature = String(data: signatureData, encoding: .utf8),
                  UpdateFeedSignature.verify(feed: feedData, signatureBase64: signature,
                                            publicKeyBase64: AppInfo.updateFeedPublicKey) else {
                Diagnostics.log("Controllo aggiornamenti: firma del feed non valida")
                return .failed
            }
            let feed = try JSONDecoder().decode(SignedFeed.self, from: feedData)
            guard feed.schema == 1,
                  let version = ReleaseVersion.normalized(feed.version),
                  let releaseURL = safeReleaseURL(feed.releaseURL) else {
                Diagnostics.log("Controllo aggiornamenti: feed non riconosciuto")
                return .failed
            }
            let current = AppInfo.version == "dev" ? "0.0.0" : AppInfo.version
            if ReleaseVersion.isNewer(feed.version, than: current) {
                Diagnostics.log("Aggiornamento disponibile nel feed firmato: \(version)")
                return .available(version: version, url: releaseURL)
            }
            return .upToDate(current: AppInfo.version)
        } catch {
            Diagnostics.log("Controllo aggiornamenti non riuscito: \(error.localizedDescription)")
            return .failed
        }
    }

    private func fetch(_ url: URL, accept: String) async throws -> Data {
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue(accept, forHTTPHeaderField: "Accept")
        request.setValue("Cornetta/\(AppInfo.version)", forHTTPHeaderField: "User-Agent")
        request.setValue("no-cache", forHTTPHeaderField: "Cache-Control")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw NSError(domain: "CornettaUpdate", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "HTTP \((response as? HTTPURLResponse)?.statusCode ?? 0)"])
        }
        return data
    }

    /// L'URL apre solo una release del repository fork: il resto non viene mai passato al browser.
    private func safeReleaseURL(_ url: URL) -> URL? {
        guard url.scheme == "https", url.host == "github.com",
              url.path.hasPrefix("/\(AppInfo.githubRepository)/releases/") else { return nil }
        return url
    }
}
