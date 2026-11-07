"""The committed update feed must be signed by the embedded public key.

  python3 -m unittest discover -s scripts/tests
"""
import base64
import json
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FEED = ROOT / "site" / "update" / "feed.json"
SIGNATURE = ROOT / "site" / "update" / "feed.json.sig"
SIGN = ROOT / "scripts" / "sign-feed.py"
PUBLIC_KEY = "BCcSn9flFlqQeVWQqoM9iFr8xKhtsy5juX9CJO70Or3aPgQVJyZOfnWeJTTYImxkxm9U20bgDWVqM5BO/NNvi60="


class UpdateFeedTests(unittest.TestCase):
    def test_public_key_has_the_expected_shape(self):
        point = base64.b64decode(PUBLIC_KEY, validate=True)
        self.assertEqual(65, len(point))
        self.assertEqual(0x04, point[0])

    def test_feed_is_valid_json_and_mentions_a_matching_release(self):
        feed = json.loads(FEED.read_text(encoding="utf-8"))
        self.assertEqual(1, feed["schema"])
        self.assertRegex(feed["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(f"https://github.com/VVG-web/cornetta-en/releases/tag/v{feed['version']}",
                         feed["release_url"])
        self.assertRegex(feed["mac"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(feed["windows"]["sha256"], r"^[0-9a-f]{64}$")

    def test_signature_verifies(self):
        result = subprocess.run(
            ["python3", str(SIGN), "--verify", str(FEED), str(SIGNATURE),
             "--public-key-base64", PUBLIC_KEY],
            capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()
