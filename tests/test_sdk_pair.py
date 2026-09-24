from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from teleopit_rh56e2.sdk import (
    RH56E2ConnectionError,
    RH56E2Hand,
    RH56E2Pair,
    RH56E2Telemetry,
    RH56E2ValidationError,
    WriteDisabledError,
)
from teleopit_rh56e2.sdk.protocol import FAULT_ACT, TEMPERATURE_ACT


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

    @staticmethod
    def validate_speed(values: object) -> tuple[int, ...]:
        return RH56E2Hand.validate_speed(values)  # type: ignore[arg-type]

    @staticmethod
    def validate_positions(values: object) -> tuple[int, ...]:
        return RH56E2Hand.validate_positions(values)  # type: ignore[arg-type]

    def _require_write_ready(self) -> None:
        pass

    def set_speed(self, values: object) -> None:
        self.speed_calls.append(values)

    def set_positions(self, values: object) -> None:
        self.position_calls.append(values)


class FakeClient:
    def __init__(self) -> None:
        self.writes: list[tuple[int, tuple[int, ...]]] = []

    def connect(self) -> None:
        pass

    def close(self) -> None:
        pass

    def read_bytes(self, address: int, byte_count: int) -> bytes:
        if address not in (FAULT_ACT, TEMPERATURE_ACT) or byte_count != 6:
            raise AssertionError((address, byte_count))
        return bytes((0, 0, 0, 0, 0, 0))

    def write_holding(self, address: int, values: tuple[int, ...]) -> None:
        self.writes.append((address, tuple(values)))


def sdk_hand(host: str, *, write_enabled: bool = True, connect: bool = True) -> tuple[RH56E2Hand, FakeClient]:
    client = FakeClient()
    hand = RH56E2Hand(host, client=client, write_enabled=write_enabled)
    if connect:
        hand.connect()
    return hand, client


class RH56E2PairTests(unittest.TestCase):
    def test_duplicate_endpoints_are_rejected(self) -> None:
        with self.assertRaisesRegex(RH56E2ValidationError, "distinct"):
            RH56E2Pair(FakeHand(), FakeHand())

    def test_second_connect_failure_closes_first(self) -> None:
        left = FakeHand()
        right = FakeHand(host="192.0.2.11", connect_error=ConnectionError("offline"))

        with self.assertRaises(ConnectionError):
            RH56E2Pair(left, right).connect()

        self.assertEqual(left.close_calls, 1)
        self.assertEqual(right.connect_calls, 1)

    def test_connect_rollback_does_not_swallow_process_control_exceptions(self) -> None:
        for control_error in (KeyboardInterrupt, SystemExit):
            with self.subTest(control_error=control_error):
                left = FakeHand(close_error=control_error())
                right = FakeHand(host="192.0.2.11", connect_error=ConnectionError("offline"))

                with self.assertRaises(control_error):
                    RH56E2Pair(left, right).connect()

                self.assertEqual(left.close_calls, 1)


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

    def test_close_does_not_swallow_process_control_exceptions(self) -> None:
        for control_error in (KeyboardInterrupt, SystemExit):
            with self.subTest(control_error=control_error):
                left = FakeHand(close_error=RuntimeError("left close failed"))
                right = FakeHand(host="192.0.2.11", close_error=control_error())

                with self.assertRaises(control_error):
                    RH56E2Pair(left, right).close()

                self.assertEqual(left.close_calls, 1)
                self.assertEqual(right.close_calls, 1)

    def test_reads_and_writes_preserve_left_right(self) -> None:
        left = FakeHand(sample=telemetry(1))
        right = FakeHand(host="192.0.2.11", sample=telemetry(2))
        pair = RH56E2Pair(left, right)

        self.assertEqual(pair.read_telemetry(), {"left": left.sample, "right": right.sample})
        pair.set_speeds(left=(1, 2, 3, 4, 5, 6), right=(7, 8, 9, 10, 11, 12))
        pair.set_positions(left=(13, 14, 15, 16, 17, 18), right=(19, 20, 21, 22, 23, 24))

        self.assertEqual(left.speed_calls, [(1, 2, 3, 4, 5, 6)])
        self.assertEqual(right.speed_calls, [(7, 8, 9, 10, 11, 12)])
        self.assertEqual(left.position_calls, [(13, 14, 15, 16, 17, 18)])
        self.assertEqual(right.position_calls, [(19, 20, 21, 22, 23, 24)])

    def test_invalid_right_command_is_rejected_before_either_write(self) -> None:
        left, left_client = sdk_hand("192.0.2.10")
        right, right_client = sdk_hand("192.0.2.11")

        with self.assertRaises(RH56E2ValidationError):
            RH56E2Pair(left, right).set_positions(left=(500,) * 6, right=(500,) * 5)

        self.assertEqual(left_client.writes, [])
        self.assertEqual(right_client.writes, [])

    def test_right_local_write_state_is_checked_before_either_write(self) -> None:
        cases = (
            ({"write_enabled": False, "connect": True}, WriteDisabledError),
            ({"write_enabled": True, "connect": False}, RH56E2ConnectionError),
        )
        for right_options, expected_error in cases:
            with self.subTest(right_options=right_options):
                left, left_client = sdk_hand("192.0.2.10")
                right, right_client = sdk_hand("192.0.2.11", **right_options)

                with self.assertRaises(expected_error):
                    RH56E2Pair(left, right).set_speeds(left=(500,) * 6, right=(500,) * 6)

                self.assertEqual(left_client.writes, [])
                self.assertEqual(right_client.writes, [])


if __name__ == "__main__":
    unittest.main()
