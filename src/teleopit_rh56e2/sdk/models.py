"""Public exceptions for the RH56E2 SDK."""

from __future__ import annotations

from dataclasses import dataclass


class RH56E2Error(Exception):
    """Base class for errors raised by the RH56E2 SDK."""


class RH56E2ConnectionError(RH56E2Error, ConnectionError):
    """A socket could not be used to communicate with an RH56E2."""


class ModbusProtocolError(RH56E2Error, RuntimeError):
    """The device returned a malformed or exception Modbus response."""


class WriteDisabledError(RH56E2Error, PermissionError):
    """A write was requested without explicitly enabling hardware writes."""


class DeviceSafetyError(RH56E2Error, RuntimeError):
    """A device fault, temperature, or unreadable health check blocked a write."""


@dataclass(frozen=True)
class RH56E2Telemetry:
    """Immutable six-channel RH56E2 telemetry snapshot."""

    angle: tuple[int, ...]
    force: tuple[int, ...]
    current: tuple[int, ...]
    fault: tuple[int, ...]
    state: tuple[int, ...]
    temperature: tuple[int, ...]
