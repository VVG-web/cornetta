import AppKit

/// Il feedback non passa più da un server: apre una segnalazione pubblica nel repository fork.
/// L'app non manda niente da sola. GitHub vede la richiesta solo quando l'utente apre la pagina.
enum FeedbackLink {
    static func open() {
        var components = URLComponents(url: AppInfo.newIssueURL, resolvingAgainstBaseURL: false)
        components?.queryItems = [
            URLQueryItem(name: "title", value: "Cornetta \(AppInfo.version): ")
        ]
        if let url = components?.url {
            NSWorkspace.shared.open(url)
        }
    }
}
