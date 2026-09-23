from __future__ import annotations

import importlib
import sys
import time
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import teleopit  # noqa: E402

teleopit.__path__.insert(0, str(ROOT / "overlay" / "teleopit"))
import teleopit.sim2real  # noqa: E402

teleopit.sim2real.__path__.insert(0, str(ROOT / "overlay" / "teleopit" / "sim2real"))
import teleopit.sim2real.hands  # noqa: E402

teleopit.sim2real.hands.__path__.insert(0, str(ROOT / "overlay" / "teleopit" / "sim2real" / "hands"))


class LegacyProtocolCompatibilityTests(unittest.TestCase):
    def test_legacy_protocol_exports_sdk_objects_and_warns(self) -> None:
        module_name = "teleopit.sim2real.hands.rh56e2_protocol"
        sys.modules.pop(module_name, None)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            legacy = importlib.import_module(module_name)

        from teleopit_rh56e2.sdk import protocol as sdk_protocol
        from teleopit_rh56e2.sdk.models import ModbusProtocolError

        self.assertTrue(any(item.category is DeprecationWarning for item in caught))
        self.assertIs(legacy.Rh56e2ModbusClient, sdk_protocol.RH56E2ModbusClient)
        self.assertIs(legacy.ModbusProtocolError, ModbusProtocolError)
        for name in (
            "ANGLE_SET",
            "SPEED_SET",
            "ANGLE_ACT",
            "FORCE_ACT",
            "CURRENT_ACT",
            "FAULT_ACT",
            "STATE_ACT",
            "TEMPERATURE_ACT",
            "build_read_frame",
            "build_write_frame",
            "parse_read_response",
            "parse_write_response",
        ):
            self.assertIs(getattr(legacy, name), getattr(sdk_protocol, name))


class TeleopitDelegationTests(unittest.TestCase):
    @staticmethod
    def _device(*, write_enabled: bool):
        from teleopit.sim2real.hands.rh56e2 import Rh56e2Device, parse_rh56e2_config

        config = parse_rh56e2_config(
            {
                "hands": {
                    "sides": ["left"],
                    "rh56e2": {"left_host": "192.168.11.210", "write_enabled": write_enabled},
                }
            }
        )
        return Rh56e2Device(config)

    def test_send_pose_delegates_to_sdk_hand_positions(self) -> None:
        from teleopit.sim2real.hands.rh56e2 import Rh56e2Device, parse_rh56e2_config

        from teleopit_rh56e2.sdk import RH56E2Telemetry

        config = parse_rh56e2_config(
            {
                "hands": {
                    "sides": ["left"],
                    "rh56e2": {"left_host": "192.168.11.210", "write_enabled": True},
                }
            }
        )
        telemetry = RH56E2Telemetry(
            angle=(0, 0, 0, 0, 0, 0),
            force=(0, 0, 0, 0, 0, 0),
            current=(0, 0, 0, 0, 0, 0),
            fault=(0, 0, 0, 0, 0, 0),
            state=(0, 0, 0, 0, 0, 0),
            temperature=(25, 25, 25, 25, 25, 25),
        )
        with patch("teleopit.sim2real.hands.rh56e2.RH56E2Hand") as hand_class:
            hand_class.validate_positions.side_effect = tuple
            hand_class.return_value.read_telemetry.return_value = telemetry
            device = Rh56e2Device(config)
            device.connect()
            device.send_pose("left", (100, 200, 300, 400, 500, 600), force=True)

        hand_class.return_value.set_positions.assert_called_once_with((100, 200, 300, 400, 500, 600))

    def test_invalid_pose_is_rejected_even_when_writes_are_disabled(self) -> None:
        device = self._device(write_enabled=False)

        with self.assertRaises(TypeError):
            device.send_pose("left", (500.5,) * 6)

    def test_invalid_pose_is_rejected_before_rate_limit_suppression(self) -> None:
        device = self._device(write_enabled=True)
        device._last_write_s["left"] = time.monotonic()

        with self.assertRaises(TypeError):
            device.send_pose("left", (500.5,) * 6)

    def test_invalid_pose_is_rejected_before_minimum_change_suppression(self) -> None:
        device = self._device(write_enabled=True)
        device._last_pose["left"] = (500,) * 6

        with self.assertRaises(TypeError):
            device.send_pose("left", (500.5,) * 6)


if __name__ == "__main__":
    unittest.main()
