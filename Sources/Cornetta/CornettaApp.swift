import AppKit
import CornettaCore
import SwiftUI

struct CornettaApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    @StateObject private var model = RecorderModel.shared
    @StateObject private var updates = UpdateManager.shared
    @StateObject private var screen = ScreenRecordingModel.shared
    @StateObject private var localization = Localization.shared

    var body: some Scene {
        MenuBarExtra {
            MenuContent(model: model, updates: updates, screen: screen)
                .localizedRoot()
        } label: {
            if model.isRecording {
                Image(nsImage: Self.recordingIcon)
                Text(model.elapsedText)
            } else if screen.isRecording {
                Image(nsImage: Self.recordingIcon)
                Text(screen.elapsedText)
            } else {
                Image(systemName: "phone")
            }
        }
    }

    /// Pallino rosso non template: il rosso resta visibile nella barra dei menu.
    @MainActor
    private static var recordingIcon: NSImage {
        coloredSymbol("record.circle.fill", .systemRed, tr(.accessibilityRecording))
    }

    private static func coloredSymbol(_ name: String, _ color: NSColor, _ label: String) -> NSImage {
        let config = NSImage.SymbolConfiguration(paletteColors: [color])
        let image = NSImage(systemSymbolName: name, accessibilityDescription: label)?.withSymbolConfiguration(config) ?? NSImage()
        image.isTemplate = false
        return image
    }
}

struct MenuContent: View {
    @ObservedObject var model: RecorderModel
    @ObservedObject var updates: UpdateManager
    @ObservedObject var screen: ScreenRecordingModel
    @ObservedObject private var localization = Localization.shared

    var body: some View {
        Button(localization.text(model.isRecording ? .menuRecordStop : .menuRecordStart)) { model.toggle() }
            .keyboardShortcut("r")
        if model.isRecording {
            Text(localization.format(.menuRecordStatus, model.elapsedText))
            Text(localization.format(.menuMicrophone,
                                     model.microphoneName ?? localization.text(.commonNone)))
        }
        if let message = model.message {
            Text(message)
        }
        if model.microphoneDenied {
            Button(localization.text(.menuMicrophoneSettings)) { model.openMicrophoneSettings() }
        }
        Button(localization.text(screen.isRecording ? .menuScreenStop : .menuScreenStart)) { screen.toggle() }
            .disabled(screen.isPicking)
        if screen.isRecording {
            Text(localization.format(.menuScreenStatus, screen.elapsedText))
            if screen.withoutMicrophone {
                Text(localization.text(.menuScreenWithoutMicrophone))
            }
        }
        Divider()
        Button("Registrazioni e trascrizioni…") { LibraryWindow.show() }
            .keyboardShortcut("t")
        Button("Apri cartella registrazioni") { model.openFolder() }
        Menu("Video dello schermo") {
            Toggle("Registra anche il microfono", isOn: $screen.includeMicrophone)
                .disabled(!ScreenRecorder.supportsMicrophone)
            Toggle("Registra anche l'audio del Mac", isOn: $screen.includeSystemAudio)
            Toggle("Mostra il pannello durante il video", isOn: $screen.showOverlay)
            Divider()
            Button("Apri cartella video") { screen.openFolder() }
        }
        if model.lastFile != nil {
            Button("Mostra l'ultima registrazione") { model.revealLastFile() }
        }
        Divider()
        Button(localization.text(.menuFeedback)) { model.openFeedback() }
        Toggle("Mostra il pannello durante la registrazione", isOn: $model.showOverlay)
        Toggle("Proponi di registrare quando inizia una chiamata", isOn: $model.proposeOnCall)
        if SpeechEngine.isAvailable {
            Toggle("Trascrivi ogni chiamata sul Mac", isOn: Library.shared.$autoTranscribe)
        }
        Toggle("Apri all'accensione del Mac", isOn: Binding(get: { LaunchAtLogin.isEnabled }, set: { LaunchAtLogin.set($0) }))
        Button(localization.text(.menuUpdates)) { model.checkForUpdates() }
            .disabled(updates.isChecking)
        Divider()
        Text(verbatim: "Cornetta \(AppInfo.version)")
        Picker(localization.text(.menuLanguage),
               selection: Binding(get: { localization.language }, set: { localization.select($0) })) {
            ForEach(AppLanguage.allCases, id: \.self) { language in
                Text(localization.text(language.nameKey)).tag(language)
            }
        }
        Divider()
        // Ferma e salva lo fa applicationShouldTerminate, senza convertire: la conversione la uccide l'uscita.
        Button("Esci da Cornetta") { NSApp.terminate(nil) }
        .keyboardShortcut("q")
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        Diagnostics.log("Avvio Cornetta \(AppInfo.version) da \(Bundle.main.bundlePath)")
        MainActor.assumeIsolated {
            if let index = CommandLine.arguments.firstIndex(of: "--demo-library"), index + 1 < CommandLine.arguments.count {
                let root = URL(fileURLWithPath: CommandLine.arguments[index + 1], isDirectory: true)
                Library.shared.useDemoFolders(recordings: root.appendingPathComponent("Registrazioni"),
                                              support: root.appendingPathComponent("Supporto"))
                // Dopo l'avvio di SwiftUI: aperta prima, la finestra non arriva sullo schermo.
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { LibraryWindow.show() }
                return
            }
            if CommandLine.arguments.contains("--demo") {
                RecorderModel.shared.showDemo()
                return
            }
            if Self.handOffToRunningInstance() { return }
            if AppMover.offerMoveIfNeeded() { return }
            _ = RecorderModel.shared
            Library.shared.reload()
            Library.shared.resumePendingTranscriptions()
            Library.shared.recoverInterruptedRecordings(
                onRecovered: { RecorderModel.shared.noteRecovered($0) },
                onRecoveryFailed: { RecorderModel.shared.noteRecoveryFailed($0) })
            if WelcomeWindow.shouldShow {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { WelcomeWindow.show() }
            }
        }
    }

    /// Doppio clic sull'app già aperta: mostra la finestra Registrazioni invece di non fare niente.
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        MainActor.assumeIsolated { LibraryWindow.show() }
        return true
    }

    /// Una sola Cornetta per volta. Restano fuori le copie sul disco di installazione, che devono poter
    /// proporre lo spostamento in Applicazioni, sia come nuova istanza sia come istanza già aperta: con loro
    /// due Cornette girano insieme, e la registrazione viva dell'altra la protegge il lock della cartella
    /// di lavoro (`WorkingFolderLock`), che il recupero salta.
    @MainActor private static func handOffToRunningInstance() -> Bool {
        guard !AppMover.isInstallerCopy(Bundle.main.bundlePath), let other = AppMover.otherInstances().first else { return false }
        Diagnostics.log("Cornetta è già aperta (pid \(other.processIdentifier)): chiudo questa copia")
        // Riaprire l'altra copia le fa mostrare la finestra Registrazioni (applicationShouldHandleReopen).
        if let url = other.bundleURL, url != Bundle.main.bundleURL {
            NSWorkspace.shared.openApplication(at: url, configuration: NSWorkspace.OpenConfiguration())
        }
        NSApp.terminate(nil)
        return true
    }

    /// Esci, aggiornamento, spegnimento: una registrazione in corso chiude i file (la converte il prossimo
    /// avvio). Una conversione già partita si aspetta fino a 60 s: interrotta, al riavvio diventa un doppione.
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        MainActor.assumeIsolated {
            let model = RecorderModel.shared
            let screen = ScreenRecordingModel.shared
            model.stopForTermination()
            guard model.hasUnsavedWork || screen.hasUnsavedWork else { return .terminateNow }
            Diagnostics.log("Uscita rimandata: finisco di salvare la registrazione o il video")
            // Il video si chiude in pochi secondi; poi si aspetta la conversione della chiamata, se c'è.
            screen.stopAndWait(timeout: 10) {
                model.whenSaved(timeout: 60) { NSApp.reply(toApplicationShouldTerminate: true) }
            }
            return .terminateLater
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        // Chiude il file anche se l'app esce durante una registrazione.
        MainActor.assumeIsolated { RecorderModel.shared.stopForTermination() }
    }
}
