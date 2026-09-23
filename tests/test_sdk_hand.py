from __future__ import annotations

import dataclasses
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from teleopit_rh56e2.sdk import DeviceSafetyError, RH56E2Hand, RH56E2Telemetry, WriteDisabledError
from teleopit_rh56e2.sdk.protocol import (
    ANGLE_ACT,
    ANGLE_SET,
    CURRENT_ACT,
    FAULT_ACT,
    FORCE_ACT,
    SPEED_SET,
    STATE_ACT,
    TEMPERATURE_ACT,
)


class FakeClient:
    """In-memory Modbus boundary used to test the public hand API."""

    def __init__(
        self,
        *,
        fault_reads: list[tuple[int, ...]] | None = None,
        temperature_reads: list[tuple[int, ...]] | None = None,
        unreadable_addresses: set[int] | None = None,
    ) -> None:
        self.connect_calls = 0
        self.close_calls = 0
        self.reads: list[tuple[int, int]] = []
        self.writes: list[tuple[int, tuple[int, ...]]] = []
        self.events: list[tuple[object, ...]] = []
        self.fault_reads = list(fault_reads or [])
        self.temperature_reads = list(temperature_reads or [])
        self.unreadable_addresses = unreadable_addresses or set()
        self.values = {
            ANGLE_ACT: (100, 101, 102, 103, 104, 105),
            FORCE_ACT: (0, 1, 32767, 32768, 65534, 65535),
            CURRENT_ACT: (10, 11, 12, 13, 14, 15),
            FAULT_ACT: (0, 0, 0, 0, 0, 0),
            STATE_ACT: (20, 21, 22, 23, 24, 25),
            TEMPERATURE_ACT: (30, 31, 32, 33, 34, 35),
        }

    def connect(self) -> None:
        self.connect_calls += 1

    def close(self) -> None:
        self.close_calls += 1

    def read_holding(self, address: int, count: int) -> tuple[int, ...]:
        self.reads.append((address, count))
        self.events.append(("read", address, count))
        if address in self.unreadable_addresses:
            raise RuntimeError("simulated unreadable register")
        if address == FAULT_ACT and self.fault_reads:
            return self.fault_reads.pop(0)
        if address == TEMPERATURE_ACT and self.temperature_reads:
            return self.temperature_reads.pop(0)
        return self.values[address]

    def write_holding(self, address: int, values: tuple[int, ...]) -> None:
        self.writes.append((address, tuple(values)))
        self.events.append(("write", address, tuple(values)))


class InterleavingProbeClient(FakeClient):
    """Makes a missing hand-level write lock deterministically observable."""

    def __init__(self) -> None:
        super().__init__()
        self.first_fault_seen = threading.Event()
        self.second_fault_seen = threading.Event()
        self.release_first_fault = threading.Event()
        self._fault_reads = 0
        self._fault_reads_lock = threading.Lock()

    def read_holding(self, address: int, count: int) -> tuple[int, ...]:
        if address != FAULT_ACT:
            return super().read_holding(address, count)
        with self._fault_reads_lock:
            fault_read_number = self._fault_reads
            self._fault_reads += 1
        result = super().read_holding(address, count)
        if fault_read_number == 0:
            self.first_fault_seen.set()
            self.release_first_fault.wait(timeout=1)
        else:
            self.second_fault_seen.set()
        return result


class RH56E2HandReadTests(unittest.TestCase):
    def test_read_telemetry_returns_immutable_six_channel_snapshot(self) -> None:
        hand = RH56E2Hand("192.0.2.10", client=FakeClient())
        hand.connect()

        sample = hand.read_telemetry()

        self.assertIsInstance(sample, RH56E2Telemetry)
        self.assertEqual(sample.angle, (100, 101, 102, 103, 104, 105))
        self.assertEqual(sample.force, (0, 1, 32767, -32768, -2, -1))
        self.assertEqual(sample.current, (10, 11, 12, 13, 14, 15))
        self.assertEqual(sample.fault, (0, 0, 0, 0, 0, 0))
        self.assertEqual(sample.state, (20, 21, 22, 23, 24, 25))
        self.assertEqual(sample.temperature, (30, 31, 32, 33, 34, 35))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            sample.angle = ()

    def test_read_telemetry_before_connect_raises_connection_error(self) -> None:
        hand = RH56E2Hand("192.0.2.10", client=FakeClient())

        with self.assertRaises(ConnectionError):
            hand.read_telemetry()

    def test_context_manager_connects_and_closes_client(self) -> None:
        client = FakeClient()

        with RH56E2Hand("192.0.2.10", client=client) as hand:
            self.assertEqual(hand.endpoint, ("192.0.2.10", 6000))
            self.assertEqual(client.connect_calls, 1)

        self.assertEqual(client.close_calls, 1)


def connected_hand(*, client: FakeClient, write_enabled: bool = False, max_temperature_c: int = 70) -> RH56E2Hand:
    hand = RH56E2Hand(
        "192.0.2.10",
        client=client,
        write_enabled=write_enabled,
        max_temperature_c=max_temperature_c,
    )
    hand.connect()
    return hand


class RH56E2HandWriteTests(unittest.TestCase):
    def test_constructor_rejects_coerced_transport_values(self) -> None:
        invalid_kwargs = (
            {"port": True},
            {"port": 6000.5},
            {"unit_id": True},
            {"unit_id": 1.5},
            {"timeout": True},
        )
        for kwargs in invalid_kwargs:
            with self.subTest(kwargs=kwargs), self.assertRaises((TypeError, ValueError)):
                RH56E2Hand("192.0.2.10", client=FakeClient(), **kwargs)

        hand = RH56E2Hand("192.0.2.10", client=FakeClient(), timeout=0.25)
        self.assertEqual(hand.timeout, 0.25)

    def test_constructor_requires_a_boolean_write_opt_in(self) -> None:
        with self.assertRaises(TypeError):
            RH56E2Hand("192.0.2.10", client=FakeClient(), write_enabled="yes")  # type: ignore[arg-type]

    def test_constructor_requires_an_integer_temperature_limit(self) -> None:
        for value in (True, 70.5):
            with self.subTest(value=value), self.assertRaises(TypeError):
                RH56E2Hand("192.0.2.10", client=FakeClient(), max_temperature_c=value)  # type: ignore[arg-type]

    def test_write_is_disabled_by_default_and_sends_no_protocol_request(self) -> None:
        client = FakeClient()
        hand = connected_hand(client=client)

        with self.assertRaises(WriteDisabledError):
            hand.set_positions([500] * 6)

        self.assertEqual(client.reads, [])
        self.assertEqual(client.writes, [])

    def test_unconnected_disabled_write_raises_write_disabled_without_protocol_request(self) -> None:
        client = FakeClient()
        hand = RH56E2Hand("192.0.2.10", client=client)

        with self.assertRaises(WriteDisabledError):
            hand.set_speed([500] * 6)

        self.assertEqual(client.reads, [])
        self.assertEqual(client.writes, [])

    def test_invalid_commands_are_rejected_without_a_protocol_request(self) -> None:
        cases = (
            ("set_speed", [500] * 5),
            ("set_speed", [True] * 6),
            ("set_speed", [500.0] * 6),
            ("set_speed", [-1] * 6),
            ("set_speed", [1001] * 6),
            ("set_positions", [500] * 7),
            ("set_positions", [True] * 6),
            ("set_positions", [500.0] * 6),
            ("set_positions", [-2] * 6),
            ("set_positions", [1001] * 6),
        )
        for method_name, values in cases:
            with self.subTest(method=method_name, values=values):
                client = FakeClient()
                hand = connected_hand(client=client, write_enabled=True)

                with self.assertRaises((TypeError, ValueError)):
                    getattr(hand, method_name)(values)

                self.assertEqual(client.reads, [])
                self.assertEqual(client.writes, [])

    def test_valid_commands_refresh_health_immediately_before_writing(self) -> None:
        client = FakeClient()
        hand = connected_hand(client=client, write_enabled=True)

        hand.set_speed([600] * 6)
        hand.set_positions([-1, 0, 250, 500, 750, 1000])

        self.assertEqual(
            client.writes,
            [
                (SPEED_SET, (600, 600, 600, 600, 600, 600)),
                (ANGLE_SET, (-1, 0, 250, 500, 750, 1000)),
            ],
        )
        self.assertEqual(
            client.events,
            [
                ("read", FAULT_ACT, 6),
                ("read", TEMPERATURE_ACT, 6),
                ("write", SPEED_SET, (600, 600, 600, 600, 600, 600)),
                ("read", FAULT_ACT, 6),
                ("read", TEMPERATURE_ACT, 6),
                ("write", ANGLE_SET, (-1, 0, 250, 500, 750, 1000)),
            ],
        )

    def test_each_write_refreshes_fault_health_before_sending(self) -> None:
        client = FakeClient(fault_reads=[(0,) * 6, (1, 0, 0, 0, 0, 0)])
        hand = connected_hand(client=client, write_enabled=True)

        hand.set_positions([500] * 6)
        with self.assertRaises(DeviceSafetyError):
            hand.set_positions([501] * 6)

        self.assertEqual(len([write for write in client.writes if write[0] == ANGLE_SET]), 1)

    def test_concurrent_writes_keep_health_reads_and_writes_atomic(self) -> None:
        client = InterleavingProbeClient()
        hand = connected_hand(client=client, write_enabled=True)
        errors: list[BaseException] = []
        start = threading.Barrier(3)

        def send_speed() -> None:
            try:
                start.wait()
                hand.set_speed([400] * 6)
            except BaseException as exc:  # Thread failures must fail this test below.
                errors.append(exc)

        def send_positions() -> None:
            try:
                start.wait()
                hand.set_positions([500] * 6)
            except BaseException as exc:  # Thread failures must fail this test below.
                errors.append(exc)

        speed_thread = threading.Thread(target=send_speed)
        position_thread = threading.Thread(target=send_positions)
        speed_thread.start()
        position_thread.start()
        start.wait()
        self.assertTrue(client.first_fault_seen.wait(timeout=1))
        client.second_fault_seen.wait(timeout=0.05)
        client.release_first_fault.set()
        speed_thread.join(timeout=1)
        position_thread.join(timeout=1)

        self.assertFalse(speed_thread.is_alive())
        self.assertFalse(position_thread.is_alive())
        self.assertEqual(errors, [])
        speed_transaction = [
            ("read", FAULT_ACT, 6),
            ("read", TEMPERATURE_ACT, 6),
            ("write", SPEED_SET, (400, 400, 400, 400, 400, 400)),
        ]
        position_transaction = [
            ("read", FAULT_ACT, 6),
            ("read", TEMPERATURE_ACT, 6),
            ("write", ANGLE_SET, (500, 500, 500, 500, 500, 500)),
        ]
        self.assertIn(client.events, [speed_transaction + position_transaction, position_transaction + speed_transaction])

    def test_over_temperature_and_unreadable_health_block_writes(self) -> None:
        cases = (
            (
                FakeClient(temperature_reads=[(70, 70, 71, 70, 70, 70)]),
                "over-temperature",
            ),
            (FakeClient(unreadable_addresses={FAULT_ACT}), "unreadable health"),
        )
        for client, condition in cases:
            with self.subTest(condition=condition):
                hand = connected_hand(client=client, write_enabled=True)

                with self.assertRaises(DeviceSafetyError):
                    hand.set_speed([500] * 6)

                self.assertEqual(client.writes, [])


if __name__ == "__main__":
    unittest.main()
