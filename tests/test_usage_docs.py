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
            "scripts/setup/install.sh",
            "scripts/dev/validate.sh",
            "scripts/dev/check_rh56e2.py",
            "scripts/dev/bench_rh56e2.py",
            "scripts/run/standalone_standing.py",
            "scripts/run/run_sim2real_rh56e2.sh",
            "teleopit/configs/pico4_sim_rh56e2.yaml",
            "MOVE_RH56E2",
            "ENABLE_G1_REAL=YES",
            "ENABLE_RH56E2_WRITES=YES",
        )
        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            for fragment in required:
                with self.subTest(path=path.name, fragment=fragment):
                    self.assertIn(fragment, text)

    def test_both_guides_document_live_simulation_operation(self):
        required = (
            "scripts/run/run_sim_rh56e2.sh",
            "63901",
            "`STANDING`",
            "`MOCAP`",
            "`Y`",
            "`B`",
            "`A`",
            "`X`",
            "`Q`",
            "policy_hz: 50",
            "pd_hz: 200",
        )
        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            for fragment in required:
                with self.subTest(path=path.name, fragment=fragment):
                    self.assertIn(fragment, text)

    def test_readme_links_both_guides(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/USAGE.en.md", readme)
        self.assertIn("docs/USAGE.zh-CN.md", readme)
        self.assertIn("docs/en/README.md", readme)
        self.assertIn("docs/zh/README.md", readme)

    def test_reference_document_trees_are_mirrored(self):
        english = {
            path.relative_to(ROOT / "docs" / "en").as_posix()
            for path in (ROOT / "docs" / "en").rglob("*.md")
        }
        chinese = {
            path.relative_to(ROOT / "docs" / "zh").as_posix()
            for path in (ROOT / "docs" / "zh").rglob("*.md")
        }
        self.assertEqual(english, chinese)


if __name__ == "__main__":
    unittest.main()
