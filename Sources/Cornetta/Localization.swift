import CornettaCore
import SwiftUI

/// The selected interface language shared by SwiftUI and AppKit code.
@MainActor
final class Localization: ObservableObject {
    static let shared = Localization()

    @Published private(set) var language: AppLanguage
    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard,
         preferredLanguages: [String] = Locale.preferredLanguages,
         existingInstall: Bool? = nil) {
        self.defaults = defaults
        let legacyKeys = ["welcomeDone", "telemetryInstallID", "telemetryLastVersion", "showOverlay",
                          "proposeOnCall", "screenMicrophone", "screenSystemAudio", "feedbackName", "feedbackEmail"]
        let legacy = existingInstall ?? legacyKeys.contains { defaults.object(forKey: $0) != nil }
        language = AppLanguage.initial(defaults: defaults, preferredLanguages: preferredLanguages,
                                       existingInstall: legacy)
    }

    var locale: Locale { language.locale }

    func select(_ selected: AppLanguage) {
        guard selected != language else { return }
        language = selected
        defaults.set(selected.rawValue, forKey: AppLanguage.storageKey)
        NotificationCenter.default.post(name: .cornettaLanguageChanged, object: nil)
    }

    func text(_ key: L10nKey) -> String {
        L10n.text(key, language: language)
    }

    func format(_ key: L10nKey, _ arguments: String...) -> String {
        L10n.format(key, language: language, arguments)
    }
}

extension Notification.Name {
    static let cornettaLanguageChanged = Notification.Name("CornettaLanguageChanged")
}

/// Localized string for AppKit and model code outside a SwiftUI environment.
@MainActor
func tr(_ key: L10nKey) -> String {
    Localization.shared.text(key)
}

@MainActor
func tr(_ key: L10nKey, _ arguments: String...) -> String {
    L10n.format(key, language: Localization.shared.language, arguments: arguments)
}

private struct AppLanguageEnvironmentKey: EnvironmentKey {
    static let defaultValue = AppLanguage.italian
}

extension EnvironmentValues {
    var appLanguage: AppLanguage {
        get { self[AppLanguageEnvironmentKey.self] }
        set { self[AppLanguageEnvironmentKey.self] = newValue }
    }
}

private struct LocalizedRootModifier: ViewModifier {
    @ObservedObject private var localization = Localization.shared

    func body(content: Content) -> some View {
        content
            .environment(\.locale, localization.locale)
            .environment(\.appLanguage, localization.language)
    }
}

extension View {
    /// Makes SwiftUI localization react immediately when the saved language changes.
    func localizedRoot() -> some View {
        modifier(LocalizedRootModifier())
    }
}
