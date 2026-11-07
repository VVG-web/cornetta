---
name: cornetta
description: Develop, debug, and verify the privacy-clean Cornetta fork across Swift/Core Audio, Windows C#, audio/video capture, local transcription, manual GitHub updates, and its static website. Use whenever working in this repository on recording reliability, platform behavior, privacy, localization, or UI changes.
compatibility: Full verification requires macOS with Xcode, .NET 10, Python 3, and a Chromium browser. Native audio and Windows checks require their respective platforms.
---

# Cornetta

## Establish context

1. Read `CLAUDE.md` and `docs/DEVELOPMENT.md` before editing.
2. Read `PRODUCT.md` for product behavior and `DESIGN.md` before UI work.
3. Keep interface text and code comments in Italian unless the user requests another language.
4. This is the privacy-clean fork `VVG-web/cornetta-en`, based on `stellakamikaze/cornetta`.
   Do not reintroduce the upstream Worker, telemetry, feedback service, Plausible, Telegram,
   Sparkle/Velopack auto-updates, or production deployment scripts.

## Make changes safely

- Start with a focused reproduction and the smallest responsible change.
- Preserve the privacy boundary: no background network connections, no telemetry, no analytics.
  The only network actions are the user-triggered signed update feed and opening a GitHub issue.
- Audio, transcripts, file names, device names, contacts and diagnostics must never be uploaded.
- Keep local-first behavior: recordings and transcripts stay in the user's folders.
- Update `site/privacy/index.html`, `site/en/privacy/index.html`, and `site/llms.txt` before adding any
  outbound request.
- Treat `site/update/feed.json` as signed data: never edit it without re-signing with
  `scripts/sign-feed.py`, and never commit the private key.
- Keep existing public formats compatible: transcript JSON uses `Transcript.decoder`.
- Put every user-facing string in `localization/strings.json`, run `scripts/localization.py`, and keep
  both Italian and English complete.
- Do not add signing keys, update feeds, deployment workflows, or release automation as a side effect.

## Verify changes

Run focused tests first, then require a green `./scripts/check.sh`. The gate covers macOS tests and a
mounted universal DMG, cross-platform .NET tests and Release build, Python script and privacy tests,
linting, and isolated browser smoke tests against the static `site/`. It never deploys or accesses
production data.

For capture changes, unit tests are insufficient. Select the relevant real check:

- `--record` with `--debug-tracks` for microphone/system audio and synchronization.
- `--record-screen` for video, audio tracks, fragmentation, and final merge behavior.
- `--probe` for Core Audio routing failures.
- `--transcribe` for transcription and `--demo-library` for library UI.
- Windows CI plus `--selftest`, `--render-ui`, and `--smoke-tray` for Windows changes.

Test transcription on macOS 26 or newer. Test Windows WASAPI and installer behavior on real Windows when
possible, and state any unverified platform coverage plainly.

## Respect platform lessons

- With full Xcode, do not inject Command Line Tools Testing frameworks into `scripts/test.sh`; use the
  CLT overrides only when CLT is selected.
- Do not copy another machine's `SDKROOT` workaround without reproducing its SDK error.
- Use a frame-count keyframe interval for HEVC. Some macOS 15 installations reject
  `AVVideoMaxKeyFrameIntervalDurationKey` even when `canApply` returns true.
- Do not set `kAudioAggregateDeviceTapAutoStartKey` to true.
- Do not open a window directly in `applicationDidFinishLaunching` of the menu bar app.
- Do not re-add an automatic updater. The GitHub check is manual by design.
