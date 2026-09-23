"""Deprecated RH56E2 protocol compatibility imports.

Use :mod:`teleopit_rh56e2.sdk` for new integrations.
"""

from __future__ import annotations

import warnings

from teleopit_rh56e2.sdk.models import ModbusProtocolError
from teleopit_rh56e2.sdk.protocol import (
    ANGLE_ACT,
    ANGLE_SET,
    CURRENT_ACT,
    FAULT_ACT,
    FORCE_ACT,
    SPEED_SET,
    STATE_ACT,
    TEMPERATURE_ACT,
    RH56E2ModbusClient,
    build_read_frame,
    build_write_frame,
    parse_read_response,
    parse_write_response,
)

warnings.warn(
    "teleopit.sim2real.hands.rh56e2_protocol is deprecated; use teleopit_rh56e2.sdk instead",
    DeprecationWarning,
    stacklevel=2,
)

Rh56e2ModbusClient = RH56E2ModbusClient

__all__ = [
    "ANGLE_SET",
    "SPEED_SET",
    "ANGLE_ACT",
    "FORCE_ACT",
    "CURRENT_ACT",
    "FAULT_ACT",
    "STATE_ACT",
    "TEMPERATURE_ACT",
    "ModbusProtocolError",
    "Rh56e2ModbusClient",
    "build_read_frame",
    "build_write_frame",
    "parse_read_response",
    "parse_write_response",
]
