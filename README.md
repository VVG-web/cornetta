# Cornetta

**Free, open-source call recorder for Mac, with a beta for Windows.**
This repository is the privacy-clean fork [`VVG-web/cornetta-en`](https://github.com/VVG-web/cornetta-en),
based on the original [Cornetta](https://github.com/stellakamikaze/cornetta) by Federico Nejrotti.

- Download: [GitHub Releases](https://github.com/VVG-web/cornetta-en/releases/latest)
  (macOS 14.4+, Apple Silicon and Intel · Windows 10 and 11, beta)
- Site: [vvg-web.github.io/cornetta-en](https://vvg-web.github.io/cornetta-en/)
- Privacy: no telemetry, no analytics, no cookies, no feedback server.
  Recordings and transcripts stay on the computer.
- Updates: manual check against a signed feed on GitHub Pages. Nothing is downloaded or installed automatically.
- Security review: [macOS Intel safety and uninstall](docs/SECURITY-REVIEW.md).
- Stack: Swift and Core Audio process taps (`Sources/`), C# .NET Framework 4.8 with NAudio (`windows/`),
  static site (`site/`).
- License: MIT. Interface text and code comments are in Italian.

---

Registratore di chiamate gratuito per Mac. Registra in un solo file la tua voce dal microfono e la voce
delle altre persone, con qualunque app: Meet, Zoom, Teams, WhatsApp, FaceTime, Slack, Discord, il browser.

Cornetta vive nella barra dei menu. Un clic avvia la registrazione, un clic la ferma. Il file finisce in
`~/Music/Cornetta/` con il nome `Chiamata AAAA-MM-GG HH.MM.m4a`.

**Italiano o inglese.** Dal menu della cornetta, in **Lingua / Language**, scegli l'interfaccia.
La scelta resta salvata; una nuova installazione segue la lingua di sistema e tutte le altre lingue usano
l'italiano. Su Windows la stessa voce è nel menu dell'area di notifica.

## Privacy e rete

Questa versione non ha telemetria, analytics, cookie, identificativi di installazione o un server di
feedback. L'app non apre connessioni in background.

Le uniche connessioni possibili sono quelle avviate dall'utente:

- **Controlla gli aggiornamenti su GitHub…** scarica il feed firmato da GitHub Pages, verifica la firma
  ECDSA P-256 e solo allora legge la versione. La richiesta contiene la versione dell'app e un normale
  User-Agent, mai audio, testi o nomi di file.
- **Feedback** apre una nuova segnalazione pubblica su GitHub nel browser. Non c'è nessun invio automatico.

Audio e trascrizioni non lasciano mai il computer. La trascrizione usa il riconoscimento vocale di Apple
sul Mac. Il sito in `site/` è statico e non usa Plausible, Telegram o altri servizi di analisi.

Dettagli: [privacy in italiano](site/privacy/index.html) e
[privacy in English](site/en/privacy/index.html).

## Sicurezza e rimozione

L'app non installa driver, kext, estensioni di sistema, launch agent o privilegiati. Usa un dispositivo
audio aggregato privato e lo distrugge allo stop. La rimozione consiste nel chiudere l'app, disattivare
facoltativamente l'avvio al login, spostare `Cornetta.app` nel Cestino e, se si vuole, cancellare le
cartelle dati dell'utente. Il test eseguito su un Mac Intel con macOS 15.8.1 e la matrice macOS 14/15/26
sono in [docs/SECURITY-REVIEW.md](docs/SECURITY-REVIEW.md).

## Manutenzione upstream

Il workflow `.github/workflows/upstream-review.yml` controlla l'originale una volta alla settimana e
aggiorna una singola issue con un rapporto diviso in:

- modifiche al core, candidate a un port mirato;
- modifiche a privacy, rete, telemetria e aggiornamenti, da non portare automaticamente;
- UI, documentazione e localizzazione, da rivedere prima del port.

Non fa merge, cherry-pick o push automatici. Il rapporto è generato da
`scripts/upstream-review.py`.

## Requisiti

- macOS 14.4 o successivo.
- Mac con Apple Silicon o Intel (app universale).
- Per lo sviluppo: Xcode completo o Command Line Tools, .NET SDK 10, Python 3 e un browser Chromium.

## Installazione macOS

1. Apri [GitHub Releases](https://github.com/VVG-web/cornetta-en/releases/latest) e scarica il DMG.
2. Trascina Cornetta nella cartella Applicazioni.
3. Al primo avvio macOS blocca l'app, perché il fork non ha una firma Apple notarizzata. Apri
   **Impostazioni di Sistema → Privacy e sicurezza**, scorri in fondo e premi **Apri comunque**.
4. Alla prima registrazione Cornetta chiede due permessi:
   - **Microfono**, per la tua voce;
   - **Registrazione audio di sistema**, per la voce degli altri.

Se hai negato un permesso, riattivalo in **Impostazioni di Sistema → Privacy e sicurezza → Microfono**
oppure **→ Registrazione schermo e audio di sistema**.

## Uso

- **Avvia registrazione** (⌘R): l'icona diventa un pallino rosso con il tempo trascorso.
- **Ferma registrazione** (⌘R): il file viene chiuso e salvato.
- **Apri cartella registrazioni**: apre `~/Music/Cornetta/` nel Finder.
- **Controlla gli aggiornamenti su GitHub…**: confronta la versione installata con l'ultima release e apre
  GitHub se ce n'è una nuova.
- **Apri una segnalazione su GitHub…**: apre il browser sulla pagina delle issue del fork.

Se a metà chiamata cambi microfono (per esempio colleghi le AirPods), Cornetta passa al nuovo microfono e
continua sullo stesso file.

## Video dello schermo

- **Registra lo schermo…**: macOS mostra il suo selettore. Scegli uno schermo, una finestra o un'app e il
  video parte.
- Il video si salva già compresso in `~/Movies/Cornetta/` («Schermo 2026-11-03 12.30.mp4»): HEVC fino a
  1920 px di lato e 30 fotogrammi al secondo, con audio AAC.
- Nel sottomenu **Video dello schermo** scegli se registrare anche il microfono (da macOS 15) e l'audio del Mac.
- Il file è a frammenti di 10 secondi: se il Mac si spegne di colpo, il video resta leggibile fino
  all'ultimo frammento.

Prova da riga di comando:
`open -n build/Cornetta.app --args --record-screen 30 --out esito.json [--no-mic] [--no-audio]`.

## Trascrizione

Da macOS 26 Cornetta trascrive ogni chiamata sul Mac, con il riconoscimento vocale di Apple (SpeechAnalyzer).

- Durante la registrazione salva due tracce separate in `~/Library/Application Support/Cornetta/Tracce/`:
  «Tu» (microfono) e «Altri» (audio di sistema).
- Allo stop la trascrizione parte da sola.
- Il testo si salva in JSON (`~/Library/Application Support/Cornetta/Trascrizioni/`) e come `.md` accanto
  all'audio.
- La finestra **Registrazioni** (⌘T dal menu) ha l'elenco, la ricerca, il testo diviso per voce e l'ascolto
  dal punto scelto.

Prova da riga di comando:
`build/Cornetta.app/Contents/MacOS/Cornetta --transcribe file.m4a [--tracks cartella]`.

## Come funziona

Cornetta usa i *process tap* di Core Audio (macOS 14.2+): legge tutto l'audio che il Mac riproduce, senza
driver virtuali come BlackHole e senza registrare lo schermo. Il tap e il microfono stanno nello stesso
dispositivo aggregato privato, quindi le due voci condividono lo stesso orologio e restano sincronizzate.

Il file è AAC stereo a 48 kHz. La tua voce sta al centro, l'audio della chiamata mantiene il suo stereo.
Un limitatore evita la distorsione quando parlate insieme.

Durante la chiamata Cornetta scrive file CAF in `~/Library/Application Support/Cornetta/In corso/`, che
restano leggibili anche se il Mac si spegne o l'app si chiude di colpo. Allo stop li converte nel `.m4a`
in `~/Music/Cornetta/` e svuota la cartella.

## Compilare da sorgente

```bash
scripts/test.sh          # test macOS
scripts/build-dmg.sh     # produce dist/Cornetta-<versione>.dmg
./scripts/check.sh       # gate completo: lint, test, DMG, .NET, script, sito
```

Per provare la cattura senza interfaccia:

```bash
open -W -n build/Cornetta.app --args --record 10 --out /tmp/prova.m4a --debug-tracks /tmp/prova
```

Il log dell'app sta in `~/Library/Logs/Cornetta/cornetta.log`.

## Windows

La versione Windows sta in `windows/`. Fa le stesse cose della versione Mac: icona nell'area di notifica,
pannello durante la registrazione, avviso quando parte una chiamata, rilevamento delle chiamate e
registrazione dell'audio di sistema. Non ha aggiornamenti automatici.

### Installazione

1. Apri [GitHub Releases](https://github.com/VVG-web/cornetta-en/releases/latest) e scarica
   `CornettaSetup.exe`. Non servono permessi di amministratore.
2. Al primo avvio Windows mostra «Windows ha protetto il PC», perché l'installer non è firmato. Premi
   **Ulteriori informazioni**, poi **Esegui comunque**.
3. Cornetta compare nell'area di notifica, vicino all'orologio. Se non la vedi, apri la freccia `^`.

Se il microfono resta muto, apri **Impostazioni → Privacy e sicurezza → Microfono** e attiva **Consenti
alle app desktop di accedere al microfono**.

### Uso

- **Avvia registrazione** (Ctrl+Alt+R): l'icona diventa un pallino rosso e compare il pannello in alto a destra.
- **Ferma registrazione** (di nuovo Ctrl+Alt+R, oppure **Ferma** nel pannello).
- I file finiscono in `Musica\Cornetta\` con il nome `Chiamata AAAA-MM-GG HH.MM.m4a`.

Il log sta in `%LOCALAPPDATA%\Cornetta\cornetta.log`.

### Compilare e provare

Serve il .NET SDK 10. L'app è per .NET Framework 4.8, già presente in Windows 10 e 11.

```bash
cd windows
dotnet test Cornetta.Windows.sln                 # test (anche su Mac e Linux)
dotnet build Cornetta.Windows.sln -c Release     # compila anche fuori da Windows
```

Su un PC Windows:

```bat
Cornetta.exe --selftest
Cornetta.exe --record 10 --out C:\prova.m4a
```

Il CI (`.github/workflows/windows.yml`) compila, esegue i test con .NET 10 e .NET Framework 4.8, lancia
`--selftest`, `--selftest-poison`, `--render-ui`, `--smoke-tray`, impacchetta con Velopack e prova
l'installer.

### Pubblicare una versione Windows

Il CI produce `CornettaSetup.exe` e gli artifact dell'installer. La release GitHub si crea manualmente
con `gh release create` e i file prodotti; non esistono feed di aggiornamento automatico né script che
pubblichino su un server esterno.

## Sito statico

Le pagine sono in `site/` e vengono pubblicate su GitHub Pages dal workflow `.github/workflows/pages.yml`.
Non c'è un Worker, un database, un servizio di analytics o un endpoint API. I pulsanti di download
puntano direttamente a GitHub Releases. Il feed aggiornamenti e la sua firma stanno in `site/update/`;
la procedura è in [docs/UPDATES.md](docs/UPDATES.md).

## Notarizzazione Apple

Oggi il fork è firmato ad-hoc: macOS lo blocca al primo avvio e chiede «Apri comunque». Con una firma
Apple notarizzata si apre con un doppio clic. Serve l'[Apple Developer Program](https://developer.apple.com/programs/).

## Nota legale

In Italia registrare una conversazione a cui partecipi è lecito per uso personale. Diffonderla senza il
consenso delle altre persone non lo è. In altri paesi le regole cambiano: informati prima di registrare.

## Licenza

MIT. Vedi `LICENSE`.
