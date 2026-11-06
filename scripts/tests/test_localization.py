"""Completeness checks for the Italian/English interface catalog."""

import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "localization" / "strings.json"

SWIFT_UI = re.compile(
    r'\b(?:Text|Button|Toggle|Label|Menu|TextField|Picker|DisclosureGroup|ContentUnavailableView)'
    r'\(\s*"((?:\\.|[^"\\])*)"'
)
SWIFT_MODIFIER = re.compile(r'\.(?:help|accessibilityLabel)\(\s*"((?:\\.|[^"\\])*)"')
SWIFT_WINDOW_OR_ALERT = re.compile(
    r'(?:\.title|\.messageText|\.informativeText)\s*=\s*"((?:\\.|[^"\\])*)"'
)
SWIFT_ALERT_BUTTON = re.compile(r'\.addButton\(withTitle:\s*"((?:\\.|[^"\\])*)"')
CSHARP_TEXT = re.compile(r'\.(?:Text|AccessibleName)\s*=\s*"((?:\\.|[^"\\])*)"')
CSHARP_HELPER = re.compile(
    r'(?:\bAdd|\bInfo|WrapLabel|SetToolTip|SetCue|new PanelButton)\([^\n]*?"((?:\\.|[^"\\])*)"'
)

# Purely structural strings are not interface copy.
SWIFT_ALLOWED = {'·'}
CSHARP_ALLOWED = {'Cornetta'}
CSHARP_CALLS = [
    re.compile(r'(?<!\.)\bAdd\(\s*"((?:\\.|[^"\\])*)"'),
    re.compile(r'(?<!\.)\bInfo\(\s*"((?:\\.|[^"\\])*)"'),
    re.compile(r'\bWrapLabel\(\s*"((?:\\.|[^"\\])*)"'),
    re.compile(r'SetToolTip\([^,]+,\s*"((?:\\.|[^"\\])*)"'),
    re.compile(r'\bSetCue\([^,]+,\s*"((?:\\.|[^"\\])*)"'),
    re.compile(r'new PanelButton\(\s*"((?:\\.|[^"\\])*)"'),
]


def catalog_values() -> set[str]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))["strings"]
    return {entry["it"] for entry in data.values()} | {entry["en"] for entry in data.values()}


def missing_csharp_literals(values: set[str]) -> list[str]:
    missing = []
    for path in (ROOT / "windows" / "src" / "Cornetta.App").glob("*.cs"):
        if path.name.endswith(".generated.cs"):
            continue
        missing.extend(missing_csharp_file(path, values))
    return missing


def missing_csharp_file(path: Path, values: set[str]) -> list[str]:
    missing = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or "Diagnostics.Log" in line:
            continue
        for pattern in (CSHARP_TEXT, *CSHARP_CALLS):
            for literal in pattern.findall(line):
                if (literal not in values and literal not in CSHARP_ALLOWED
                        and literal not in ("", "⚠ ") and not literal.startswith("Cornetta ")):
                    missing.append(f"{path.relative_to(ROOT)}: {literal}")
    return missing


class LocalizationTests(unittest.TestCase):
    def test_generated_catalogs_are_current(self):
        result = subprocess.run([str(ROOT / "scripts" / "localization.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_swift_ui_literals_are_catalogued(self):
        values = catalog_values()
        missing = []
        for path in (ROOT / "Sources" / "Cornetta").rglob("*.swift"):
            text = path.read_text(encoding="utf-8")
            for pattern in (SWIFT_UI, SWIFT_MODIFIER, SWIFT_WINDOW_OR_ALERT, SWIFT_ALERT_BUTTON):
                for literal in pattern.findall(text):
                    if (literal not in values and literal not in SWIFT_ALLOWED
                            and "number" not in literal):
                        missing.append(f"{path.relative_to(ROOT)}: {literal}")
        self.assertEqual(missing, [], "UI strings missing from localization/strings.json:\n" + "\n".join(missing))

    def test_language_controls_are_present_on_both_platforms(self):
        mac = (ROOT / "Sources" / "Cornetta" / "CornettaApp.swift").read_text(encoding="utf-8")
        windows = (ROOT / "windows" / "src" / "Cornetta.App" / "TrayApp.cs").read_text(encoding="utf-8")
        self.assertIn("Picker(localization.text(.menuLanguage)", mac)
        self.assertIn("L10nKey.MenuLanguage", windows)
        self.assertIn("AppLanguageSettings.Select(language)", windows)

    def test_info_plist_strings_have_the_same_keys(self):
        def keys(path: Path) -> set[str]:
            text = path.read_text(encoding="utf-8")
            matches = re.findall(r'^"([^"]+)"\s*=\s*"([^"]+)";', text, re.MULTILINE)
            self.assertTrue(matches, f"No localized entries in {path}")
            self.assertTrue(all(value.strip() for _, value in matches), f"Empty value in {path}")
            return {key for key, _ in matches}
        italian = keys(ROOT / "Sources" / "Cornetta" / "Resources" / "it.lproj" / "InfoPlist.strings")
        english = keys(ROOT / "Sources" / "Cornetta" / "Resources" / "en.lproj" / "InfoPlist.strings")
        self.assertEqual(italian, english)

    def test_windows_ui_literals_are_catalogued(self):
        missing = missing_csharp_literals(catalog_values())
        self.assertEqual(missing, [], "UI strings missing from localization/strings.json:\n" + "\n".join(missing))


if __name__ == "__main__":
    unittest.main()
