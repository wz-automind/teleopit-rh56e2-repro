import json
import unittest
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 development environments
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_project_declares_all_upstream_dependencies(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(project["requires-python"], ">=3.10")
        dependencies = "\n".join(project["dependencies"])
        for name in ("teleopit", "somehand", "pico-bridge"):
            with self.subTest(name=name):
                self.assertIn(name, dependencies)

    def test_dev_tools_match_upstream_conventions(self):
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(config["tool"]["pytest"]["ini_options"]["testpaths"], ["tests"])
        self.assertEqual(config["tool"]["ruff"]["target-version"], "py310")

    def test_manifest_defines_rh56e2_integration_ownership(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        architecture = manifest["architecture"]
        self.assertEqual(architecture["base_runtime"], "teleopit")
        self.assertEqual(architecture["hand_retargeting"], "somehand")
        self.assertEqual(architecture["pico_transport"], "pico_bridge")
        self.assertEqual(architecture["supported_hand"], "Inspire RH56E2")

    def test_upstream_style_entry_points_exist(self):
        paths = (
            "scripts/setup/install.sh",
            "scripts/dev/validate.sh",
            "scripts/dev/check_rh56e2.py",
            "scripts/dev/bench_rh56e2.py",
            "scripts/run/run_sim_rh56e2.sh",
            "scripts/run/run_sim2real_rh56e2.sh",
        )
        for relative in paths:
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_shell_launchers_preserve_arguments_and_exit_codes(self):
        for relative in (
            "scripts/setup/install.sh",
            "scripts/dev/validate.sh",
            "scripts/run/run_sim_rh56e2.sh",
            "scripts/run/run_sim2real_rh56e2.sh",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                self.assertIn("exec ", text)
                self.assertIn('"$@"', text)


if __name__ == "__main__":
    unittest.main()
