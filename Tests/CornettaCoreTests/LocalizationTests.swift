import Foundation
import Testing
@testable import CornettaCore

struct LocalizationTests {
    private func defaults() -> UserDefaults {
        let suite = "cornetta-localization-\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defaults.removePersistentDomain(forName: suite)
        return defaults
    }

    @Test func englishSystemLanguageSelectsEnglishForANewInstall() {
        let store = defaults()
        let language = AppLanguage.initial(defaults: store, preferredLanguages: ["en-GB", "it-IT"],
                                           existingInstall: false)
        #expect(language == .english)
        #expect(store.string(forKey: AppLanguage.storageKey) == "en")
    }

    @Test func otherSystemLanguagesFallBackToItalian() {
        let store = defaults()
        let language = AppLanguage.initial(defaults: store, preferredLanguages: ["de-DE", "en-US"],
                                           existingInstall: false)
        #expect(language == .italian)
    }

    @Test func existingInstallWithoutAChoiceStaysItalian() {
        let store = defaults()
        let language = AppLanguage.initial(defaults: store, preferredLanguages: ["en-US"],
                                           existingInstall: true)
        #expect(language == .italian)
        #expect(store.string(forKey: AppLanguage.storageKey) == "it")
    }

    @Test func explicitChoiceWinsOverSystemAndLegacyState() {
        let store = defaults()
        store.set("en", forKey: AppLanguage.storageKey)
        let language = AppLanguage.initial(defaults: store, preferredLanguages: ["it-IT"],
                                           existingInstall: true)
        #expect(language == .english)
    }

    @Test func invalidSavedValueFallsBackAndIsReplaced() {
        let store = defaults()
        store.set("de", forKey: AppLanguage.storageKey)
        let language = AppLanguage.initial(defaults: store, preferredLanguages: ["en-US"],
                                           existingInstall: false)
        #expect(language == .english)
        #expect(store.string(forKey: AppLanguage.storageKey) == "en")
    }

    @Test func everyCatalogKeyHasBothTranslations() {
        for key in L10nKey.allCases {
            for language in AppLanguage.allCases {
                #expect(!L10n.text(key, language: language).isEmpty)
            }
        }
    }

    @Test func placeholdersFormatAndKeepLiteralPercentSigns() {
        #expect(L10n.format(.libraryStatusTranscribing, language: .italian, "42") == "Trascrivo 42%")
        #expect(L10n.format(.libraryStatusTranscribing, language: .english, "42") == "Transcribing 42%")
        #expect(L10n.format(.noticeUpdateMessage, language: .english, "0.5.0")
                == "Cornetta 0.5.0 is ready. Installing takes a few seconds and the app reopens automatically.")
    }
}
