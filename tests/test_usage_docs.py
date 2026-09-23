import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCS = (ROOT / "docs" / "USAGE.zh-CN.md", ROOT / "docs" / "USAGE.en.md")
QUICK_GUIDE = ROOT / "docs" / "安装与运行.md"


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

    def test_robot_host_commands_match_the_unitree_deployment(self):
        required = (
            "source /home/unitree/miniforge3/bin/activate teleopit",
            "cd /home/unitree/Teleopit",
            "# Whole-body teleoperation (without dexterous hands)",
            "# Whole-body teleoperation (with dual RH56E2 hands)",
            "hands.rh56e2.write_enabled=true",
        )
        chinese_required = (
            "# 全身遥操启动指令（不包含灵巧手）",
            "# 全身遥操启动指令（包含左右 E2）",
            "不能同时运行",
        )
        english_required = ("must not run at the same time",)

        english = DOCS[1].read_text(encoding="utf-8")
        chinese = DOCS[0].read_text(encoding="utf-8")
        for fragment in required:
            with self.subTest(language="en", fragment=fragment):
                self.assertIn(fragment, english)
        for fragment in required[:2] + required[4:]:
            with self.subTest(language="zh", fragment=fragment):
                self.assertIn(fragment, chinese)
        for fragment in chinese_required:
            self.assertIn(fragment, chinese)
        for fragment in english_required:
            self.assertIn(fragment, english)

        for text in (english, chinese):
            base_index = text.index("--config-name pico4_sim2real ")
            e2_index = text.index("--config-name pico4_sim2real_rh56e2 ")
            self.assertLess(base_index, e2_index)
            for stale_interface in (
                "real_robot.network_interface=eth0",
                "NETWORK_INTERFACE=eth0",
                "--network-interface eth0",
            ):
                self.assertNotIn(stale_interface, text)

    def test_chinese_quick_guide_points_to_current_commands(self):
        text = QUICK_GUIDE.read_text(encoding="utf-8")
        required = (
            "[完整中文使用手册](USAGE.zh-CN.md)",
            "scripts/setup/install.sh",
            "scripts/run/run_sim_rh56e2.py",
            "source /home/unitree/miniforge3/bin/activate teleopit",
            "cd /home/unitree/Teleopit",
            "--config-name pico4_sim2real ",
            "--config-name pico4_sim2real_rh56e2 ",
            "real_robot.network_interface=eth1",
            "hands.rh56e2.write_enabled=true",
            "不能同时运行",
        )
        forbidden = (
            "NETWORK_INTERFACE=eth0",
            "bash scripts/install.sh",
            "bash scripts/run_real.sh",
            "9 项 Modbus/映射单元测试",
        )
        for fragment in required:
            with self.subTest(required=fragment):
                self.assertIn(fragment, text)
        for fragment in forbidden:
            with self.subTest(forbidden=fragment):
                self.assertNotIn(fragment, text)

    def test_operator_docs_use_one_miniforge_environment(self):
        paths = (ROOT / "README.md", QUICK_GUIDE, *DOCS)
        required = (
            "source /home/unitree/miniforge3/bin/activate teleopit",
            "conda create -n teleopit python=3.11",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn(".venv", text)
                for fragment in required:
                    self.assertIn(fragment, text)


if __name__ == "__main__":
    unittest.main()
