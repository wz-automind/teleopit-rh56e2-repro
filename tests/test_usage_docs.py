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

    def test_guides_show_upstream_commands_before_e2_extensions(self):
        required = (
            "python scripts/run/run_sim.py",
            "--config-name pico4_sim",
            "python scripts/run/run_sim_rh56e2.py",
            "--config-name pico4_sim_rh56e2",
            "python scripts/run/run_sim2real.py",
            "--config-name pico4_sim2real",
            "--config-name pico4_sim2real_rh56e2",
            "hands.rh56e2.left_host=192.168.11.210",
            "hands.rh56e2.right_host=192.168.11.211",
        )
        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            for fragment in required:
                with self.subTest(path=path.name, fragment=fragment):
                    self.assertIn(fragment, text)
            self.assertLess(
                text.index("python scripts/run/run_sim.py"),
                text.index("python scripts/run/run_sim_rh56e2.py"),
            )
            self.assertLess(
                text.index("--config-name pico4_sim2real \\"),
                text.index("--config-name pico4_sim2real_rh56e2"),
            )

    def test_default_workflow_does_not_require_path_exports(self):
        forbidden = (
            'export REPRO_DIR="$PWD"',
            'export TELEOPIT_DIR="$HOME/Teleopit"',
            'export SOMEHAND_DIR="$TELEOPIT_DIR/third_party/somehand"',
        )
        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            for fragment in forbidden:
                with self.subTest(path=path.name, fragment=fragment):
                    self.assertNotIn(fragment, text)


if __name__ == "__main__":
    unittest.main()

