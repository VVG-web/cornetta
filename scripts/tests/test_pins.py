"""GitHub Actions must stay pinned to a full commit SHA.

  python3 -m unittest discover -s scripts/tests
An action reference such as `actions/checkout@v7` follows whatever the tag
points to later. A full 40-character SHA is immutable.
"""
import os
import re
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("CORNETTA_REPO", os.path.abspath(os.path.join(HERE, "..", "..")))


def tracked_workflows():
    result = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True)
    files = [name for name in result.stdout.split() if name.startswith(".github/workflows/") and name.endswith((".yml", ".yaml"))]
    if not files:
        root = os.path.join(REPO, ".github", "workflows")
        if os.path.isdir(root):
            files = [os.path.join(".github", "workflows", name) for name in os.listdir(root) if name.endswith((".yml", ".yaml"))]
    for name in files:
        path = os.path.join(REPO, name)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                yield name, handle.read()


class PinTests(unittest.TestCase):
    def test_every_action_is_pinned_to_a_commit_sha(self):
        uses = []
        for _, text in tracked_workflows():
            uses.extend(re.findall(r"uses:\s*([^\s#]+)", text))
        self.assertTrue(uses, "no GitHub Action references found")
        for reference in uses:
            if reference.startswith("./"):
                continue
            self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}$", f"action not pinned to a SHA: {reference}")


if __name__ == "__main__":
    unittest.main()
