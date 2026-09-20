import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCS = (ROOT / "docs" / "USAGE.zh-CN.md", ROOT / "docs" / "USAGE.en.md")


class UsageGuideTests(unittest.TestCase):
    def test_guides_have_matching_numbered_structure(self):
        sequences = []
        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            sequences.append([int(value) for value in re.findall(r"^## (\d+)\.", text, re.MULTILINE)])
        self.assertEqual(sequences[0], list(range(1, 20)))
        self.assertEqual(sequences[0], sequences[1])

    def test_both_guides_include_every_safety_entry_point(self):
        required = (
            "scripts/install.sh",
            "scripts/validate.sh",
            "scripts/rh56e2_preflight.py",
            "scripts/rh56e2_bench_test.py",
            "scripts/run/standalone_standing.py",
            "scripts/run_real.sh",
            "MOVE_RH56E2",
            "ENABLE_G1_REAL=YES",
            "ENABLE_RH56E2_WRITES=YES",
        )
        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            for fragment in required:
                with self.subTest(path=path.name, fragment=fragment):
                    self.assertIn(fragment, text)

    def test_readme_links_both_guides(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/USAGE.zh-CN.md", readme)
        self.assertIn("docs/USAGE.en.md", readme)


if __name__ == "__main__":
    unittest.main()
