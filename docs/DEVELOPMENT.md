# Development environment

## Source provenance

The original Cornetta project is `https://github.com/stellakamikaze/cornetta` and remains the canonical
upstream. This repository is the privacy-clean fork `VVG-web/cornetta-en`. At setup, both `master` branches
pointed to commit `af48825261415a5d1422916c706bacb1e9b2c0d0` (`v0.4.0`).

Review future upstream changes before executing downloaded scripts or dependencies:

```bash
git fetch upstream --tags
git log --oneline HEAD..upstream/master
git diff --stat HEAD..upstream/master
```

This fork intentionally does not contain the upstream Cloudflare Worker, telemetry, feedback service,
Plausible/Telegram integrations, Sparkle/Velopack automatic updates, or production deployment scripts.

## Required tools

- Full Xcode or Xcode Command Line Tools with Swift 5.10 or newer.
- .NET SDK 10, selected by `windows/global.json`.
- Python 3 for scripts and browser tests.
- ShellCheck 0.11.0, SwiftLint 0.65.1, SwiftFormat 0.64.1 or compatible newer versions.
- FFmpeg and ffprobe for inspecting real recordings.

The verified local binaries were obtained from the official repositories `koalaman/shellcheck`,
`realm/SwiftLint`, and `nicklockwood/SwiftFormat`. Their release archives were checked against the
SHA-256 digests published by the GitHub API. Keep these tools in a user-writable directory on `PATH`,
such as `~/.local/bin`; no administrator installation is needed.

## Browser test setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

The smoke test uses an installed Google Chrome, Chromium, or Edge automatically. Only if none is
available, install Playwright's browser without deleting other versions:

```bash
.venv/bin/python -m playwright install chromium --no-remove
```

Set `CORNETTA_CHROMIUM=/absolute/path/to/chromium` to override browser discovery.

## Full local gate

```bash
./scripts/check.sh
```

It runs ShellCheck, the localization catalog checks, SwiftLint, SwiftFormat, macOS tests, a universal
DMG build that is mounted and inspected for both architectures and signature validity, cross-platform
.NET tests and Release compilation, Python script tests, isolated browser smoke tests against the static
`site/`, and `git diff --check`.

It does not deploy, push, release, access production data, or use signing keys.

For an environment without any browser, `CORNETTA_SKIP_BROWSER=1 ./scripts/check.sh` runs the remaining
checks. This is an explicit exception, not a substitute for the full gate when a browser is available.

## Privacy boundary

The app must not open background connections. The only allowed network actions are:

- a user-triggered GitHub release check in `Sources/Cornetta/UpdateManager.swift` and
  `windows/src/Cornetta.App/Updates.cs`;
- opening GitHub Issues in the browser when the user chooses Feedback;
- system services such as Apple speech model downloads, which are outside app code.

Do not add telemetry, analytics, crash reporting, ad SDKs, a feedback server, or an automatic updater.
`python3 -m unittest discover -s scripts/tests -p 'test_privacy_guard.py'` checks that the old endpoints
and components stay gone. Any new outbound request must be opt-in, documented in both privacy pages, and
covered by a test.

## Real application checks

Unit tests do not cover microphones, system audio permissions, ScreenCaptureKit, transcription on
macOS 26, Windows WASAPI, tray startup, or installer behavior. Use the existing headless modes when
changing those areas:

```bash
open -W -n build/Cornetta.app --args --record 10 --out /tmp/prova.m4a --debug-tracks /tmp/prova
open -n build/Cornetta.app --args --record-screen 30 --out esito.json
open -W -n build/Cornetta.app --args --probe /tmp/sonda.txt
build/Cornetta.app/Contents/MacOS/Cornetta --transcribe file.m4a
python3 site-src/make-demo-library.py /tmp/demo
open -n build/Cornetta.app --args --demo-library /tmp/demo
```

Run real recording tests only with permission to capture the selected audio and screen. Windows changes
also require the existing Windows CI and preferably a real Windows 10/11 machine for `--selftest`,
`--render-ui`, `--smoke-tray`, and a real recording.

## Interface localization

The single source of truth is `localization/strings.json`. Each entry has an identifier and both
Italian and English text. Run:

```bash
scripts/localization.py          # regenerate Swift, C# and .lproj catalogs
scripts/localization.py --check  # fail if generated files are stale
```

Generated files are committed: `LocalizedStrings.generated.swift`,
`LocalizedStrings.generated.cs`, and the `Localizable.strings` files under
`Sources/Cornetta/Resources/`. Never edit generated files directly.

The automated tests reject missing translations, mismatched placeholders, and UI literals that are not
represented in the catalog. A new interface string therefore requires an Italian and an English entry
before the gate can pass.

The saved key is `appLanguage` (`it` or `en`). New installs choose English when the first supported
system language is English and Italian otherwise. Existing installs remain Italian until the user
chooses another language. This choice is independent from the speech-recognition language.

## Releases

There is no automatic updater and no production deployment script. Build and verify locally, then create
a GitHub Release manually with the DMG or Windows installer. Users check for updates from the app menu
and download from the GitHub Release page. Record SHA-256 fingerprints in the release notes.
