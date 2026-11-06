import Foundation

/// Languages supported by the Cornetta interface.
public enum AppLanguage: String, CaseIterable, Sendable {
    case italian = "it"
    case english = "en"

    public static let storageKey = "appLanguage"

    public var locale: Locale { Locale(identifier: rawValue) }

    public var nameKey: L10nKey {
        switch self {
        case .italian: return .menuLanguageItalian
        case .english: return .menuLanguageEnglish
        }
    }

    /// Italian unless English is the first supported system language.
    public static func systemDefault(preferredLanguages: [String] = Locale.preferredLanguages) -> AppLanguage {
        guard let primary = preferredLanguages.first?.lowercased() else { return .italian }
        return primary == "en" || primary.hasPrefix("en-") || primary.hasPrefix("en_") ? .english : .italian
    }

    /// Reads the saved choice. On first launch, legacy installs stay Italian and new installs follow
    /// the system once; the result is saved immediately so later system changes do not alter it.
    public static func initial(defaults: UserDefaults = .standard,
                               preferredLanguages: [String] = Locale.preferredLanguages,
                               existingInstall: Bool) -> AppLanguage {
        if let raw = defaults.string(forKey: storageKey), let saved = AppLanguage(rawValue: raw) {
            return saved
        }
        let selected: AppLanguage = existingInstall ? .italian : systemDefault(preferredLanguages: preferredLanguages)
        defaults.set(selected.rawValue, forKey: storageKey)
        return selected
    }
}
