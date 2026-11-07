"""The update feed signing tool must round-trip and reject tampering.

  python3 -m unittest discover -s scripts/tests
Keys are generated in a temporary directory with openssl and never enter the repository.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SIGN = ROOT / "scripts" / "sign-feed.py"


class SignFeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.key = self.dir / "feed.pem"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", str(self.key)],
            check=True, capture_output=True,
        )
        self.key.chmod(0o600)
        self.feed = self.dir / "feed.json"
        self.feed.write_bytes(b'{"schema":1,"version":"0.0.0","release_url":"https://github.com/VVG-web/cornetta-en/releases/tag/v0.0.0"}')

    def tearDown(self):
        self.tmp.cleanup()

    def run_sign(self, *args):
        return subprocess.run(
            ["python3", str(SIGN), "--key", str(self.key), *args],
            capture_output=True, text=True, env=dict(os.environ),
        )

    def test_sign_and_verify(self):
        result = self.run_sign("--sign", str(self.feed))
        self.assertEqual(result.returncode, 0, result.stderr)
        signature = self.feed.with_name(self.feed.name + ".sig")
        self.assertTrue(signature.is_file())
        public = self.run_sign("--public-key")
        self.assertEqual(public.returncode, 0, public.stderr)
        key = public.stdout.strip()
        self.assertEqual(len(key), 88)
        self.assertTrue(key.endswith("="))
        verified = self.run_sign("--verify", str(self.feed), str(signature), "--public-key-base64", key)
        self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_changed_feed_is_rejected(self):
        self.assertEqual(self.run_sign("--sign", str(self.feed)).returncode, 0)
        signature = self.feed.with_name(self.feed.name + ".sig")
        public = self.run_sign("--public-key").stdout.strip()
        self.feed.write_bytes(self.feed.read_bytes() + b" ")
        result = self.run_sign("--verify", str(self.feed), str(signature), "--public-key-base64", public)
        self.assertNotEqual(result.returncode, 0)

    def test_bad_key_permissions_are_rejected(self):
        self.key.chmod(0o644)
        result = self.run_sign("--check-key")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
