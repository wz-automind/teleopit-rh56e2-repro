import re
import unittest
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOCS = (ROOT / "docs" / "zh" / "usage.md", ROOT / "docs" / "en" / "usage.md")
LANGUAGE_ROOTS = (ROOT / "docs" / "en", ROOT / "docs" / "zh")
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


class UsageGuideTests(unittest.TestCase):
    def test_sdk_references_are_mirrored_and_indexed(self):
        english_path = ROOT / "docs" / "en" / "reference" / "sdk.md"
        chinese_path = ROOT / "docs" / "zh" / "reference" / "sdk.md"
        english = english_path.read_text(encoding="utf-8")
        chinese = chinese_path.read_text(encoding="utf-8")
        required = (
            "RH56E2Hand",
            "RH56E2Pair",
            "read_telemetry",
            "set_speed",
            "set_positions",
            "write_enabled=True",
            "192.168.123.210",
            "192.168.123.211",
        )
        for fragment in required:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, english)
                self.assertIn(fragment, chinese)

        for path in (ROOT / "docs" / "en" / "README.md", ROOT / "docs" / "zh" / "README.md"):
            with self.subTest(path=path):
                self.assertIn("reference/sdk.md", path.read_text(encoding="utf-8"))

        root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/en/reference/sdk.md", root_readme)
        self.assertIn("docs/zh/reference/sdk.md", root_readme)

    def test_guides_have_matching_numbered_structure(self):
        sequences = []
        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            sequences.append([int(value) for value in re.findall(r"^## (\d+)\.", text, re.MULTILINE)])
        self.assertEqual(sequences[0], list(range(1, 20)))
        self.assertEqual(sequences[0], sequences[1])

    def test_both_guides_include_every_safety_entry_point(self):
        required = (
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

    def test_both_guides_deploy_full_teleopit_before_integration_overlay(self):
        required = (
            "git archive --format=tar.gz",
            "teleopit-rh56e2-repro-latest.tar.gz",
            "Teleopit-latest.tar.gz",
            "scp",
            "unitree@192.168.50.62:/home/unitree/",
            "tar -xzf",
            "Teleopit-backup-",
            "overlay/teleopit/.",
            "overlay/scripts/.",
            "overlay/assets/.",
            "overlay/third_party/somehand/.",
            "pip install --no-build-isolation -e . --no-deps",
        )
        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            for fragment in required:
                with self.subTest(path=path.name, fragment=fragment):
                    self.assertIn(fragment, text)
            self.assertLess(
                text.index("tar -xzf Teleopit-latest.tar.gz"),
                text.index("cp -a overlay/teleopit/."),
            )

        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("bash scripts/setup/install.sh", text)

        chinese = DOCS[0].read_text(encoding="utf-8")
        english = DOCS[1].read_text(encoding="utf-8")
        self.assertIn("G1 初始没有 Teleopit", chinese)
        self.assertIn("G1 initially has no Teleopit", english)
        self.assertIn("Teleopit 源码压缩包不包含 Conda 环境", chinese)
        self.assertIn("Teleopit source archive does not contain the Conda environment", english)

    def test_both_guides_explain_how_e2_endpoints_were_identified(self):
        required = (
            "ip -4 address show eth1",
            "ip route",
            "ip neigh show dev eth1",
            "nc -vz -w 2 192.168.123.210 6000",
            "nc -vz -w 2 192.168.123.211 6000",
            "Modbus FC03",
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
        self.assertIn("docs/en/usage.md", readme)
        self.assertIn("docs/zh/usage.md", readme)
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

    def test_language_trees_include_usage(self):
        required = {"README.md", "usage.md"}
        for root in LANGUAGE_ROOTS:
            actual = {
                path.relative_to(root).as_posix()
                for path in root.rglob("*.md")
            }
            with self.subTest(root=root.name):
                self.assertTrue(required.issubset(actual))

    def test_docs_root_has_no_language_specific_markdown(self):
        root_markdown = sorted(path.name for path in (ROOT / "docs").glob("*.md"))
        self.assertEqual(root_markdown, [])

    def test_language_docs_do_not_cross_link(self):
        for language, other in (("en", "zh"), ("zh", "en")):
            language_root = ROOT / "docs" / language
            other_root = (ROOT / "docs" / other).resolve()
            for path in language_root.rglob("*.md"):
                text = path.read_text(encoding="utf-8")
                for target in MARKDOWN_LINK_RE.findall(text):
                    resolved = self._resolve_local_link(path, target)
                    if resolved is None:
                        continue
                    language_switch = (ROOT / "docs" / other / "README.md").resolve()
                    if path.name == "README.md" and resolved == language_switch:
                        continue
                    with self.subTest(path=path, target=target):
                        try:
                            resolved.relative_to(other_root)
                        except ValueError:
                            pass
                        else:
                            self.fail(f"cross-language link: {path} -> {target}")

    def test_all_relative_markdown_links_resolve(self):
        markdown_files = tuple(
            path for path in ROOT.rglob("*.md")
            if ".git" not in path.parts
        )
        for path in markdown_files:
            text = path.read_text(encoding="utf-8")
            for target in MARKDOWN_LINK_RE.findall(text):
                resolved = self._resolve_local_link(path, target)
                if resolved is None:
                    continue
                with self.subTest(path=path, target=target):
                    self.assertTrue(resolved.exists(), f"broken link: {path} -> {target}")

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

    def test_guides_document_verified_onboard_and_external_host_topologies(self):
        shared = (
            "192.168.123.164",
            "192.168.123.210",
            "192.168.123.211",
            "scripts/dev/check_unitree_g1_rh56e2.sh",
            "scripts/run/run_unitree_g1_rh56e2.sh",
            "g1_host_cli",
            "Ctrl+C",
        )
        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            for fragment in shared:
                with self.subTest(path=path.name, fragment=fragment):
                    self.assertIn(fragment, text)

        chinese = DOCS[0].read_text(encoding="utf-8")
        english = DOCS[1].read_text(encoding="utf-8")
        for fragment in ("机载运行", "外部主机运行", "同一时间只能有一个"):
            self.assertIn(fragment, chinese)
        for fragment in ("Onboard operation", "External-host operation", "Only one"):
            self.assertIn(fragment, english)

    def test_operator_docs_use_one_miniforge_environment(self):
        paths = (ROOT / "README.md", *DOCS)
        required = ("source /home/unitree/miniforge3/bin/activate teleopit",)
        for path in paths:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn(".venv", text)
                self.assertNotIn("conda create -n teleopit", text)
                for fragment in required:
                    self.assertIn(fragment, text)

    @staticmethod
    def _resolve_local_link(source: Path, target: str) -> Optional[Path]:
        target = target.strip().strip("<>")
        if not target or target.startswith("#") or "://" in target or target.startswith("mailto:"):
            return None
        path_text = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if not path_text:
            return None
        return (source.parent / path_text).resolve()


if __name__ == "__main__":
    unittest.main()
