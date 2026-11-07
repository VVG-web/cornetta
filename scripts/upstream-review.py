#!/usr/bin/env python3
"""Produce a selective upstream review report for the fork.

The report is advisory only. It never merges, cherry-picks, pushes, or executes upstream code.
Upstream commit messages and paths are untrusted data and are rendered inside code blocks.
"""
import argparse
import re
import subprocess
import sys

SENSITIVE = re.compile(
    r"(telemetry|feedback|privacy|plausible|telegram|cloudflare|worker/|wrangler|d1|kv|"
    r"sparkle|velopack|update|appcast|feed|site/update|analytics|crash|sentry|"
    r"Info\.plist|AppInfo|entitlements)",
    re.IGNORECASE,
)
CORE = re.compile(
    r"(CallRecorder|RecordingFinalizer|Mixer|AudioRouting|CallDetector|ScreenRecorder|"
    r"ScreenAudio|ScreenEncoding|Transcript|VoiceActivity|VoiceLeveler|TapSilence|"
    r"RecorderModel|SpeechEngine|Library|FileNaming|WorkingRecording|RecordingPipeline|"
    r"PathPrivacy|windows/src/Cornetta\.Core/|windows/src/Cornetta\.App/(Recorder|Audio|"
    r"Recording|Overlay|TrayApp|Call))",
    re.IGNORECASE,
)
UI = re.compile(r"(localization/|\.lproj|site/(index|en|privacy|assets)|README|PRODUCT|DESIGN|docs/)", re.IGNORECASE)
MAX_FILES = 200
MAX_COMMITS = 100
MAX_LINE = 300


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def clean(text: str) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = text.replace("\r", " ").replace("\n", " ")
    return text[:MAX_LINE]


def clean_block(text: str, max_lines: int = MAX_COMMITS) -> str:
    lines = [clean(line) for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:max_lines])


def classify(path: str) -> str:
    if SENSITIVE.search(path):
        return "privacy/network"
    if CORE.search(path):
        return "core"
    if UI.search(path):
        return "ui/docs"
    return "other"


def categories(files: list[tuple[str, str]]) -> dict[str, list[tuple[str, str]]]:
    grouped = {"core": [], "privacy/network": [], "ui/docs": [], "other": []}
    for status, path in files:
        grouped[classify(path)].append((status, path))
    return grouped


def render_report(base: str, upstream: str, commits: str, files: list[tuple[str, str]], stat: str) -> str:
    lines = [
        "# Upstream review",
        "",
        "This is an advisory report. Nothing is merged or cherry-picked automatically.",
        "Upstream text is shown as untrusted data inside code blocks.",
        "",
        f"- Fork base: `{base}`",
        f"- Upstream: `{upstream}`",
        f"- Changed files: {len(files)}",
        "",
    ]
    if not commits.strip():
        lines += ["No new upstream commits.", ""]
    else:
        lines += ["## Commits", "", "```text", clean_block(commits), "```", ""]
    if stat.strip():
        lines += ["## Diff stat", "", "```text", clean_block(stat, MAX_FILES), "```", ""]

    grouped = categories(files)
    guidance = {
        "core": "Candidates for a focused port after regression tests and real capture checks.",
        "privacy/network": "Do not port automatically. Review against the fork privacy boundary; most of this is intentionally absent.",
        "ui/docs": "Review identity, localization, privacy wording, and GitHub Pages paths before porting.",
        "other": "Review manually; no automatic recommendation.",
    }
    for key in ("core", "privacy/network", "ui/docs", "other"):
        entries = grouped[key]
        if not entries:
            continue
        lines += [f"## {key}", "", guidance[key], "", "```text"]
        for status, path in entries[:MAX_FILES]:
            lines.append(f"{clean(status):2} {clean(path)}")
        if len(entries) > MAX_FILES:
            lines.append(f"... {len(entries) - MAX_FILES} more")
        lines += ["```", ""]

    lines += [
        "## Recommended next step",
        "",
        "1. Identify a test-backed core fix or behavior improvement.",
        "2. Port it in a separate commit, never as a bulk upstream merge.",
        "3. Reject telemetry, analytics, feedback-server, and automatic-update changes.",
        "4. Run `./scripts/check.sh` and the relevant real capture check.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--upstream-ref", default="upstream/master")
    options = parser.parse_args()

    try:
        base = git("rev-parse", "--short", options.base).strip()
        upstream = git("rev-parse", "--short", options.upstream_ref).strip()
        log = git("log", "--reverse", f"--max-count={MAX_COMMITS}", "--date=short",
                  "--format=%h %ad %an: %s", f"{options.base}..{options.upstream_ref}")
        raw_files = git("diff", "--name-status", f"{options.base}...{options.upstream_ref}")
        stat = git("diff", "--stat", f"{options.base}...{options.upstream_ref}")
    except RuntimeError as error:
        sys.exit(f"upstream-review: {error}")

    files = []
    for line in raw_files.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            files.append((parts[0], parts[-1]))
    print(render_report(base, upstream, log, files, stat))


if __name__ == "__main__":
    main()
