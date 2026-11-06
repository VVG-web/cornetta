import AppKit
import AVFoundation
import CornettaCore
import ServiceManagement
import SwiftUI

/// Avvio all'accensione del Mac (Impostazioni › Generali › Elementi login).
@MainActor
enum LaunchAtLogin {
    static var isEnabled: Bool { SMAppService.mainApp.status == .enabled }

    static func set(_ enabled: Bool) {
        do {
            if enabled { try SMAppService.mainApp.register() } else { try SMAppService.mainApp.unregister() }
            Diagnostics.log("Avvio all'accensione: \(enabled)")
        } catch {
            Diagnostics.log("Avvio all'accensione non impostato: \(error.localizedDescription)")
        }
    }
}

/// Finestra del primo avvio: dove trovare Cornetta e i due permessi, chiesti subito.
@MainActor
enum WelcomeWindow {
    private static var window: NSWindow?
    private static var languageObserver: NSObjectProtocol?

    static var shouldShow: Bool { !UserDefaults.standard.bool(forKey: "welcomeDone") }

    static func show() {
        if window == nil {
            let window = NSWindow(contentRect: .zero, styleMask: [.titled, .closable, .fullSizeContentView], backing: .buffered, defer: false)
            window.titlebarAppearsTransparent = true
            window.title = tr(.welcomeWindow)
            window.isReleasedWhenClosed = false
            window.contentView = NSHostingView(rootView: WelcomeView {
                UserDefaults.standard.set(true, forKey: "welcomeDone")
                WelcomeWindow.window?.close()
            }.localizedRoot())
            window.center()
            self.window = window
            if languageObserver == nil {
                languageObserver = NotificationCenter.default.addObserver(
                    forName: .cornettaLanguageChanged, object: nil, queue: .main
                ) { _ in
                    MainActor.assumeIsolated { WelcomeWindow.window?.title = tr(.welcomeWindow) }
                }
            }
        }
        NSApp.activate(ignoringOtherApps: true)
        window?.makeKeyAndOrderFront(nil)
    }
}

struct WelcomeView: View {
    let done: () -> Void
    @State private var micStatus = AVCaptureDevice.authorizationStatus(for: .audio)
    @State private var systemAudioAsked = UserDefaults.standard.bool(forKey: "systemAudioPrimed")
    @State private var askingSystemAudio = false
    @State private var launchAtLogin = true
    @Environment(\.appLanguage) private var language

    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            HStack(spacing: 16) {
                Image(nsImage: NSApp.applicationIconImage).resizable().frame(width: 64, height: 64)
                VStack(alignment: .leading, spacing: 4) {
                    Text("Cornetta è pronta").font(.title.weight(.bold))
                    Text("La trovi in alto a destra, nella barra dei menu: è l'icona della cornetta.")
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }

            VStack(alignment: .leading, spacing: 14) {
                Text("Due permessi, una volta sola").font(.headline)
                PermissionRow(number: 1, title: L10n.text(.welcomeMicrophone, language: language),
                              detail: L10n.text(.welcomeMicrophoneDetail, language: language),
                              granted: micStatus == .authorized, denied: micStatus == .denied || micStatus == .restricted,
                              action: L10n.text(.welcomeAllow, language: language)) {
                    Task {
                        _ = await CallRecorder.requestMicrophoneAccess()
                        micStatus = AVCaptureDevice.authorizationStatus(for: .audio)
                        if micStatus == .denied { openPrivacy("Privacy_Microphone") }
                    }
                }
                PermissionRow(number: 2, title: L10n.text(.welcomeCallAudio, language: language),
                              detail: L10n.text(.welcomeCallAudioDetail, language: language),
                              granted: systemAudioAsked, denied: false,
                              action: L10n.text(askingSystemAudio ? .welcomeWait : .welcomeAllow, language: language)) {
                    askingSystemAudio = true
                    Task {
                        await CallRecorder.primeSystemAudioPermission()
                        UserDefaults.standard.set(true, forKey: "systemAudioPrimed")
                        systemAudioAsked = true
                        askingSystemAudio = false
                    }
                }
                Text("Se per errore hai premuto «Non consentire», riattiva Cornetta in Impostazioni di Sistema › Privacy e sicurezza.")
                    .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("Come si usa").font(.headline)
                Label("Quando parte una chiamata, Cornetta ti chiede se registrarla.", systemImage: "phone.fill")
                Label("Oppure apri il menu della cornetta e scegli Avvia registrazione (⌘R).", systemImage: "record.circle")
                if SpeechEngine.isAvailable {
                    Label("A fine chiamata trovi la trascrizione in Registrazioni (⌘T).", systemImage: "text.bubble")
                }
            }
            .foregroundStyle(.secondary)

            Toggle("Apri Cornetta all'accensione del Mac, così è sempre pronta", isOn: $launchAtLogin)

            HStack {
                Spacer()
                Button("Inizia") {
                    LaunchAtLogin.set(launchAtLogin)
                    done()
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding(28)
        .frame(width: 520)
    }

    private func openPrivacy(_ anchor: String) {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?\(anchor)") { NSWorkspace.shared.open(url) }
    }
}

struct PermissionRow: View {
    let number: Int
    let title: String
    let detail: String
    let granted: Bool
    let denied: Bool
    let action: String
    let onAsk: () -> Void
    @Environment(\.appLanguage) private var language

    var body: some View {
        HStack(alignment: .center, spacing: 14) {
            ZStack {
                Circle().fill(granted ? Color.green.opacity(0.18) : Color.secondary.opacity(0.15)).frame(width: 30, height: 30)
                if granted {
                    Image(systemName: "checkmark").font(.system(size: 13, weight: .bold)).foregroundStyle(.green)
                } else {
                    Text("\(number)").font(.system(size: 14, weight: .semibold))
                }
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.body.weight(.semibold))
                Text(denied ? L10n.text(.permissionDenied, language: language) : detail)
                    .font(.callout).foregroundStyle(denied ? .red : .secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer()
            if granted {
                Text(L10n.text(.permissionDone, language: language)).foregroundStyle(.secondary)
            } else {
                Button(denied ? L10n.text(.permissionOpenSettings, language: language) : action, action: onAsk)
            }
        }
    }
}
