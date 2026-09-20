from __future__ import annotations

import struct
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
import teleopit  # noqa: E402

teleopit.__path__.insert(0, str(ROOT / "overlay" / "teleopit"))
import teleopit.sim2real  # noqa: E402

teleopit.sim2real.__path__.insert(0, str(ROOT / "overlay" / "teleopit" / "sim2real"))
import teleopit.sim2real.hands  # noqa: E402

teleopit.sim2real.hands.__path__.insert(0, str(ROOT / "overlay" / "teleopit" / "sim2real" / "hands"))

from teleopit.sim2real.hands.rh56e2 import (
    ModbusProtocolError,
    build_read_frame,
    build_write_frame,
    parse_read_response,
    parse_rh56e2_config,
    parse_write_response,
    radians_to_raw,
)


def response(pdu: bytes, *, transaction_id: int = 9, unit_id: int = 0xFF) -> bytes:
    return struct.pack(">HHHB", transaction_id, 0, len(pdu) + 1, unit_id) + pdu


class ProtocolTests(unittest.TestCase):
    def test_build_read_frame(self) -> None:
        self.assertEqual(
            build_read_frame(1, 0xFF, 1546, 6).hex(),
            "000100000006ff03060a0006",
        )

    def test_build_write_frame_encodes_hold_as_ffff(self) -> None:
        frame = build_write_frame(2, 0xFF, 1486, [0, 1, 500, 999, 1000, -1])
        self.assertEqual(frame[:7].hex(), "000200000013ff")
        self.assertEqual(frame[7:13].hex(), "1005ce00060c")
        self.assertEqual(frame[13:].hex(), "0000000101f403e703e8ffff")

    def test_parse_read_response(self) -> None:
        frame = response(b"\x03\x0c" + struct.pack(">6H", 0, 1, 500, 999, 1000, 65535))
        self.assertEqual(parse_read_response(frame, count=6), (0, 1, 500, 999, 1000, 65535))

    def test_parse_write_response_ignores_transaction_id_quirk(self) -> None:
        frame = response(struct.pack(">BHH", 0x10, 1486, 6), transaction_id=77)
        parse_write_response(frame, address=1486, count=6)

    def test_modbus_exception_is_rejected(self) -> None:
        with self.assertRaises(ModbusProtocolError):
            parse_read_response(response(b"\x83\x02"), count=6)


class MappingTests(unittest.TestCase):
    def test_unitree_inspire_ranges_map_open_to_1000(self) -> None:
        self.assertEqual(radians_to_raw([0, 0, 0, 0, 0, -0.1]), (1000,) * 6)

    def test_unitree_inspire_ranges_map_closed_to_zero(self) -> None:
        self.assertEqual(radians_to_raw([1.7, 1.7, 1.7, 1.7, 0.5, 1.3]), (0,) * 6)


class ConfigTests(unittest.TestCase):
    def test_writes_are_disabled_by_default(self) -> None:
        cfg = {
            "hands": {
                "sides": ["left"],
                "rh56e2": {"left_host": "192.168.11.210"},
            }
        }
        parsed = parse_rh56e2_config(cfg)
        self.assertFalse(parsed.write_enabled)
        self.assertEqual(parsed.endpoints["left"], ("192.168.11.210", 6000))

    def test_dual_hands_cannot_share_one_endpoint(self) -> None:
        cfg = {
            "hands": {
                "sides": ["left", "right"],
                "rh56e2": {
                    "left_host": "192.168.11.210",
                    "right_host": "192.168.11.210",
                },
            }
        }
        with self.assertRaisesRegex(ValueError, "distinct"):
            parse_rh56e2_config(cfg)


if __name__ == "__main__":
    unittest.main()
