"""Minimal Modbus TCP protocol and transport for Inspire RH56E2 hands."""

from __future__ import annotations

import socket
import struct
import threading
from typing import Sequence

ANGLE_SET = 1486
SPEED_SET = 1522
ANGLE_ACT = 1546
FORCE_ACT = 1582
CURRENT_ACT = 1594
FAULT_ACT = 1606
STATE_ACT = 1612
TEMPERATURE_ACT = 1618


class ModbusProtocolError(RuntimeError):
    """Raised when an RH56E2 returns a malformed or exception response."""


def build_read_frame(transaction_id: int, unit_id: int, address: int, count: int) -> bytes:
    if not 1 <= count <= 125:
        raise ValueError(f"Modbus read count must be in 1..125, got {count}")
    pdu = struct.pack(">BHH", 0x03, _u16(address, "address"), count)
    return struct.pack(">HHHB", transaction_id & 0xFFFF, 0, len(pdu) + 1, _u8(unit_id, "unit_id")) + pdu


def build_write_frame(transaction_id: int, unit_id: int, address: int, values: Sequence[int]) -> bytes:
    encoded = tuple(_register_value(value) for value in values)
    if not 1 <= len(encoded) <= 123:
        raise ValueError(f"Modbus write count must be in 1..123, got {len(encoded)}")
    payload = struct.pack(">" + "H" * len(encoded), *encoded)
    pdu = struct.pack(">BHHB", 0x10, _u16(address, "address"), len(encoded), len(payload)) + payload
    return struct.pack(">HHHB", transaction_id & 0xFFFF, 0, len(pdu) + 1, _u8(unit_id, "unit_id")) + pdu


def parse_read_response(frame: bytes, *, count: int) -> tuple[int, ...]:
    _, pdu = _parse_response(frame)
    if not pdu:
        raise ModbusProtocolError("empty Modbus PDU")
    if pdu[0] & 0x80:
        raise ModbusProtocolError(f"Modbus exception for FC03: code={pdu[1] if len(pdu) > 1 else 'missing'}")
    expected_bytes = count * 2
    if pdu[0] != 0x03 or len(pdu) != expected_bytes + 2 or pdu[1] != expected_bytes:
        raise ModbusProtocolError(
            f"invalid FC03 response: function={pdu[0]:#x}, "
            f"byte_count={pdu[1] if len(pdu) > 1 else 'missing'}, len={len(pdu)}"
        )
    return struct.unpack(">" + "H" * count, pdu[2:])


def parse_write_response(frame: bytes, *, address: int, count: int) -> None:
    _, pdu = _parse_response(frame)
    if not pdu:
        raise ModbusProtocolError("empty Modbus PDU")
    if pdu[0] & 0x80:
        raise ModbusProtocolError(f"Modbus exception for FC16: code={pdu[1] if len(pdu) > 1 else 'missing'}")
    if len(pdu) != 5 or pdu[0] != 0x10:
        raise ModbusProtocolError(f"invalid FC16 response: {pdu.hex()}")
    response_address, response_count = struct.unpack(">HH", pdu[1:])
    if response_address != address or response_count != count:
        raise ModbusProtocolError(
            f"FC16 acknowledgement mismatch: address={response_address}, count={response_count}"
        )


class Rh56e2ModbusClient:
    """Small synchronous Modbus TCP client with complete response draining."""

    def __init__(self, host: str, port: int = 6000, *, unit_id: int = 0xFF, timeout_s: float = 0.5):
        self.host = str(host)
        self.port = int(port)
        self.unit_id = _u8(unit_id, "unit_id")
        self.timeout_s = float(timeout_s)
        self._socket: socket.socket | None = None
        self._transaction_id = 0
        self._lock = threading.Lock()

    def connect(self) -> None:
        if self._socket is not None:
            return
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout_s)
        sock.settimeout(self.timeout_s)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._socket = sock

    def read_holding(self, address: int, count: int) -> tuple[int, ...]:
        transaction_id = self._next_transaction_id()
        request = build_read_frame(transaction_id, self.unit_id, address, count)
        with self._lock:
            self._send(request)
            frame = self._recv_frame()
        return parse_read_response(frame, count=count)

    def read_bytes(self, address: int, byte_count: int) -> bytes:
        if byte_count <= 0:
            raise ValueError("byte_count must be positive")
        register_count = (byte_count + 1) // 2
        values = self.read_holding(address, register_count)
        payload = struct.pack(">" + "H" * len(values), *values)
        return payload[:byte_count]

    def write_holding(self, address: int, values: Sequence[int]) -> None:
        transaction_id = self._next_transaction_id()
        request = build_write_frame(transaction_id, self.unit_id, address, values)
        with self._lock:
            self._send(request)
            frame = self._recv_frame()
        parse_write_response(frame, address=address, count=len(values))

    def close(self) -> None:
        sock, self._socket = self._socket, None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()

    def _next_transaction_id(self) -> int:
        self._transaction_id = (self._transaction_id % 0xFFFE) + 1
        return self._transaction_id

    def _send(self, payload: bytes) -> None:
        if self._socket is None:
            raise ConnectionError(f"RH56E2 {self.host}:{self.port} is not connected")
        self._socket.sendall(payload)

    def _recv_frame(self) -> bytes:
        header = self._recv_exact(7)
        _, protocol_id, length, _ = struct.unpack(">HHHB", header)
        if protocol_id != 0 or length < 2 or length > 260:
            raise ModbusProtocolError(f"invalid MBAP header: protocol={protocol_id}, length={length}")
        return header + self._recv_exact(length - 1)

    def _recv_exact(self, length: int) -> bytes:
        if self._socket is None:
            raise ConnectionError(f"RH56E2 {self.host}:{self.port} is not connected")
        data = bytearray()
        while len(data) < length:
            chunk = self._socket.recv(length - len(data))
            if not chunk:
                raise ConnectionError("RH56E2 closed the Modbus TCP connection")
            data.extend(chunk)
        return bytes(data)


def _parse_response(frame: bytes) -> tuple[int, bytes]:
    if len(frame) < 9:
        raise ModbusProtocolError(f"short Modbus TCP response: {len(frame)} bytes")
    transaction_id, protocol_id, length, _ = struct.unpack(">HHHB", frame[:7])
    if protocol_id != 0 or length != len(frame) - 6:
        raise ModbusProtocolError(
            f"invalid MBAP response: protocol={protocol_id}, length={length}, frame={len(frame)}"
        )
    # Some RH56 firmware revisions echo the transaction ID incorrectly. Keep
    # it for diagnostics, but do not use it as an acknowledgement gate.
    return transaction_id, frame[7:]


def _u8(value: object, name: str) -> int:
    parsed = int(value)
    if not 0 <= parsed <= 0xFF:
        raise ValueError(f"{name} must be in 0..255, got {value!r}")
    return parsed


def _u16(value: object, name: str) -> int:
    parsed = int(value)
    if not 0 <= parsed <= 0xFFFF:
        raise ValueError(f"{name} must be in 0..65535, got {value!r}")
    return parsed


def _register_value(value: object) -> int:
    parsed = int(value)
    if parsed == -1:
        return 0xFFFF
    return _u16(parsed, "register value")
