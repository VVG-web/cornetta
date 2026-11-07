"""Guard the fork's privacy boundary.

  python3 -m unittest discover -s scripts/tests

This is intentionally a source-level guard, not a replacement for the functional tests.
It catches accidental reintroduction of the upstream telemetry, feedback, analytics, update-feed
and deployment components after they were removed.
"""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
FORBIDDEN_HOSTS = (
    "cornetta.stellakamikaze.org",
    "analytics.stellakamikaze.org",
    "api.telegram.org",
)
FORBIDDEN_ENDPOINTS = (
    "/api/feedback",
    "/api/t",
    "/api/e",
    "/js/p.js",
    "validateTelemetry",
    "SUFeedURL",
    "SUPublicEDKey",
    "UpdateFeedPublicKey",
    "FeedSignature",
    "TELEGRAM_TOKEN",
)
FORBIDDEN_FILES = (
    "Sources/Cornetta/Telemetry.swift",
    "Sources/CornettaCore/TelemetryFields.swift",
    "windows/src/Cornetta.App/Telemetry.cs",
    "windows/src/Cornetta.Core/TelemetryPayload.cs",
    "windows/src/Cornetta.Core/FeedbackPayload.cs",
    "windows/src/Cornetta.Core/FeedSignature.cs",
    "windows/src/Cornetta.App/FeedbackForm.cs",
    "worker/src/index.js",
    "worker/wrangler.toml",
    "scripts/deploy-site.sh",
    "scripts/release.sh",
    "scripts/feedback.py",
    "scripts/telemetria.py",
    "windows/tools/publish.sh",
    "windows/tools/sign-feed.py",
)
TEXT_SUFFIXES = (".swift", ".cs", ".js", ".json", ".html", ".css", ".txt", ".md", ".yml", ".yaml", ".sh", ".py", ".plist", ".toml")


def tracked_files():
    result = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    return [path for path in result.stdout.splitlines() if path]


class PrivacyGuardTests(unittest.TestCase):
    def test_removed_runtime_components_stay_removed(self):
        for path in FORBIDDEN_FILES:
            self.assertFalse((ROOT / path).exists(), f"removed component came back: {path}")

    def test_no_upstream_hosts_or_api_endpoints(self):
        problems = []
        for name in tracked_files():
            path = ROOT / name
            if name == str(SELF.relative_to(ROOT)) or not path.is_file():
                continue
            if path.suffix not in TEXT_SUFFIXES and path.name not in ("Info.plist",):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for needle in FORBIDDEN_HOSTS + FORBIDDEN_ENDPOINTS:
                if needle in text:
                    problems.append(f"{name}: {needle}")
        self.assertEqual(problems, [], "\n".join(problems))

    def test_apps_have_only_the_manual_github_check(self):
        mac = (ROOT / "Sources/Cornetta/UpdateManager.swift").read_text(encoding="utf-8")
        mac_info = (ROOT / "Sources/Cornetta/AppInfo.swift").read_text(encoding="utf-8")
        win = (ROOT / "windows/src/Cornetta.App/Updates.cs").read_text(encoding="utf-8")
        win_info = (ROOT / "windows/src/Cornetta.App/AppInfo.cs").read_text(encoding="utf-8")
        for text in (mac_info, win_info):
            self.assertIn("api.github.com/repos/", text)
            self.assertIn("VVG-web/cornetta-en", text)
        for text in (mac, win):
            self.assertNotIn("SUScheduledCheckInterval", text)
            self.assertNotIn("Velopack", text)
        self.assertIn("UseCookies = false", win)

    def test_macos_bundle_has_no_update_feed_metadata(self):
        plist = (ROOT / "Resources/Info.plist").read_text(encoding="utf-8")
        self.assertNotIn("SUFeedURL", plist)
        self.assertNotIn("SUPublicEDKey", plist)
        self.assertNotIn("SUEnableAutomaticChecks", plist)

    def test_static_site_has_no_analytics_or_download_api(self):
        pages = [ROOT / "site/index.html", ROOT / "site/en/index.html",
                 ROOT / "site/privacy/index.html", ROOT / "site/en/privacy/index.html"]
        for page in pages:
            text = page.read_text(encoding="utf-8")
            self.assertNotIn("js/p.js", text)
            self.assertNotIn("data-api", text)
            self.assertIn("github.com/VVG-web/cornetta-en/releases/latest", text)

    def test_privacy_pages_state_the_boundary(self):
        italian = (ROOT / "site/privacy/index.html").read_text(encoding="utf-8")
        english = (ROOT / "site/en/privacy/index.html").read_text(encoding="utf-8")
        for text in (italian, english):
            self.assertIn("GitHub", text)
        self.assertIn("Nessuna telemetria", italian)
        self.assertIn("No telemetry", english)

    def test_no_telemetry_switch_in_localization(self):
        catalog = (ROOT / "localization/strings.json").read_text(encoding="utf-8")
        self.assertNotIn("menu.telemetry", catalog)
        self.assertNotIn("Send usage data", catalog)


if __name__ == "__main__":
    unittest.main()
