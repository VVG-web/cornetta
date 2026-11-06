using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Media;
using System.Reflection;
using System.Threading.Tasks;
using System.Windows.Forms;
using Cornetta.Core;
using Microsoft.Win32;

namespace Cornetta.App
{
    /// <summary>
    /// Cornetta nell'area di notifica: menu, registrazione, pannelli, rilevamento chiamate, aggiornamenti.
    /// Porta di RecorderModel.swift e CornettaApp.swift. Tutto gira sul thread dell'interfaccia,
    /// tranne avvio e stop della cattura (Task.Run).
    /// </summary>
    internal sealed class TrayApp : ApplicationContext
    {
        private static readonly TimeSpan UpdateInterval = TimeSpan.FromHours(4);

        private readonly NotifyIcon tray;
        private readonly ContextMenuStrip menu = new ContextMenuStrip();
        private readonly Control invoker = new Control();
        private readonly Timer meterTimer = new Timer { Interval = 100 };
        private readonly Timer callTimer = new Timer { Interval = 2000 };
        private readonly Timer updateTimer = new Timer { Interval = (int)UpdateInterval.TotalMilliseconds };
        private readonly CallMonitor calls = new CallMonitor();
        private readonly UpdateService updates = new UpdateService();
        private readonly GlobalHotkey hotkey;

        private Recorder? recorder;
        private bool busy;
        private DateTime startedAt;
        private string? microphoneName;
        private string? message;
        private string? lastFile;
        private bool microphoneDenied;
        private bool callEndedSuggestion;
        private bool pollInFlight;
        /// <summary>La conversione dell'ultima registrazione fermata, finché non finisce.</summary>
        private Task<bool>? saving;
        private SilenceWatch? silenceWatch;

        private OverlayForm? overlay;
        private NoticeForm? notice;
        private Func<NoticeForm>? noticeFactory;
        private Timer? noticeTimeout;
        private FeedbackForm? feedback;
        private string? pendingUpdateNotice;
        private bool installing;

        public TrayApp(bool firstRun)
        {
            invoker.CreateControl();
            // Prima del menu: BuildMenu legge hotkey.Registered.
            hotkey = new GlobalHotkey(Toggle);
            tray = new NotifyIcon { Icon = TrayIcons.Idle, Text = "Cornetta", ContextMenuStrip = menu, Visible = true };
            tray.MouseUp += (_, e) => { if (e.Button == MouseButtons.Left) ShowMenu(); };
            tray.BalloonTipClicked += (_, __) => RevealLastFile();
            menu.Opening += (_, e) => { BuildMenu(); e.Cancel = false; };
            BuildMenu();

            meterTimer.Tick += (_, __) => Tick();
            callTimer.Tick += (_, __) => PollCalls();
            callTimer.Start();
            updateTimer.Tick += async (_, __) => await CheckUpdates(manual: false);
            updateTimer.Start();
            AppLanguageSettings.LanguageChanged += RelayToOpenWindows;
            // Spegnimento, disconnessione e sospensione: il file va chiuso prima, o resta illeggibile.
            SystemEvents.SessionEnding += OnSessionEnding;
            SystemEvents.PowerModeChanged += OnPowerModeChanged;

            // Un controllo all'avvio, oltre a quelli ogni 4 ore: chi apre l'app scopre subito la novità.
            var startupCheck = new Timer { Interval = 5000 };
            startupCheck.Tick += async (_, __) => { startupCheck.Stop(); startupCheck.Dispose(); await CheckUpdates(manual: false); };
            startupCheck.Start();

            if (firstRun)
            {
                tray.ShowBalloonTip(10_000, L10n.Text(L10nKey.WindowsTrayReadyTitle),
                    L10n.Text(L10nKey.WindowsTrayReadyMessage), ToolTipIcon.Info);
            }
            RecoverInterruptedRecordings();
        }

        /// <summary>
        /// Registrazioni interrotte da un crash, da Gestione attività o da uno spegnimento: le salva come il Mac.
        /// L'elenco si legge subito, prima che parta una registrazione nuova; la conversione gira in background.
        /// </summary>
        private async void RecoverInterruptedRecordings()
        {
            try
            {
                var leftovers = WorkingFiles.Leftovers(AppInfo.WorkingDirectory);
                if (leftovers.Length == 0) return;
                List<string> saved = await Task.Run(() => RecordingFiles.Recover(leftovers, AppInfo.RecordingsDirectory));
                if (saved.Count == 0) return;
                string name = saved[saved.Count - 1];
                lastFile = Path.Combine(AppInfo.RecordingsDirectory, name);
                message = L10n.Format(L10nKey.RecordingRecovered, name);
                tray.ShowBalloonTip(8000, L10n.Text(L10nKey.WindowsTrayRecoveredTitle),
                    saved.Count == 1
                        ? L10n.Format(L10nKey.WindowsTrayRecoveredMessageOne, name)
                        : L10n.Format(L10nKey.WindowsTrayRecoveredMessageMany, saved.Count),
                    ToolTipIcon.Info);
            }
            catch (Exception ex)
            {
                Diagnostics.Log("Recupero delle registrazioni interrotte: " + ex.Message);
            }
        }

        private bool IsRecording => recorder != null;

        private string ElapsedText => TimeText.Elapsed(IsRecording ? DateTime.UtcNow - startedAt : TimeSpan.Zero);

        // MARK: - Menu

        private void ShowMenu()
        {
            // NotifyIcon apre il menu solo col tasto destro: col sinistro si usa lo stesso metodo interno.
            var method = typeof(NotifyIcon).GetMethod("ShowContextMenu", BindingFlags.Instance | BindingFlags.NonPublic);
            method?.Invoke(tray, null);
        }

        private void BuildMenu()
        {
            menu.Items.Clear();
            string? version = updates.AvailableVersion;
            if (version != null)
            {
                Add(L10n.Format(L10nKey.MenuUpdateInstall, version), () => InstallUpdate());
                menu.Items.Add(new ToolStripSeparator());
            }
            var toggle = Add(L10n.Text(IsRecording ? L10nKey.MenuRecordStop : L10nKey.MenuRecordStart), Toggle);
            if (hotkey.Registered) toggle.ShortcutKeyDisplayString = "Ctrl+Alt+R";
            toggle.Enabled = !busy;
            if (IsRecording)
            {
                Info(L10n.Format(L10nKey.MenuRecordStatus, ElapsedText));
                Info(L10n.Format(L10nKey.MenuMicrophone, microphoneName ?? L10n.Text(L10nKey.CommonNone)));
            }
            if (message != null) Info(message);
            if (microphoneDenied)
            {
                Add(L10n.Text(L10nKey.MenuMicrophoneSettings), () => OpenSettings("ms-settings:privacy-microphone"));
            }
            menu.Items.Add(new ToolStripSeparator());
            Add(L10n.Text(L10nKey.MenuRecordingsOpenFolder), OpenFolder);
            if (lastFile != null) Add(L10n.Text(L10nKey.MenuLastRecording), RevealLastFile);
            menu.Items.Add(new ToolStripSeparator());
            Add(L10n.Text(L10nKey.MenuFeedback), OpenFeedback);
            var overlayItem = Add(L10n.Text(L10nKey.MenuOverlay), () =>
            {
                Settings.ShowOverlay = !Settings.ShowOverlay;
                RefreshOverlay();
            });
            overlayItem.Checked = Settings.ShowOverlay;
            var proposeItem = Add(L10n.Text(L10nKey.MenuPropose), () => Settings.ProposeOnCall = !Settings.ProposeOnCall);
            proposeItem.Checked = Settings.ProposeOnCall;
            var telemetryItem = Add(L10n.Text(L10nKey.MenuTelemetry), () => Telemetry.IsEnabled = !Telemetry.IsEnabled);
            telemetryItem.Checked = Telemetry.IsEnabled;
            Add(L10n.Text(L10nKey.MenuUpdates), async () => await CheckUpdates(manual: true));
            var languageItem = new ToolStripMenuItem(L10n.Text(L10nKey.MenuLanguage));
            foreach (AppLanguage language in new[] { AppLanguage.Italian, AppLanguage.English })
            {
                var choice = new ToolStripMenuItem(language == AppLanguage.Italian
                    ? L10n.Text(L10nKey.MenuLanguageItalian)
                    : L10n.Text(L10nKey.MenuLanguageEnglish))
                {
                    Checked = AppLanguageSettings.Current == language,
                };
                choice.Click += (_, __) => AppLanguageSettings.Select(language);
                languageItem.DropDownItems.Add(choice);
            }
            menu.Items.Add(languageItem);
            menu.Items.Add(new ToolStripSeparator());
            Info("Cornetta " + AppInfo.Version);
            Add(L10n.Text(L10nKey.MenuQuit), Quit);
        }

        private ToolStripMenuItem Add(string text, Action action)
        {
            var item = new ToolStripMenuItem(text);
            item.Click += (_, __) => action();
            menu.Items.Add(item);
            return item;
        }

        private void Info(string text)
        {
            menu.Items.Add(new ToolStripMenuItem(text) { Enabled = false });
        }

        private void UpdateTrayIcon()
        {
            if (IsRecording)
            {
                tray.Icon = TrayIcons.Recording;
                SetTrayText(L10n.Format(L10nKey.WindowsTrayRecordingStatus, ElapsedText));
            }
            else if (updates.AvailableVersion != null)
            {
                tray.Icon = TrayIcons.Update;
                SetTrayText(L10n.Text(L10nKey.WindowsTrayUpdateStatus));
            }
            else
            {
                tray.Icon = TrayIcons.Idle;
                SetTrayText("Cornetta");
            }
        }

        private void SetTrayText(string text)
        {
            // NotifyIcon accetta al massimo 63 caratteri.
            tray.Text = text.Length > 63 ? text.Substring(0, 63) : text;
        }

        // MARK: - Registrazione

        private void Toggle()
        {
            if (busy) return;
            if (IsRecording) _ = Stop(); else _ = Start();
        }

        private async Task Start()
        {
            if (IsRecording || busy) return;
            if (installing)
            {
                // L'aggiornamento riavvia l'app: una registrazione partita adesso verrebbe troncata.
                tray.ShowBalloonTip(5000, "Cornetta", L10n.Text(L10nKey.WindowsTrayInstalling), ToolTipIcon.Info);
                return;
            }
            busy = true;
            message = null;
            CloseNotice();
            Diagnostics.Log("Avvio richiesto");
            bool micAllowed = MicrophonePrivacy.IsAllowed();
            Diagnostics.Log("Permesso microfono: " + (micAllowed ? "true" : "false"));
            microphoneDenied = !micAllowed;
            // Un nome occupato anche da un WAV ancora in «In corso» (salvataggio fallito, recupero in corso): il nuovo lo azzererebbe.
            string path = FileNaming.RecordingPath(AppInfo.RecordingsDirectory, DateTime.Now,
                p => File.Exists(p) || File.Exists(WorkingFiles.PathFor(AppInfo.WorkingDirectory, p)), RecordingFiles.Extension);
            var newRecorder = new Recorder(path);
            newRecorder.MicrophoneChanged += name => invoker.BeginInvoke(new Action(() => { microphoneName = name; Tick(); }));
            newRecorder.Failure += text => invoker.BeginInvoke(new Action(() => HandleFailure(newRecorder, text)));
            try
            {
                await Task.Run(() => newRecorder.Start(micAllowed));
            }
            catch (Exception ex)
            {
                Telemetry.Send("registrazione", "errore", TelemetryPayload.ErrorCode(ex, "avvio"));
                Diagnostics.Log("Avvio registrazione non riuscito: " + ex.Message);
                message = L10n.Text(L10nKey.WindowsTrayStartError);
                busy = false;
                tray.ShowBalloonTip(8000, "Cornetta", message, ToolTipIcon.Warning);
                return;
            }
            recorder = newRecorder;
            busy = false;
            microphoneName = newRecorder.MicrophoneName;
            if (!micAllowed)
            {
                message = L10n.Text(L10nKey.RecordingMicrophoneDenied);
            }
            else if (newRecorder.MicrophoneName == null)
            {
                message = L10n.Text(L10nKey.WindowsTrayNoMicrophone);
            }
            else if (newRecorder.OutputName == null)
            {
                message = L10n.Text(L10nKey.WindowsTrayNoOutput);
            }
            startedAt = DateTime.UtcNow;
            callEndedSuggestion = false;
            calls.RecordingStarted(DateTime.UtcNow);
            silenceWatch = new SilenceWatch();
            silenceWatch.NoteCallApps(calls.CurrentApps.Count);
            meterTimer.Start();
            RefreshOverlay();
            UpdateTrayIcon();
            if (message != null) tray.ShowBalloonTip(6000, "Cornetta", message, ToolTipIcon.Warning);
        }

        /// <summary>
        /// Chiude subito il WAV di lavoro e libera l'interfaccia: la conversione in AAC (decine di secondi per una chiamata
        /// lunga) gira dopo, in background, e intanto si può già registrare la chiamata successiva.
        /// </summary>
        private async Task Stop()
        {
            var current = recorder;
            if (current == null || busy) return;
            busy = true;
            RecordingStats? stats = null;
            try
            {
                stats = await Task.Run(() => current.StopWithoutSaving());
                Diagnostics.Log("Stop: " + Diagnostics.F(stats.Seconds, 2) + " s scritti, "
                    + Diagnostics.F((DateTime.UtcNow - startedAt).TotalSeconds, 2) + " s dall'avvio, riavvii " + current.RestartCount
                    + ", guadagno voce " + Diagnostics.F(current.MicGain, 1));
            }
            catch (Exception ex)
            {
                Telemetry.Send("registrazione", "errore", TelemetryPayload.ErrorCode(ex, "stop"));
                Diagnostics.Log("Stop non riuscito: " + ex.Message);
            }
            finally
            {
                busy = false;
            }
            Finish();
            message = L10n.Format(L10nKey.WindowsTraySaving, Path.GetFileName(current.OutputPath));
            // File.Exists fuori dal thread dell'interfaccia: la cartella può stare su un disco di rete o su OneDrive.
            var save = Task.Run(() => current.SaveRecording());
            saving = save;
            _ = save.ContinueWith(t => OnUi(() => SaveFinished(current, t, stats)));
        }

        private void SaveFinished(Recorder current, Task<bool> save, RecordingStats? stats)
        {
            if (saving == save) saving = null;
            bool saved = save.Status == TaskStatus.RanToCompletion && save.Result;
            if (stats != null)
            {
                if (current.SaveError != null)
                    Telemetry.Send("registrazione", "errore", TelemetryPayload.ErrorCode(current.SaveError, "salvataggio"), stats.Seconds);
                else
                    Telemetry.Send("registrazione", "ok", seconds: stats.Seconds);
            }
            if (saved) lastFile = current.OutputPath;
            // Una registrazione nuova partita nel frattempo tiene il suo stato: niente messaggio né avviso sopra la chiamata.
            if (IsRecording || busy) return;
            if (saved)
            {
                message = L10n.Format(L10nKey.RecordingSaved, Path.GetFileName(current.OutputPath));
                tray.ShowBalloonTip(6000, L10n.Text(L10nKey.WindowsTraySavedTitle),
                    L10n.Format(L10nKey.WindowsTraySavedMessage, Path.GetFileName(current.OutputPath)),
                    ToolTipIcon.Info);
            }
            else
            {
                message = L10n.Text(L10nKey.WindowsTrayNotSaved);
                tray.ShowBalloonTip(8000, "Cornetta", L10n.Text(L10nKey.WindowsTrayNotSaved), ToolTipIcon.Warning);
            }
            if (pendingUpdateNotice != null)
            {
                string version = pendingUpdateNotice;
                pendingUpdateNotice = null;
                AnnounceUpdate(version);
            }
        }

        private void HandleFailure(Recorder failed, string text)
        {
            if (recorder != failed) return;
            Telemetry.Send("registrazione", "errore", "interrotta", (DateTime.UtcNow - startedAt).TotalSeconds);
            lastFile = failed.OutputPath;
            Finish();
            message = text;
            tray.ShowBalloonTip(8000, "Cornetta", text, ToolTipIcon.Error);
        }

        private void Finish()
        {
            meterTimer.Stop();
            recorder = null;
            silenceWatch = null;
            callEndedSuggestion = false;
            if (notice?.Kind == "silence") CloseNotice();
            RefreshOverlay();
            UpdateTrayIcon();
        }

        private void Tick()
        {
            if (!IsRecording) return;
            var levels = recorder!.Meter?.Levels ?? (0f, 0f);
            overlay?.UpdateState(ElapsedText, levels.Mic, levels.System, microphoneName, callEndedSuggestion);
            if (DateTime.UtcNow.Millisecond < 100) UpdateTrayIcon();
            CheckOthersAudio();
        }

        /// <summary>La voce degli altri non arriva (vedi SilenceWatch): avviso una volta, oppure solo una riga nel log.</summary>
        private void CheckOthersAudio()
        {
            var current = recorder!;
            var stats = current.Stats;
            if (stats == null || silenceWatch == null) return;
            switch (silenceWatch.Check(stats))
            {
                case SilenceAlert.OthersMuted:
                    Diagnostics.Log("Avviso: audio di sistema muto durante una chiamata");
                    ShowOthersMutedNotice(current.GeneralOutputName != null ? current.OutputName + " e " + current.GeneralOutputName : current.OutputName);
                    break;
                case SilenceAlert.LongSilence:
                    Diagnostics.Log("Audio di sistema a zero da oltre " + SilenceWatch.LongSilenceSeconds + " s durante una chiamata");
                    break;
            }
        }

        // MARK: - Pannello di registrazione

        private void RefreshOverlay()
        {
            if (IsRecording && Settings.ShowOverlay)
            {
                if (overlay == null || overlay.IsDisposed)
                {
                    overlay = new OverlayForm();
                    overlay.StopClicked += () => _ = Stop();
                    overlay.FeedbackClicked += OpenFeedback;
                    overlay.ContinueClicked += DismissCallEnded;
                }
                Tick();
                overlay.ShowPanel();
            }
            else
            {
                overlay?.Hide();
            }
        }

        private void DismissCallEnded()
        {
            callEndedSuggestion = false;
            calls.DismissCallEnded();
            Tick();
        }

        // MARK: - Chiamate

        private async void PollCalls()
        {
            // Sessioni audio e processi si leggono fuori dal thread dell'interfaccia: un dispositivo lento non blocca menu e scorciatoia.
            if (pollInFlight) return;
            pollInFlight = true;
            List<CallApp> apps;
            try { apps = await Task.Run(() => CallDetector.CallApps(MicrophoneUsage.Read())); }
            finally { pollInFlight = false; }
            bool noticeOpen = notice != null;
            var result = calls.Poll(DateTime.UtcNow, apps, IsRecording, Settings.ProposeOnCall, noticeOpen, notice?.Kind == "call");

            if (IsRecording)
            {
                silenceWatch?.NoteCallApps(apps.Count);
                if (result.CallResumed)
                {
                    callEndedSuggestion = false;
                    if (notice?.Kind == "ended") CloseNotice();
                    Tick();
                }
                if (result.CallEnded)
                {
                    callEndedSuggestion = true;
                    if (!Settings.ShowOverlay) ShowCallEndedNotice();
                    Tick();
                }
                return;
            }

            if (result.CloseCallNotice) CloseNotice();
            if (result.PromptApp != null) ShowCallNotice(result.PromptApp);
        }

        private void ShowCallNotice(string appName)
        {
            Diagnostics.Log("Chiamata rilevata: " + appName);
            ShowLocalizedNotice(() => new NoticeForm("call", "", Theme.Red,
                L10n.Format(L10nKey.NoticeCallTitle, appName),
                L10n.Text(L10nKey.NoticeCallMessage),
                L10n.Text(L10nKey.NoticeRecord), L10n.Text(L10nKey.NoticeNotNow),
                () => { CloseNotice(); _ = Start(); },
                CloseNotice));
            // Se nessuno risponde, l'avviso sparisce da solo dopo 30 secondi.
            noticeTimeout = new Timer { Interval = 30_000 };
            noticeTimeout.Tick += (_, __) => { if (notice?.Kind == "call") CloseNotice(); };
            noticeTimeout.Start();
        }

        private void ShowCallEndedNotice()
        {
            ShowLocalizedNotice(() => new NoticeForm("ended", "", Theme.Orange,
                L10n.Text(L10nKey.NoticeCallEndedTitle),
                L10n.Text(L10nKey.NoticeCallEndedMessage),
                L10n.Text(L10nKey.NoticeStopAndSave), L10n.Text(L10nKey.CommonContinue),
                () => { CloseNotice(); _ = Stop(); },
                () => { CloseNotice(); DismissCallEnded(); }));
        }

        private void ShowOthersMutedNotice(string? outputs)
        {
            SystemSounds.Exclamation.Play();
            ShowLocalizedNotice(() => new NoticeForm("silence", "\uE7BA", Theme.Orange,
                L10n.Text(L10nKey.WindowsNoticeSilenceTitle),
                L10n.Format(L10nKey.WindowsNoticeSilenceMessage,
                    outputs ?? L10n.Text(L10nKey.WindowsNoticeSilenceOutput)),
                L10n.Text(L10nKey.WindowsNoticeAudioSettings), L10n.Text(L10nKey.CommonClose),
                () => { CloseNotice(); OpenSettings("ms-settings:sound"); },
                CloseNotice));
        }

        // MARK: - Aggiornamenti

        private async Task CheckUpdates(bool manual)
        {
            // Durante l'installazione un controllo potrebbe cambiare l'aggiornamento scelto: si salta.
            if (installing) return;
            var result = await updates.CheckAsync();
            UpdateTrayIcon();
            switch (result)
            {
                case UpdateCheck.Found:
                    AnnounceUpdate(updates.AvailableVersion!);
                    break;
                case UpdateCheck.UpToDate when manual:
                tray.ShowBalloonTip(5000, "Cornetta",
                    L10n.Format(L10nKey.WindowsTrayUpToDate, AppInfo.Version), ToolTipIcon.Info);
                    break;
                case UpdateCheck.NotInstalled when manual:
                tray.ShowBalloonTip(5000, "Cornetta", L10n.Text(L10nKey.WindowsTrayInstalledOnly), ToolTipIcon.Info);
                    break;
                case UpdateCheck.Failed when manual:
                tray.ShowBalloonTip(5000, "Cornetta", L10n.Text(L10nKey.WindowsTrayUpdateCheckFailed), ToolTipIcon.Warning);
                    break;
            }
        }

        private void AnnounceUpdate(string version)
        {
            // Durante una registrazione l'avviso aspetta lo stop: niente distrazioni in chiamata.
            if (IsRecording)
            {
                pendingUpdateNotice = version;
                return;
            }
            if (notice?.Kind == "update" || installing) return;
            ShowLocalizedNotice(() => new NoticeForm("update", "", Theme.Blue,
                L10n.Text(L10nKey.NoticeUpdateTitle),
                L10n.Format(L10nKey.NoticeUpdateMessage, version),
                L10n.Text(L10nKey.NoticeUpdateNow), L10n.Text(L10nKey.NoticeUpdateLater),
                () => { CloseNotice(); InstallUpdate(); },
                CloseNotice));
            SystemSounds.Asterisk.Play();
        }

        private async void InstallUpdate()
        {
            if (installing) return;
            if (IsRecording)
            {
                // Non si interrompe una chiamata: l'avviso torna appena la registrazione finisce.
                pendingUpdateNotice = updates.AvailableVersion;
                tray.ShowBalloonTip(5000, "Cornetta", L10n.Text(L10nKey.WindowsTrayUpdateWaiting), ToolTipIcon.Info);
                return;
            }
            installing = true;
                SetTrayText(L10n.Text(L10nKey.WindowsTrayUpdateDownloading));
            try
            {
                // L'aggiornamento riavvia l'app: la conversione appena partita finisce prima.
                if (saving != null) await saving;
                await updates.InstallAsync(
                    percent => invoker.BeginInvoke(new Action(() =>
                        SetTrayText(L10n.Format(L10nKey.WindowsTrayUpdateProgress, percent)))),
                    () => { tray.Visible = false; });
            }
            catch (Exception ex)
            {
                Diagnostics.Log("Aggiornamento non riuscito: " + ex.Message);
                tray.Visible = true;
                tray.ShowBalloonTip(8000, "Cornetta", L10n.Text(L10nKey.WindowsTrayUpdateFailed), ToolTipIcon.Warning);
            }
            installing = false;
            UpdateTrayIcon();
        }

        // MARK: - Avvisi

        private void ShowNotice(NoticeForm form)
        {
            CloseNotice();
            notice = form;
            notice.ShowPanel();
        }

        private void ShowLocalizedNotice(Func<NoticeForm> factory)
        {
            ShowNotice(factory());
            noticeFactory = factory;
        }

        private void CloseNotice()
        {
            noticeTimeout?.Stop();
            noticeTimeout?.Dispose();
            noticeTimeout = null;
            if (notice != null)
            {
                notice.Close();
                notice.Dispose();
                notice = null;
            }
            noticeFactory = null;
        }

        // MARK: - Feedback

        private void OpenFeedback()
        {
            if (feedback != null && !feedback.IsDisposed)
            {
                feedback.Activate();
                return;
            }
            feedback = new FeedbackForm(microphoneName);
            feedback.FormClosed += (_, __) => feedback = null;
            feedback.Show();
            feedback.Activate();
        }

        // MARK: - Esplora file

        private void OpenFolder()
        {
            string folder = AppInfo.RecordingsDirectory;
            try
            {
                Directory.CreateDirectory(folder);
                Process.Start(new ProcessStartInfo("explorer.exe", "\"" + folder + "\"") { UseShellExecute = true });
            }
            catch (Exception ex)
            {
                Diagnostics.Log("Cartella non aperta: " + ex.Message);
            }
        }

        private void RevealLastFile()
        {
            if (lastFile == null || !File.Exists(lastFile)) return;
            try
            {
                Process.Start(new ProcessStartInfo("explorer.exe", "/select,\"" + lastFile + "\"") { UseShellExecute = true });
            }
            catch (Exception ex)
            {
                Diagnostics.Log("File non mostrato: " + ex.Message);
            }
        }

        private void OpenSettings(string uri)
        {
            try
            {
                Process.Start(new ProcessStartInfo(uri) { UseShellExecute = true });
            }
            catch (Exception ex)
            {
                Diagnostics.Log("Impostazioni non aperte: " + ex.Message);
            }
        }

        // MARK: - Uscita

        private async void Quit()
        {
            // Se una registrazione sta partendo, aspetta che sia partita: poi la chiude bene.
            while (busy) await Task.Delay(100);
            if (recorder != null)
            {
                var current = recorder;
                var stats = await Task.Run(() => current.Stop());
                Diagnostics.Log("Stop all'uscita: " + Diagnostics.F(stats.Seconds, 2) + " s scritti");
                recorder = null;
            }
            // Una conversione partita da Stop: qualche secondo per finirla, poi il WAV lo salva il recupero al prossimo avvio.
            if (saving != null) await Task.WhenAny(saving, Task.Delay(TimeSpan.FromSeconds(10)));
            ExitThread();
        }

        private void OnSessionEnding(object sender, SessionEndingEventArgs e) =>
            StopForSystem(L10n.Text(L10nKey.WindowsTrayShutdownStop));

        private void OnPowerModeChanged(object sender, PowerModeChangedEventArgs e)
        {
            if (e.Mode == PowerModes.Suspend) StopForSystem(L10n.Text(L10nKey.WindowsTraySleepStop));
        }

        /// <summary>
        /// Chiude subito il WAV di lavoro, da qualunque thread arrivi l'evento di sistema: qui la conversione non fa in tempo.
        /// Parte subito dopo in background; se Windows chiude l'app prima, la finisce il recupero al prossimo avvio.
        /// </summary>
        private void StopForSystem(string reason)
        {
            var current = recorder;
            if (current == null) return;
            try
            {
                var stats = Task.Run(() => current.StopWithoutSaving()).Result;
                Diagnostics.Log(reason + " " + Diagnostics.F(stats.Seconds, 2) + " s scritti");
            }
            catch (Exception ex)
            {
                Diagnostics.Log("Stop di sistema non riuscito: " + ex.GetBaseException().Message);
            }
            string pending = current.OutputPath;
            OnUi(() =>
            {
                if (recorder != current) return;
                lastFile = pending;
                Finish();
                message = reason;
            });
            Task.Run(() => current.SaveRecording()).ContinueWith(t => OnUi(() =>
            {
                if (lastFile != pending) return;
                if (t.Status == TaskStatus.RanToCompletion && t.Result) { lastFile = current.OutputPath; return; }
                lastFile = null;
                if (message == reason) message = L10n.Text(L10nKey.WindowsTrayNotSaved);
            }));
        }

        private void RelayToOpenWindows()
        {
            message = null;
            overlay?.Relocalize();
            if (notice != null && noticeFactory != null)
            {
                var factory = noticeFactory;
                CloseNotice();
                ShowNotice(factory());
                noticeFactory = factory;
            }
            UpdateTrayIcon();
        }

        private void OnUi(Action action)
        {
            try { invoker.BeginInvoke(action); }
            catch (InvalidOperationException) { }
        }

        protected override void ExitThreadCore()
        {
            SystemEvents.SessionEnding -= OnSessionEnding;
            SystemEvents.PowerModeChanged -= OnPowerModeChanged;
            // Chiude il WAV anche se l'app esce durante una registrazione: lo salva il recupero al prossimo avvio.
            if (recorder != null)
            {
                var current = recorder;
                recorder = null;
                Task.Run(() => current.StopWithoutSaving()).Wait(TimeSpan.FromSeconds(30));
            }
            try { saving?.Wait(TimeSpan.FromSeconds(5)); }
            catch (AggregateException) { }
            meterTimer.Stop();
            callTimer.Stop();
            updateTimer.Stop();
            CloseNotice();
            overlay?.Close();
            feedback?.Close();
            hotkey.Dispose();
            tray.Visible = false;
            tray.Dispose();
            base.ExitThreadCore();
        }
    }
}
