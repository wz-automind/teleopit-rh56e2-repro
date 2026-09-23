"""Safe public single-hand API for Inspire RH56E2 devices."""

from __future__ import annotations

from numbers import Integral
from typing import Sequence

from .models import DeviceSafetyError, RH56E2ConnectionError, RH56E2Telemetry, WriteDisabledError
from .protocol import (
    ANGLE_ACT,
    ANGLE_SET,
    CURRENT_ACT,
    FAULT_ACT,
    FORCE_ACT,
    SPEED_SET,
    STATE_ACT,
    TEMPERATURE_ACT,
    RH56E2ModbusClient,
)


class RH56E2Hand:
    """Connected RH56E2 hand with read-only telemetry access."""

    def __init__(
        self,
        host: str,
        port: int = 6000,
        *,
        unit_id: int = 0xFF,
        timeout: float = 0.5,
        write_enabled: bool = False,
        max_temperature_c: int = 70,
        client: RH56E2ModbusClient | None = None,
    ) -> None:
        if not isinstance(write_enabled, bool):
            raise TypeError(f"write_enabled must be a bool, got {write_enabled!r}")
        if not isinstance(max_temperature_c, Integral) or isinstance(max_temperature_c, bool):
            raise TypeError(f"max_temperature_c must be an integer, got {max_temperature_c!r}")
        self.host = str(host)
        self.port = int(port)
        self.unit_id = int(unit_id)
        self.timeout = float(timeout)
        self.write_enabled = write_enabled
        self.max_temperature_c = int(max_temperature_c)
        self._client = client or RH56E2ModbusClient(
            self.host, self.port, unit_id=self.unit_id, timeout=self.timeout
        )
        self._connected = False

    @property
    def endpoint(self) -> tuple[str, int]:
        """Network endpoint used to reach this hand."""
        return (self.host, self.port)

    def connect(self) -> None:
        """Connect to the hand. Repeated calls are harmless."""
        if self._connected:
            return
        self._client.connect()
        self._connected = True

    def close(self) -> None:
        """Close the hand connection. Repeated calls are harmless."""
        if not self._connected:
            return
        self._client.close()
        self._connected = False

    def __enter__(self) -> RH56E2Hand:
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def read_telemetry(self) -> RH56E2Telemetry:
        """Read an immutable six-channel telemetry snapshot."""
        self._require_connected()
        angle = self._read_six(ANGLE_ACT)
        force = tuple(_signed_16(value) for value in self._read_six(FORCE_ACT))
        current = self._read_six(CURRENT_ACT)
        fault = self._read_six(FAULT_ACT)
        state = self._read_six(STATE_ACT)
        temperature = self._read_six(TEMPERATURE_ACT)
        return RH56E2Telemetry(angle, force, current, fault, state, temperature)

    def set_speed(self, values: Sequence[int]) -> None:
        """Set six channel speeds after a fresh device-health check."""
        self._write_guarded(SPEED_SET, values, allow_hold=False)

    def set_positions(self, values: Sequence[int]) -> None:
        """Set six channel positions after a fresh device-health check."""
        self._write_guarded(ANGLE_SET, values, allow_hold=True)

    def _write_guarded(self, address: int, values: Sequence[int], *, allow_hold: bool) -> None:
        self._require_connected()
        if not self.write_enabled:
            raise WriteDisabledError("RH56E2 writes are disabled; construct with write_enabled=True to permit motion")
        command = _validate_command(values, allow_hold=allow_hold)
        self._require_healthy()
        self._client.write_holding(address, command)

    def _require_healthy(self) -> None:
        try:
            fault = self._read_six(FAULT_ACT)
            temperature = self._read_six(TEMPERATURE_ACT)
            if len(fault) != 6 or len(temperature) != 6:
                raise DeviceSafetyError("RH56E2 health check did not return six channels")
            if any(value != 0 for value in fault):
                raise DeviceSafetyError(f"RH56E2 write blocked by fault registers: {fault}")
            if any(value > self.max_temperature_c for value in temperature):
                raise DeviceSafetyError(
                    f"RH56E2 write blocked by temperature above {self.max_temperature_c} C: {temperature}"
                )
        except DeviceSafetyError:
            raise
        except Exception as exc:
            raise DeviceSafetyError("RH56E2 write blocked because device health is unreadable") from exc

    def _read_six(self, address: int) -> tuple[int, ...]:
        return tuple(self._client.read_holding(address, 6))

    def _require_connected(self) -> None:
        if not self._connected:
            raise RH56E2ConnectionError("RH56E2 hand is not connected; call connect() before use")


def _signed_16(value: int) -> int:
    return value - 0x10000 if value >= 0x8000 else value


def _validate_command(values: Sequence[int], *, allow_hold: bool) -> tuple[int, ...]:
    try:
        command = tuple(values)
    except TypeError as exc:
        raise TypeError("RH56E2 command must be a sequence of exactly six integers") from exc
    if len(command) != 6:
        raise ValueError(f"RH56E2 command must contain exactly six values, got {len(command)}")
    for value in command:
        if not isinstance(value, Integral) or isinstance(value, bool):
            raise TypeError(f"RH56E2 command values must be integers, got {value!r}")
        if allow_hold and value == -1:
            continue
        if not 0 <= value <= 1000:
            limit = "-1 or 0..1000" if allow_hold else "0..1000"
            raise ValueError(f"RH56E2 command values must be in {limit}, got {value!r}")
    return tuple(int(value) for value in command)
