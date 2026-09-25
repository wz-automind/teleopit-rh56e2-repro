import re
import unittest
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
USAGE = ROOT / "docs" / "zh" / "usage.md"
DOCS = (USAGE,)
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


class UsageGuideTests(unittest.TestCase):
    def test_repository_exposes_only_chinese_operator_docs(self):
        self.assertFalse((ROOT / "docs" / "en").exists())
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/zh/README.md", readme)
        self.assertIn("docs/zh/usage.md", readme)
        self.assertNotIn("docs/en/", readme)

    def test_sdk_reference_is_indexed(self):
        chinese_path = ROOT / "docs" / "zh" / "reference" / "sdk.md"
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
                self.assertIn(fragment, chinese)

        index = (ROOT / "docs" / "zh" / "README.md").read_text(encoding="utf-8")
        self.assertIn("reference/sdk.md", index)

        root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/zh/reference/sdk.md", root_readme)

    def test_guide_has_complete_numbered_structure(self):
        text = USAGE.read_text(encoding="utf-8")
        sequence = [int(value) for value in re.findall(r"^## (\d+)\.", text, re.MULTILINE)]
        self.assertEqual(sequence, list(range(1, 18)))

    def test_guide_includes_every_safety_entry_point(self):
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

    def test_staged_hardware_checks_are_described_without_command_walkthroughs(self):
        text = USAGE.read_text(encoding="utf-8")
        staged = text.split("## 12.", 1)[1].split("## 13.", 1)[0]
        for command in (
            "python scripts/dev/check_rh56e2.py",
            "python scripts/dev/bench_rh56e2.py",
            "python scripts/run/standalone_standing.py",
            "--dry-run",
        ):
            with self.subTest(command=command):
                self.assertNotIn(command, staged)

    def test_guide_deploys_full_teleopit_before_integration_overlay(self):
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

        chinese = USAGE.read_text(encoding="utf-8")
        self.assertLess(
            chinese.index("bash scripts/setup/install.sh"),
            chinese.index("scp ~/Teleopit-latest.tar.gz"),
        )
        self.assertIn("G1 初始没有 Teleopit", chinese)
        self.assertIn("Teleopit 源码压缩包不包含 Conda 环境", chinese)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for text in (readme, chinese):
            with self.subTest(document="README" if text is readme else "usage"):
                self.assertIn("c753829882fba461ed07ba25aaabee0a25d83663", text)
                self.assertLess(
                    text.index("c753829882fba461ed07ba25aaabee0a25d83663"),
                    text.index("-czf Teleopit-latest.tar.gz"),
                )

        g1_section = chinese.split("## 9. 通过 SSH 传输并配置 G1", 1)[1]
        self.assertNotIn("git clone https://", g1_section)

    def test_guide_explains_how_e2_endpoints_were_identified(self):
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

    def test_guide_documents_live_simulation_operation(self):
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

    def test_readme_links_chinese_guide(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/zh/usage.md", readme)
        self.assertIn("docs/zh/README.md", readme)

    def test_chinese_document_tree_includes_required_guides(self):
        actual = {
            path.relative_to(ROOT / "docs" / "zh").as_posix()
            for path in (ROOT / "docs" / "zh").rglob("*.md")
        }
        required = {
            "README.md",
            "usage.md",
            "reference/architecture.md",
            "reference/rh56e2.md",
            "reference/sdk.md",
            "reference/upstreams.md",
        }
        self.assertTrue(required.issubset(actual))

    def test_docs_root_has_no_language_specific_markdown(self):
        root_markdown = sorted(path.name for path in (ROOT / "docs").glob("*.md"))
        self.assertEqual(root_markdown, [])

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
            "hands.rh56e2.write_enabled=true",
        )
        chinese_required = (
            "# 全身遥操启动指令（不包含灵巧手）",
            "# 全身遥操启动指令（包含左右 E2）",
            "不能同时运行",
        )
        chinese = USAGE.read_text(encoding="utf-8")
        for fragment in required:
            with self.subTest(language="zh", fragment=fragment):
                self.assertIn(fragment, chinese)
        for fragment in chinese_required:
            self.assertIn(fragment, chinese)

        base_index = chinese.index("--config-name pico4_sim2real ")
        e2_index = chinese.index("--config-name pico4_sim2real_rh56e2 ")
        self.assertLess(base_index, e2_index)
        for stale_interface in (
            "real_robot.network_interface=eth0",
            "NETWORK_INTERFACE=eth0",
            "--network-interface eth0",
        ):
            self.assertNotIn(stale_interface, chinese)

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

        chinese = USAGE.read_text(encoding="utf-8")
        for fragment in ("机载运行", "外部主机运行", "同一时间只能有一个"):
            self.assertIn(fragment, chinese)

    def test_operator_docs_use_the_default_miniforge_installation(self):
        paths = (ROOT / "README.md", *DOCS)
        required = (
            "source /home/unitree/miniforge3/bin/activate teleopit",
            "conda create -n teleopit python=3.11",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn("python -m venv", text)
                self.assertNotIn("source .venv", text)
                self.assertNotIn("Miniforge3-26.7.2-0-Linux-aarch64.sh", text)
                self.assertNotIn("89b786c8d2c8b0fda7553914c1314ae4ddaa094503802f279377b19ac4463cb2", text)
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
