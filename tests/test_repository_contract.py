import json
import unittest
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 development environments
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_sdk_is_installed_and_validated_without_hardware_connection(self):
        install_text = (ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        validate_text = (ROOT / "scripts" / "validate.sh").read_text(encoding="utf-8")

        self.assertIn('pip install --no-build-isolation -e "$ROOT_DIR" --no-deps', install_text)
        self.assertIn("from teleopit_rh56e2.sdk import RH56E2Hand", validate_text)

    def test_sdk_uses_src_package_discovery_without_extra_runtime_dependencies(self):
        project_config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        package_find = project_config["tool"]["setuptools"]["packages"]["find"]
        self.assertEqual(package_find["where"], ["src"])
        self.assertIn("teleopit_rh56e2*", package_find["include"])
        self.assertEqual(len(project_config["project"]["dependencies"]), 3)

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
            "scripts/dev/check_unitree_g1_rh56e2.sh",
            "scripts/run/run_unitree_g1_rh56e2.sh",
        )
        for relative in paths:
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_verified_unitree_deployment_entry_points_use_observed_network(self):
        check = (ROOT / "scripts" / "dev" / "check_unitree_g1_rh56e2.sh").read_text(
            encoding="utf-8"
        )
        launch = (ROOT / "scripts" / "run" / "run_unitree_g1_rh56e2.sh").read_text(
            encoding="utf-8"
        )
        required = (
            "192.168.123.164",
            "192.168.123.210",
            "192.168.123.211",
            "192.168.50.62",
            "eth1",
            "6000",
        )
        for fragment in required:
            with self.subTest(script="check", fragment=fragment):
                self.assertIn(fragment, check)
            with self.subTest(script="launch", fragment=fragment):
                self.assertIn(fragment, launch)

        self.assertIn("--hardware", check)
        self.assertNotIn("write_enabled=true", check)
        self.assertIn('exec env', launch)
        self.assertIn('ENABLE_G1_REAL="${ENABLE_G1_REAL:-}"', launch)
        self.assertIn('ENABLE_RH56E2_WRITES="${ENABLE_RH56E2_WRITES:-}"', launch)
        self.assertIn('input.bridge_advertise_ip=$PICO_ADVERTISE_IP', launch)

    def test_shell_launchers_preserve_arguments_and_exit_codes(self):
        for relative in (
            "scripts/setup/install.sh",
            "scripts/dev/validate.sh",
            "scripts/run_real.sh",
            "scripts/run/run_sim_rh56e2.sh",
            "scripts/run/run_sim2real_rh56e2.sh",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                self.assertIn("exec ", text)
                self.assertIn('"$@"', text)

    def test_real_launcher_extends_the_upstream_sim2real_command(self):
        text = (ROOT / "scripts" / "run_real.sh").read_text(encoding="utf-8")
        required = (
            "scripts/run/run_sim2real.py",
            "--config-name pico4_sim2real_rh56e2",
            "controller.policy_path=ckpt/track_g1.onnx",
            "real_robot.network_interface=$NETWORK_INTERFACE",
            "hands.rh56e2.left_host=$LEFT_HAND_IP",
            "hands.rh56e2.right_host=$RIGHT_HAND_IP",
            "hands.rh56e2.write_enabled=true",
        )
        for fragment in required:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)
        self.assertGreater(
            text.rfind('"$@"'),
            text.find('"hands.rh56e2.write_enabled=true"'),
        )

    def test_install_and_launchers_use_the_active_teleopit_conda_environment(self):
        helper = (ROOT / "scripts" / "lib" / "conda_env.sh").read_text(encoding="utf-8")
        for fragment in (
            "CONDA_DEFAULT_ENV",
            "CONDA_PREFIX",
            "teleopit",
            "conda activate teleopit",
            "TELEOPIT_PYTHON",
        ):
            with self.subTest(helper=fragment):
                self.assertIn(fragment, helper)

        self.assertNotIn("/home/unitree/miniforge3", helper)

        scripts = (
            ROOT / "scripts" / "install.sh",
            ROOT / "scripts" / "validate.sh",
            ROOT / "scripts" / "run_real.sh",
            ROOT / "scripts" / "run" / "run_sim_rh56e2.sh",
        )
        for path in scripts:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("require_teleopit_conda", text)
                self.assertIn("TELEOPIT_PYTHON", text)
                self.assertNotIn(".venv", text)
                self.assertNotIn("-m venv", text)

    def test_real_launcher_uses_current_network_and_hand_port_keys(self):
        text = (ROOT / "scripts" / "run_real.sh").read_text(encoding="utf-8")
        self.assertIn('NETWORK_INTERFACE="${NETWORK_INTERFACE:-eth1}"', text)
        self.assertIn('"hands.rh56e2.port=$HAND_PORT"', text)
        self.assertNotIn("hands.rh56e2.left_port", text)
        self.assertNotIn("hands.rh56e2.right_port", text)


if __name__ == "__main__":
    unittest.main()
