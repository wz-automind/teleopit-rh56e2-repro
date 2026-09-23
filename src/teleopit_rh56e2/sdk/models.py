"""Public exceptions for the RH56E2 SDK."""

from __future__ import annotations


class RH56E2Error(Exception):
    """Base class for errors raised by the RH56E2 SDK."""


class RH56E2ConnectionError(RH56E2Error, ConnectionError):
    """A socket could not be used to communicate with an RH56E2."""


class ModbusProtocolError(RH56E2Error, RuntimeError):
    """The device returned a malformed or exception Modbus response."""
