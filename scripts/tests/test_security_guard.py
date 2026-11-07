"""Static guards for macOS privilege, drivers, persistence, and cleanup.

These tests do not replace the real Intel audit. They prevent a future change from
quietly adding a privileged helper, a kernel/system extension, or a system-wide login item.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAFE_SERVICE_MANAGEMENT = "SMAppService.mainApp"
FORBIDDEN = {
    "SMJobBless": "privileged helper",
    "AuthorizationExecuteWithPrivileges": "privileged execution",
    "AuthorizationCreate": "authorization API",
    "NSTask": "subprocess execution",
    "osascript": "AppleScript execution",
    "kextload": "kernel extension loading",
    "kextutil": "kernel extension loading",
    "/Library/LaunchDaemons": "system daemon",
    "/Library/LaunchAgents": "system login agent",
    "/System/Library": "system modification",
    "OSSystemExtension": "system extension",
    "SystemExtensionRequest": "system extension",
    "com.apple.security.cs.disable-library-validation": "hardened runtime weakening",
    "com.apple.security.cs.allow-jit": "hardened runtime weakening",
    "com.apple.security.get-task-allow": "debug entitlement",
}


def text_files():
    for folder in ("Sources", "Sources/CornettaCore"):
        path = ROOT / folder
        if not path.exists():
            continue
        for file in path.rglob("*"):
            if file.suffix in (".swift", ".plist", ".entitlements"):
                yield file


class MacSecurityGuardTests(unittest.TestCase):
    def test_no_privileged_or_system_level_code(self):
        problems = []
        for file in text_files():
            text = file.read_text(encoding="utf-8", errors="replace")
            for needle, reason in FORBIDDEN.items():
                if needle in text:
                    problems.append(f"{file.relative_to(ROOT)}: {needle} ({reason})")
        self.assertEqual(problems, [], "\n".join(problems))

    def test_login_item_is_only_the_main_app(self):
        text = (ROOT / "Sources/Cornetta/Welcome.swift").read_text(encoding="utf-8")
        if "SMAppService" in text:
            self.assertIn(SAFE_SERVICE_MANAGEMENT, text)
            self.assertNotIn("SMAppService.daemon", text)
            self.assertNotIn("SMAppService.agent", text)
            self.assertIn("unregister()", text)

    def test_audio_aggregate_is_private_and_destroyed(self):
        text = (ROOT / "Sources/CornettaCore/AggregateDevice.swift").read_text(encoding="utf-8")
        self.assertIn("kAudioAggregateDeviceIsPrivateKey: true", text)
        self.assertIn("kAudioAggregateDeviceTapAutoStartKey: false", text)
        self.assertIn("AudioHardwareDestroyAggregateDevice", text)
        recorder = (ROOT / "Sources/CornettaCore/CallRecorder.swift").read_text(encoding="utf-8")
        self.assertIn("aggregate?.destroy()", recorder)
        self.assertIn("tap?.destroy()", recorder)

    def test_no_system_wide_installer_or_receipts(self):
        text = (ROOT / "Sources/CornettaCore/AppInstaller.swift").read_text(encoding="utf-8")
        self.assertNotIn("/System", text)
        self.assertNotIn("/Library", text)
        self.assertIn("replaceItemAt", text)

    def test_entitlements_are_audio_only(self):
        text = (ROOT / "Resources/Cornetta.entitlements").read_text(encoding="utf-8")
        keys = set(re.findall(r"<key>([^<]+)</key>", text))
        self.assertEqual({"com.apple.security.device.audio-input"}, keys)


if __name__ == "__main__":
    unittest.main()
