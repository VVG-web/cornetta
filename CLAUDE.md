# Cornetta

Registratore di chiamate gratuito e open source: app Mac (Swift, `Sources/`), app Windows in beta
(.NET Framework 4.8, `windows/`), sito statico (`site/`). Testi e commenti in italiano.
Il taglio di prodotto sta in `PRODUCT.md`; la verifica e l'ambiente in `docs/DEVELOPMENT.md`.

## Comandi

```bash
scripts/test.sh                                  # test Mac (Core e app)
cd windows && dotnet test Cornetta.Windows.sln   # test Windows, girano anche su Mac
python3 -m unittest discover -s scripts/tests   # test degli script e del sito
scripts/build-dmg.sh                             # DMG macOS universale
./scripts/check.sh                               # gate completo
```

## Regole

- Privacy prima di tutto: niente telemetria, analytics, cookie, crash reporting, server di feedback o
  aggiornamenti automatici. L'app non apre connessioni in background.
- Le uniche connessioni sono quelle avviate dall'utente: controllo manuale delle release su GitHub e
  apertura di una issue su GitHub. Audio e trascrizioni non lasciano il computer.
- Ogni nuovo testo dell'interfaccia entra in `localization/strings.json`, poi si rigenera con
  `scripts/localization.py`. Italiano e inglese devono restare completi.
- Ogni guasto trovato su una macchina vera diventa un controllo in CI o nei test prima del rilascio
  successivo.
- I test del sito usano `site/`; non esistono Worker, D1, KV, Plausible o Telegram in questo fork.

## Errori comuni

- NON aggiungere un endpoint di telemetria o un feedback server: `scripts/tests/test_privacy_guard.py`
  deve fallire se ricompaiono.
- NON aggiungere Sparkle, Velopack UpdateManager o timer di controllo aggiornamenti. Il controllo è solo
  manuale e apre GitHub.
- NON mettere `kAudioAggregateDeviceTapAutoStartKey` a true: su macOS 26 l'aggregate col tap non parte
  (zero callback).
- NON leggere il JSON delle trascrizioni col decoder di default: le date sono ISO 8601 e tutto risulta
  «Da trascrivere». Usa `Transcript.decoder`.
- NON aprire una finestra in `applicationDidFinishLaunching` di un'app MenuBarExtra: non arriva sullo
  schermo. Aprila dopo, con `asyncAfter` di 0,5 s.
- NON usare i predefiniti generali su Windows al posto di quelli del ruolo Comunicazioni: le chiamate
  passano da lì. Il microfono generale serve solo se manca quello di Comunicazioni; l'uscita generale si
  ascolta in aggiunta, mai al suo posto.
- NON fidarti di selftest e `--render-ui` per l'avvio su Windows: non passano dal costruttore di
  `TrayApp`. La CI prova l'app vera con `--smoke-tray`.
- Le GitHub Actions restano fissate a uno SHA completo (`scripts/tests/test_pins.py`). Per aggiornarle
  scegli una versione uscita da almeno due settimane.
- NON compilare l'app con l'SDK 27 dei Command Line Tools: manca il plugin delle macro di SwiftUI
  («SwiftUIMacros not found»). Compila con
  `SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk swift build`.
