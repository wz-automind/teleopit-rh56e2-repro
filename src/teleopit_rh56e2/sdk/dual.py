"""Thin lifecycle and command composition for a pair of RH56E2 hands."""

from __future__ import annotations

from typing import Sequence

from .hand import RH56E2Hand
from .models import RH56E2Telemetry


class RH56E2Pair:
    """Manage explicitly named left and right RH56E2 hands."""

    def __init__(self, left: RH56E2Hand, right: RH56E2Hand) -> None:
        if left.endpoint == right.endpoint:
            raise ValueError("left and right RH56E2 endpoints must be distinct")
        self.left = left
        self.right = right

    def connect(self) -> None:
        """Connect left then right, rolling back left if right fails."""
        self.left.connect()
        try:
            self.right.connect()
        except Exception as connect_error:
            try:
                self.left.close()
            except Exception:
                pass
            raise connect_error

    def close(self) -> None:
        """Close both hands, preserving the first close error if any."""
        first_error: Exception | None = None
        try:
            self.left.close()
        except Exception as error:
            first_error = error
        try:
            self.right.close()
        except Exception as error:
            if first_error is None:
                first_error = error
        if first_error is not None:
            raise first_error

    def __enter__(self) -> RH56E2Pair:
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def read_telemetry(self) -> dict[str, RH56E2Telemetry]:
        """Read both hands and retain their explicit left/right labels."""
        return {"left": self.left.read_telemetry(), "right": self.right.read_telemetry()}

    def set_speeds(self, *, left: Sequence[int], right: Sequence[int]) -> None:
        """Delegate each speed command to its corresponding hand."""
        self.left.set_speed(left)
        self.right.set_speed(right)

    def set_positions(self, *, left: Sequence[int], right: Sequence[int]) -> None:
        """Delegate each position command to its corresponding hand."""
        self.left.set_positions(left)
        self.right.set_positions(right)
