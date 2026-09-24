"""Dependency-free Modbus TCP framing and transport for RH56E2 hands."""

from __future__ import annotations

import math
import socket
import struct
import threading
import warnings
from numbers import Integral
from typing import Callable, Sequence

from .models import (
    ModbusProtocolError,
    RH56E2ConnectionError,
    _RH56E2TypeValidationError,
    _RH56E2ValueValidationError,
)

ANGLE_SET = 1486
SPEED_SET = 1522
ANGLE_ACT = 1546
FORCE_ACT = 1582
CURRENT_ACT = 1594
FAULT_ACT = 1606
STATE_ACT = 1612
TEMPERATURE_ACT = 1618


def build_read_frame(transaction_id: int, unit_id: int, address: int, count: int) -> bytes:
    if not isinstance(count, Integral) or isinstance(count, bool):
        raise _RH56E2TypeValidationError(f"Modbus read count must be an integer, got {count!r}")
    if not 1 <= count <= 125:
        raise _RH56E2ValueValidationError(f"Modbus read count must be in 1..125, got {count}")
    pdu = struct.pack(">BHH", 0x03, _u16(address, "address"), count)
    return struct.pack(">HHHB", transaction_id & 0xFFFF, 0, len(pdu) + 1, _u8(unit_id, "unit_id")) + pdu


def build_write_frame(transaction_id: int, unit_id: int, address: int, values: Sequence[int]) -> bytes:
    encoded = tuple(_register_value(value) for value in values)
    if not 1 <= len(encoded) <= 123:
        raise _RH56E2ValueValidationError(f"Modbus write count must be in 1..123, got {len(encoded)}")
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


class RH56E2ModbusClient:
    """Small synchronous Modbus TCP client with complete response draining."""

    def __init__(
        self,
        host: str,
        port: int = 6000,
        *,
        unit_id: int = 0xFF,
        timeout: float = 0.5,
        timeout_s: float | None = None,
        socket_factory: Callable[..., socket.socket] = socket.socket,
    ):
        if timeout_s is not None:
            warnings.warn(
                "timeout_s is deprecated; use timeout instead",
                DeprecationWarning,
                stacklevel=2,
            )
            timeout = timeout_s
        if not isinstance(port, Integral) or isinstance(port, bool):
            raise _RH56E2TypeValidationError(f"port must be an integer, got {port!r}")
        if not 1 <= port <= 65535:
            raise _RH56E2ValueValidationError(f"port must be in 1..65535, got {port!r}")
        if not isinstance(unit_id, Integral) or isinstance(unit_id, bool):
            raise _RH56E2TypeValidationError(f"unit_id must be an integer, got {unit_id!r}")
        if not 0 <= unit_id <= 0xFF:
            raise _RH56E2ValueValidationError(f"unit_id must be in 0..255, got {unit_id!r}")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise _RH56E2TypeValidationError(f"timeout must be a finite positive number, got {timeout!r}")
        if not math.isfinite(timeout) or timeout <= 0:
            raise _RH56E2ValueValidationError(f"timeout must be a finite positive number, got {timeout!r}")
        self.host = str(host)
        self.port = int(port)
        self.unit_id = int(unit_id)
        self.timeout = float(timeout)
        self._socket_factory = socket_factory
        self._socket: socket.socket | None = None
        self._transaction_id = 0
        self._lock = threading.Lock()

    @property
    def timeout_s(self) -> float:
        """Deprecated alias for :attr:`timeout`."""
        warnings.warn(
            "timeout_s is deprecated; use timeout instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.timeout

    def connect(self) -> None:
        if self._socket is not None:
            return
        sock: socket.socket | None = None
        try:
            if self._socket_factory is socket.socket:
                sock = self._socket_factory(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
            else:
                sock = self._socket_factory((self.host, self.port), timeout=self.timeout)
                sock.settimeout(self.timeout)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except (OSError, TimeoutError) as exc:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
            raise RH56E2ConnectionError(f"failed to connect to RH56E2 {self.host}:{self.port}: {exc}") from exc
        self._socket = sock

    def read_holding(self, address: int, count: int) -> tuple[int, ...]:
        with self._lock:
            transaction_id = self._next_transaction_id()
            request = build_read_frame(transaction_id, self.unit_id, address, count)
            self._send(request)
            frame = self._recv_frame()
        return parse_read_response(frame, count=count)

    def read_bytes(self, address: int, byte_count: int) -> bytes:
        if not isinstance(byte_count, Integral) or isinstance(byte_count, bool):
            raise _RH56E2TypeValidationError("byte_count must be a positive integer")
        if byte_count <= 0:
            raise _RH56E2ValueValidationError("byte_count must be positive")
        register_count = (byte_count + 1) // 2
        values = self.read_holding(address, register_count)
        payload = struct.pack(">" + "H" * len(values), *values)
        return payload[:byte_count]

    def write_holding(self, address: int, values: Sequence[int]) -> None:
        with self._lock:
            transaction_id = self._next_transaction_id()
            command = tuple(values)
            request = build_write_frame(transaction_id, self.unit_id, address, command)
            self._send(request)
            frame = self._recv_frame()
        parse_write_response(frame, address=address, count=len(command))

    def close(self) -> None:
        sock, self._socket = self._socket, None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def _next_transaction_id(self) -> int:
        self._transaction_id = (self._transaction_id % 0xFFFE) + 1
        return self._transaction_id

    def _send(self, payload: bytes) -> None:
        if self._socket is None:
            raise RH56E2ConnectionError(f"RH56E2 {self.host}:{self.port} is not connected")
        try:
            self._socket.sendall(payload)
        except (OSError, TimeoutError) as exc:
            raise RH56E2ConnectionError(f"failed to send to RH56E2 {self.host}:{self.port}: {exc}") from exc

    def _recv_frame(self) -> bytes:
        header = self._recv_exact(7)
        _, protocol_id, length, _ = struct.unpack(">HHHB", header)
        if protocol_id != 0 or length < 2 or length > 260:
            raise ModbusProtocolError(f"invalid MBAP header: protocol={protocol_id}, length={length}")
        return header + self._recv_exact(length - 1)

    def _recv_exact(self, length: int) -> bytes:
        if self._socket is None:
            raise RH56E2ConnectionError(f"RH56E2 {self.host}:{self.port} is not connected")
        data = bytearray()
        while len(data) < length:
            try:
                chunk = self._socket.recv(length - len(data))
            except (OSError, TimeoutError) as exc:
                raise RH56E2ConnectionError(f"failed to receive from RH56E2 {self.host}:{self.port}: {exc}") from exc
            if not chunk:
                raise RH56E2ConnectionError("RH56E2 closed the Modbus TCP connection")
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
    return transaction_id, frame[7:]


def _u8(value: object, name: str) -> int:
    if not isinstance(value, Integral) or isinstance(value, bool):
        raise _RH56E2TypeValidationError(f"{name} must be an integer, got {value!r}")
    parsed = int(value)
    if not 0 <= parsed <= 0xFF:
        raise _RH56E2ValueValidationError(f"{name} must be in 0..255, got {value!r}")
    return parsed


def _u16(value: object, name: str) -> int:
    if not isinstance(value, Integral) or isinstance(value, bool):
        raise _RH56E2TypeValidationError(f"{name} must be an integer, got {value!r}")
    parsed = int(value)
    if not 0 <= parsed <= 0xFFFF:
        raise _RH56E2ValueValidationError(f"{name} must be in 0..65535, got {value!r}")
    return parsed


def _register_value(value: object) -> int:
    if not isinstance(value, Integral) or isinstance(value, bool):
        raise _RH56E2TypeValidationError(f"register value must be an integer, got {value!r}")
    parsed = int(value)
    if parsed == -1:
        return 0xFFFF
    return _u16(parsed, "register value")
