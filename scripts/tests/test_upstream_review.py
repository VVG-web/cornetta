"""Upstream review must classify changes and remain advisory.

  python3 -m unittest discover -s scripts/tests
"""
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "upstream-review.py"
spec = importlib.util.spec_from_file_location("upstream_review", SCRIPT)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class UpstreamReviewTests(unittest.TestCase):
    def test_classifies_core_and_privacy(self):
        self.assertEqual("core", review.classify("Sources/CornettaCore/CallRecorder.swift"))
        self.assertEqual("privacy/network", review.classify("Sources/Cornetta/Telemetry.swift"))
        self.assertEqual("privacy/network", review.classify("worker/src/index.js"))
        self.assertEqual("privacy/network", review.classify("site/update/feed.json"))
        self.assertEqual("ui/docs", review.classify("site/index.html"))
        self.assertEqual("ui/docs", review.classify("README.md"))
        self.assertEqual("other", review.classify("LICENSE"))

    def test_report_is_advisory_and_keeps_multiple_commits(self):
        files = [("M", "Sources/CornettaCore/CallRecorder.swift"),
                 ("M", "Sources/Cornetta/Telemetry.swift")]
        report = review.render_report("abc", "def", "111 core fix\n222 telemetry change", files, "2 files changed")
        self.assertIn("Nothing is merged", report)
        self.assertIn("111 core fix", report)
        self.assertIn("222 telemetry change", report)
        self.assertIn("Do not port automatically", report)
        self.assertIn("Candidates for a focused port", report)

    def test_control_characters_are_removed(self):
        self.assertNotIn("\x00", review.clean("a\x00b"))
        self.assertLessEqual(len(review.clean("x" * 1000)), review.MAX_LINE)


if __name__ == "__main__":
    unittest.main()
