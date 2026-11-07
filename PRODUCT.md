# Product

<!-- impeccable:product-schema 1 -->

## Platform

web (pagina di download statica). Le app sono native: macOS (SwiftUI, barra dei menu) e Windows in beta
(.NET Framework 4.8, area di notifica).

## Stack

HTML/CSS statico in `site/`, senza Worker, database o API. Download e note di versione stanno su GitHub
Releases. L'app Mac è Swift, l'app Windows è C# .NET Framework 4.8.

## Users

Chiunque abbia bisogno di registrare una chiamata dal computer, su Mac o su Windows. Molti non sono
tecnici: arrivano dal link di un amico, da una ricerca o da una lista di app. Aprono il link dal Mac o dal
telefono, scaricano un DMG o un installer e installano un'app non notarizzata. [Inferito]

## Product Purpose

Cornetta registra le chiamate dal computer con qualunque app (WhatsApp, FaceTime, Meet, Zoom, Teams): la
voce di chi registra dal microfono e la voce degli altri dall'audio di sistema, in un file `.m4a`. Sul Mac
trascrive la chiamata sul computer. Gratuita, open source (MIT). Successo della pagina: la persona
installa e concede i permessi senza chiamare nessuno.

## Positioning

Un software gratis e open source per fare una cosa semplice che serve a tutti: registrare una chiamata.
Nessun driver audio virtuale, nessun account, nessun abbonamento, un'icona nella barra dei menu e un clic
per registrare. Propone da sola di registrare quando parte una chiamata. Ogni testo, dal sito alle note
di rilascio, parte da questo taglio: niente toni da prodotto premium.

## Capabilities and Constraints

- Mac: macOS 14.4 o successivo, Apple Silicon e Intel. App non notarizzata: al primo avvio macOS la blocca
  e serve «Apri comunque» in Impostazioni di Sistema → Privacy e sicurezza. Due permessi: Microfono,
  Registrazione audio di sistema. Download solo da GitHub Releases.
- Trascrizione sul Mac, solo con macOS 26: righe «Tu» e «Altri» dalle due tracce, file Markdown accanto
  all'audio.
- Windows (beta): Windows 10 e 11, installer per utente senza permessi di amministratore. L'installer non
  è firmato: SmartScreen chiede «Ulteriori informazioni → Esegui comunque». Niente trascrizione.
- Telefoni esclusi: iOS non dà l'audio delle chiamate, Android lo blocca dalla 10.
- Nessun aggiornamento automatico. Il menu scarica un feed firmato ECDSA P-256 da GitHub Pages, verifica
  la firma e apre la pagina della release. Non esiste Sparkle, Velopack UpdateManager o installazione
  automatica.
- Nessun feedback server: il pulsante apre una issue pubblica su GitHub nel browser.
- Dati che partono: nessuno in background. Solo il controllo manuale delle release su GitHub e
  l'apertura di una issue. Nessuna telemetria, analytics, cookie o identificativo di installazione.
  Le pagine privacy e `llms.txt` devono restare allineate.

## Evidence on Hand

Icona dell'app (`build/icon.png`), screenshot in `site/img/`. Non ci sono statistiche di utilizzo o
telemetria: non inventare numeri di utenti, download o avvii.

## Product Principles

- Chi installa non deve sapere cos'è un DMG: ogni passo dice cosa vedrà sullo schermo.
- Onestà sul blocco di macOS: lo si spiega prima che spaventi.
- La privacy è un fatto: registrazioni e trascrizioni restano sul computer, e l'app non apre connessioni
  in background.

## Accessibility & Inclusion

Pubblico anche anziano o poco pratico: testo grande, contrasto alto, passi numerati, niente gergo.
[Inferito]
