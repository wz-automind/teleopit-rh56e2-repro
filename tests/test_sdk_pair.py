from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from teleopit_rh56e2.sdk import RH56E2Pair, RH56E2Telemetry


def telemetry(value: int) -> RH56E2Telemetry:
    channels = (value,) * 6
    return RH56E2Telemetry(channels, channels, channels, channels, channels, channels)


class FakeHand:
    def __init__(
        self,
        host: str = "192.0.2.10",
        port: int = 6000,
        *,
        connect_error: BaseException | None = None,
        close_error: BaseException | None = None,
        sample: RH56E2Telemetry | None = None,
    ) -> None:
        self.endpoint = (host, port)
        self.connect_error = connect_error
        self.close_error = close_error
        self.sample = sample or telemetry(0)
        self.connect_calls = 0
        self.close_calls = 0
        self.speed_calls: list[object] = []
        self.position_calls: list[object] = []

    def connect(self) -> None:
        self.connect_calls += 1
        if self.connect_error is not None:
            raise self.connect_error

    def close(self) -> None:
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error

    def read_telemetry(self) -> RH56E2Telemetry:
        return self.sample

    def set_speed(self, values: object) -> None:
        self.speed_calls.append(values)

    def set_positions(self, values: object) -> None:
        self.position_calls.append(values)


class RH56E2PairTests(unittest.TestCase):
    def test_duplicate_endpoints_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "distinct"):
            RH56E2Pair(FakeHand(), FakeHand())

    def test_second_connect_failure_closes_first(self) -> None:
        left = FakeHand()
        right = FakeHand(host="192.0.2.11", connect_error=ConnectionError("offline"))

        with self.assertRaises(ConnectionError):
            RH56E2Pair(left, right).connect()

        self.assertEqual(left.close_calls, 1)
        self.assertEqual(right.connect_calls, 1)

    def test_context_closes_both_after_exception(self) -> None:
        left = FakeHand()
        right = FakeHand(host="192.0.2.11")

        with self.assertRaises(RuntimeError):
            with RH56E2Pair(left, right):
                raise RuntimeError("body failed")

        self.assertEqual(left.close_calls, 1)
        self.assertEqual(right.close_calls, 1)

    def test_close_attempts_right_when_left_close_fails(self) -> None:
        left = FakeHand(close_error=RuntimeError("left close failed"))
        right = FakeHand(host="192.0.2.11")

        with self.assertRaisesRegex(RuntimeError, "left close failed"):
            RH56E2Pair(left, right).close()

        self.assertEqual(left.close_calls, 1)
        self.assertEqual(right.close_calls, 1)

    def test_reads_and_writes_preserve_left_right(self) -> None:
        left = FakeHand(sample=telemetry(1))
        right = FakeHand(host="192.0.2.11", sample=telemetry(2))
        pair = RH56E2Pair(left, right)

        self.assertEqual(pair.read_telemetry(), {"left": left.sample, "right": right.sample})
        pair.set_speeds(left=(1, 2, 3), right=(4, 5, 6))
        pair.set_positions(left=(7, 8, 9), right=(10, 11, 12))

        self.assertEqual(left.speed_calls, [(1, 2, 3)])
        self.assertEqual(right.speed_calls, [(4, 5, 6)])
        self.assertEqual(left.position_calls, [(7, 8, 9)])
        self.assertEqual(right.position_calls, [(10, 11, 12)])


if __name__ == "__main__":
    unittest.main()
