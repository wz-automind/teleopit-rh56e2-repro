#!/usr/bin/env python3
"""Guarded, single-DOF RH56E2 bench test.

The default invocation is read-only. Motion requires both ``--write`` and the
exact confirmation phrase so that copying the inspection command cannot move a
hand accidentally.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Sequence

DOF_ORDER = ("pinky", "ring", "middle", "index", "thumb_bend", "thumb_rotation")
CONFIRM_PHRASE = "MOVE_RH56E2"
MIN_COMMAND = 0
MAX_COMMAND = 1000
MAX_DELTA = 100


def bounded_target(current: int, delta: int) -> int:
    """Return a controller-unit target clamped to the RH56E2 range."""
    return max(MIN_COMMAND, min(MAX_COMMAND, int(current) + int(delta)))


def validate_delta(delta: int) -> None:
    if delta == 0 or abs(delta) > MAX_DELTA:
        raise ValueError(f"--delta must be non-zero and within +/-{MAX_DELTA}")


def authorize_motion(write: bool, confirm: str) -> None:
    if not write:
        raise ValueError("motion requires --write")
    if confirm != CONFIRM_PHRASE:
        raise ValueError(f"motion requires --confirm {CONFIRM_PHRASE}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read RH56E2 telemetry, or perform one guarded low-speed relative move"
    )
    parser.add_argument("--teleopit-dir", type=Path, default=Path.home() / "Teleopit")
    parser.add_argument("--host", required=True, help="IP address of one isolated hand")
    parser.add_argument("--port", type=int, default=6000)
    parser.add_argument("--unit-id", type=lambda value: int(value, 0), default=0xFF)
    parser.add_argument("--timeout", type=float, default=0.8)
    parser.add_argument("--dof", choices=DOF_ORDER, default="index")
    parser.add_argument("--delta", type=int, default=50, help="relative controller units, max +/-100")
    parser.add_argument("--speed", type=int, default=50, help="low test speed, range 1..200")
    parser.add_argument("--settle-s", type=float, default=1.0)
    parser.add_argument("--max-temperature-c", type=int, default=60)
    parser.add_argument("--write", action="store_true", help="allow the guarded motion sequence")
    parser.add_argument("--confirm", default="", help=f"must be exactly {CONFIRM_PHRASE}")
    return parser


def validate_arguments(args: argparse.Namespace) -> None:
    validate_delta(args.delta)
    if not 1 <= args.speed <= 200:
        raise ValueError("--speed must be in 1..200")
    if not 0.2 <= args.settle_s <= 5.0:
        raise ValueError("--settle-s must be in 0.2..5.0")
    if not 1 <= args.port <= 65535:
        raise ValueError("--port must be in 1..65535")


def report(label: str, angles: Sequence[int], faults: Sequence[int], temperatures: Sequence[int]) -> None:
    print(json.dumps({
        "stage": label,
        "dof_order": DOF_ORDER,
        "angle": list(angles),
        "fault": list(faults),
        "temperature_c": list(temperatures),
    }, ensure_ascii=False))


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        validate_arguments(args)
        if args.write:
            authorize_motion(args.write, args.confirm)

        teleopit = args.teleopit_dir.expanduser().resolve()
        sys.path.insert(0, str(teleopit))
        from teleopit.sim2real.hands.rh56e2 import (  # type: ignore
            ANGLE_ACT,
            ANGLE_SET,
            FAULT_ACT,
            SPEED_SET,
            TEMPERATURE_ACT,
            Rh56e2ModbusClient,
        )

        client = Rh56e2ModbusClient(args.host, args.port, unit_id=args.unit_id, timeout_s=args.timeout)
        try:
            client.connect()
            initial = client.read_holding(ANGLE_ACT, 6)
            faults = tuple(client.read_bytes(FAULT_ACT, 6))
            temperatures = tuple(client.read_bytes(TEMPERATURE_ACT, 6))
            report("initial", initial, faults, temperatures)

            if not args.write:
                print("READ-ONLY: telemetry read completed; no Modbus write was sent.")
                return 0
            if any(faults):
                raise RuntimeError(f"refusing motion: non-zero fault bytes {faults}")
            if max(temperatures) > args.max_temperature_c:
                raise RuntimeError(
                    f"refusing motion: maximum temperature {max(temperatures)} C exceeds "
                    f"{args.max_temperature_c} C"
                )

            index = DOF_ORDER.index(args.dof)
            target = bounded_target(initial[index], args.delta)
            if target == initial[index]:
                raise RuntimeError("refusing motion: target is unchanged after range clamping")

            restore = [-1] * 6
            restore[index] = initial[index]
            move_attempted = False
            try:
                client.write_holding(SPEED_SET, [args.speed] * 6)
                move = [-1] * 6
                move[index] = target
                move_attempted = True
                client.write_holding(ANGLE_SET, move)
                time.sleep(args.settle_s)
                moved = client.read_holding(ANGLE_ACT, 6)
                report("moved", moved, tuple(client.read_bytes(FAULT_ACT, 6)), tuple(client.read_bytes(TEMPERATURE_ACT, 6)))
            finally:
                if move_attempted:
                    client.write_holding(ANGLE_SET, restore)
                    time.sleep(args.settle_s)
                    restored = client.read_holding(ANGLE_ACT, 6)
                    report("restored", restored, tuple(client.read_bytes(FAULT_ACT, 6)), tuple(client.read_bytes(TEMPERATURE_ACT, 6)))
            print(f"PASS: {args.dof} moved from {initial[index]} toward {target} and was commanded back to {initial[index]}.")
            return 0
        finally:
            client.close()
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
