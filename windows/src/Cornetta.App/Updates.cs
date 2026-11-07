using System;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using Cornetta.Core;

namespace Cornetta.App
{
    /// <summary>Icone incluse nell'eseguibile.</summary>
    internal static class TrayIcons
    {
        public static readonly Icon App = Load("cornetta.ico", 32);
        public static readonly Icon Idle = Load("tray-idle.ico", SystemInformation.SmallIconSize.Width);
        public static readonly Icon Recording = Load("tray-recording.ico", SystemInformation.SmallIconSize.Width);

        private static Icon Load(string name, int size)
        {
            using (var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("Cornetta." + name))
            {
                if (stream == null) return SystemIcons.Application;
                return new Icon(stream, new Size(size, size));
            }
        }
    }

    /// <summary>Esito di un controllo manuale degli aggiornamenti.</summary>
    internal enum UpdateCheck { UpToDate, Available, Failed }

    /// <summary>
    /// Controllo manuale delle release su GitHub. Non parte niente all'avvio e non c'è nessun timer:
    /// la richiesta esiste solo dopo «Controlla gli aggiornamenti su GitHub…». Non scarica e non installa nulla.
    /// </summary>
    internal sealed class UpdateService
    {
        private static readonly HttpClient Client = CreateClient();
        private string? availableVersion;
        private string releaseUrl = AppInfo.LatestReleaseUrl;

        private static HttpClient CreateClient()
        {
            ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;
            return new HttpClient { Timeout = TimeSpan.FromSeconds(15) };
        }

        public string? AvailableVersion => availableVersion;

        public string ReleaseUrl => releaseUrl;

        public async Task<UpdateCheck> CheckAsync()
        {
            availableVersion = null;
            releaseUrl = AppInfo.LatestReleaseUrl;
            try
            {
                using (var request = new HttpRequestMessage(HttpMethod.Get, AppInfo.LatestReleaseApiUrl))
                {
                    request.Headers.UserAgent.ParseAdd("Cornetta/" + AppInfo.Version);
                    request.Headers.Accept.ParseAdd("application/vnd.github+json");
                    request.Headers.CacheControl = new System.Net.Http.Headers.CacheControlHeaderValue { NoCache = true };
                    using (var response = await Client.SendAsync(request).ConfigureAwait(true))
                    {
                        if (!response.IsSuccessStatusCode)
                        {
                            Diagnostics.Log("Controllo aggiornamenti: HTTP " + (int)response.StatusCode);
                            return UpdateCheck.Failed;
                        }
                        string json = await response.Content.ReadAsStringAsync().ConfigureAwait(true);
                        Release? release = Parse(json);
                        if (release?.TagName == null) return UpdateCheck.Failed;
                        string? version = ReleaseVersion.Normalized(release.TagName);
                        if (version == null)
                        {
                            Diagnostics.Log("Controllo aggiornamenti: tag non riconosciuto");
                            return UpdateCheck.Failed;
                        }
                        string current = AppInfo.Version == "dev" ? "0.0.0" : AppInfo.Version;
                        if (!ReleaseVersion.IsNewer(release.TagName, current)) return UpdateCheck.UpToDate;
                        availableVersion = version;
                        releaseUrl = SafeReleaseUrl(release.HtmlUrl);
                        Diagnostics.Log("Aggiornamento disponibile su GitHub: " + version);
                        return UpdateCheck.Available;
                    }
                }
            }
            catch (Exception ex)
            {
                Diagnostics.Log("Controllo aggiornamenti non riuscito: " + ex.GetBaseException().Message);
                return UpdateCheck.Failed;
            }
        }

        private static Release? Parse(string json)
        {
            try
            {
                var serializer = new DataContractJsonSerializer(typeof(Release));
                using (var stream = new MemoryStream(Encoding.UTF8.GetBytes(json)))
                {
                    return serializer.ReadObject(stream) as Release;
                }
            }
            catch (SerializationException) { return null; }
            catch (ArgumentException) { return null; }
            catch (InvalidOperationException) { return null; }
        }

        /// <summary>L'URL apre solo una release del repository fork: il resto non viene mai passato al browser.</summary>
        private static string SafeReleaseUrl(string? raw)
        {
            if (Uri.TryCreate(raw, UriKind.Absolute, out Uri? uri)
                && uri.Scheme == Uri.UriSchemeHttps
                && uri.Host == "github.com"
                && uri.AbsolutePath.StartsWith("/" + AppInfo.GithubRepository + "/releases/", StringComparison.Ordinal))
            {
                return uri.ToString();
            }
            return AppInfo.LatestReleaseUrl;
        }

        [DataContract]
        private sealed class Release
        {
            [DataMember(Name = "tag_name")] public string? TagName { get; set; }
            [DataMember(Name = "html_url")] public string? HtmlUrl { get; set; }
        }
    }

    /// <summary>Scorciatoia globale Ctrl+Alt+R per avviare e fermare la registrazione.</summary>
    internal sealed class GlobalHotkey : NativeWindow, IDisposable
    {
        private const int Id = 0xC0E7;
        private readonly Action pressed;

        public GlobalHotkey(Action pressed)
        {
            this.pressed = pressed;
            CreateHandle(new CreateParams());
            Registered = NativeMethods.RegisterHotKey(Handle, Id,
                NativeMethods.MOD_CONTROL | NativeMethods.MOD_ALT | NativeMethods.MOD_NOREPEAT, (uint)Keys.R);
            if (!Registered) Diagnostics.Log("Scorciatoia Ctrl+Alt+R già usata da un'altra app");
        }

        public bool Registered { get; }

        protected override void WndProc(ref Message m)
        {
            if (m.Msg == NativeMethods.WM_HOTKEY && m.WParam.ToInt32() == Id) pressed();
            base.WndProc(ref m);
        }

        public void Dispose()
        {
            if (Registered) NativeMethods.UnregisterHotKey(Handle, Id);
            DestroyHandle();
        }
    }
}
