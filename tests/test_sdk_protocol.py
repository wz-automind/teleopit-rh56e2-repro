from __future__ import annotations

import struct
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from teleopit_rh56e2.sdk.models import ModbusProtocolError, RH56E2ConnectionError, RH56E2ValidationError
from teleopit_rh56e2.sdk.protocol import (
    ANGLE_ACT,
    ANGLE_SET,
    RH56E2ModbusClient,
    build_read_frame,
    build_write_frame,
    parse_read_response,
    parse_write_response,
)


def response(pdu: bytes, *, transaction_id: int = 9, unit_id: int = 0xFF) -> bytes:
    return struct.pack(">HHHB", transaction_id, 0, len(pdu) + 1, unit_id) + pdu


class FakeSocket:
    def __init__(self, *chunks: bytes):
        self.chunks = list(chunks)
        self.sent: list[bytes] = []
        self.shutdown_calls = 0
        self.close_calls = 0

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def setsockopt(self, *args: object) -> None:
        pass

    def sendall(self, payload: bytes) -> None:
        self.sent.append(payload)

    def recv(self, size: int) -> bytes:
        if not self.chunks:
            return b""
        return self.chunks.pop(0)

    def shutdown(self, how: int) -> None:
        self.shutdown_calls += 1

    def close(self) -> None:
        self.close_calls += 1


class AllocationProbeClient(RH56E2ModbusClient):
    """Pauses the first allocation so lock coverage is directly observable."""

    def __init__(self) -> None:
        super().__init__("host")
        self.first_allocation = threading.Event()
        self.second_allocation = threading.Event()
        self.release_first_allocation = threading.Event()
        self.sent: list[bytes] = []
        self._allocation_calls = 0
        self._allocation_probe_lock = threading.Lock()

    def _next_transaction_id(self) -> int:
        with self._allocation_probe_lock:
            self._allocation_calls += 1
            allocation_call = self._allocation_calls
        transaction_id = super()._next_transaction_id()
        if allocation_call == 1:
            self.first_allocation.set()
            self.release_first_allocation.wait(timeout=1)
        else:
            self.second_allocation.set()
        return transaction_id

    def _send(self, payload: bytes) -> None:
        self.sent.append(payload)

    def _recv_frame(self) -> bytes:
        return response(b"\x03\x02\x00\x2a")


class ProtocolTests(unittest.TestCase):
    def test_build_read_frame(self) -> None:
        self.assertEqual(build_read_frame(1, 0xFF, ANGLE_ACT, 6).hex(), "000100000006ff03060a0006")

    def test_build_write_frame_encodes_hold_as_ffff(self) -> None:
        frame = build_write_frame(2, 0xFF, ANGLE_SET, [0, 1, 500, 999, 1000, -1])
        self.assertEqual(frame[:7].hex(), "000200000013ff")
        self.assertEqual(frame[7:13].hex(), "1005ce00060c")
        self.assertEqual(frame[13:].hex(), "0000000101f403e703e8ffff")

    def test_parse_read_response(self) -> None:
        frame = response(b"\x03\x0c" + struct.pack(">6H", 0, 1, 500, 999, 1000, 65535))
        self.assertEqual(parse_read_response(frame, count=6), (0, 1, 500, 999, 1000, 65535))

    def test_parse_write_response_ignores_transaction_id_quirk(self) -> None:
        frame = response(struct.pack(">BHH", 0x10, ANGLE_SET, 6), transaction_id=77)
        parse_write_response(frame, address=ANGLE_SET, count=6)

    def test_modbus_exception_is_rejected(self) -> None:
        with self.assertRaises(ModbusProtocolError):
            parse_read_response(response(b"\x83\x02"), count=6)

    def test_constructor_rejects_invalid_network_values(self) -> None:
        for kwargs in (
            {"port": 0},
            {"port": 65536},
            {"unit_id": -1},
            {"unit_id": 256},
            {"timeout": 0},
            {"timeout": float("nan")},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(RH56E2ValidationError):
                RH56E2ModbusClient("192.0.2.10", **kwargs)

    def test_request_lock_covers_transaction_allocation_and_frame_building(self) -> None:
        client = AllocationProbeClient()
        errors: list[BaseException] = []

        def read() -> None:
            try:
                client.read_holding(ANGLE_ACT, 1)
            except BaseException as exc:  # Thread failures must fail this test below.
                errors.append(exc)

        first = threading.Thread(target=read)
        second = threading.Thread(target=read)
        first.start()
        self.assertTrue(client.first_allocation.wait(timeout=1))
        second.start()
        try:
            self.assertFalse(client.second_allocation.wait(timeout=0.05))
            self.assertEqual(client.sent, [])
        finally:
            client.release_first_allocation.set()
            first.join(timeout=1)
            second.join(timeout=1)

        self.assertEqual(errors, [])
        self.assertEqual([struct.unpack(">H", frame[:2])[0] for frame in client.sent], [1, 2])

    def test_write_rejects_bool_and_float_registers(self) -> None:
        for value in (True, 1.0):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                build_write_frame(1, 0xFF, ANGLE_SET, [value] * 6)

    def test_client_reads_exact_frame_across_partial_chunks(self) -> None:
        frame = response(b"\x03\x02\x00\x2a")
        fake = FakeSocket(frame[:2], frame[2:7], frame[7:])
        client = RH56E2ModbusClient("host", socket_factory=lambda *args, **kwargs: fake)
        client.connect()
        self.assertEqual(client.read_holding(ANGLE_ACT, 1), (42,))
        self.assertEqual(len(fake.sent), 1)

    def test_client_rejects_peer_close(self) -> None:
        fake = FakeSocket(struct.pack(">HHHB", 1, 0, 3, 0xFF), b"")
        client = RH56E2ModbusClient("host", socket_factory=lambda *args, **kwargs: fake)
        client.connect()
        with self.assertRaises(RH56E2ConnectionError):
            client.read_holding(ANGLE_ACT, 1)

    def test_close_is_idempotent(self) -> None:
        fake = FakeSocket()
        client = RH56E2ModbusClient("host", socket_factory=lambda *args, **kwargs: fake)
        client.connect()
        client.close()
        client.close()
        self.assertEqual(fake.shutdown_calls, 1)
        self.assertEqual(fake.close_calls, 1)


if __name__ == "__main__":
    unittest.main()
