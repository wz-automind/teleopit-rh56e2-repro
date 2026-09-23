#!/usr/bin/env python3
"""Guarded, single-DOF RH56E2 bench test.

The default invocation is read-only. Motion requires both ``--write`` and the
exact confirmation phrase so that copying the inspection command cannot move a
hand accidentally.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
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

        from teleopit_rh56e2.sdk import RH56E2Hand

        hand = RH56E2Hand(
            args.host,
            args.port,
            unit_id=args.unit_id,
            timeout=args.timeout,
            write_enabled=args.write,
            max_temperature_c=args.max_temperature_c,
        )
        try:
            hand.connect()
            initial = hand.read_telemetry()
            report("initial", initial.angle, initial.fault, initial.temperature)

            if not args.write:
                print("READ-ONLY: telemetry read completed; no Modbus write was sent.")
                return 0

            index = DOF_ORDER.index(args.dof)
            target = bounded_target(initial.angle[index], args.delta)
            if target == initial.angle[index]:
                raise RuntimeError("refusing motion: target is unchanged after range clamping")

            restore = [-1] * 6
            restore[index] = initial.angle[index]
            move_attempted = False
            try:
                hand.set_speed([args.speed] * 6)
                move = [-1] * 6
                move[index] = target
                move_attempted = True
                hand.set_positions(move)
                time.sleep(args.settle_s)
                moved = hand.read_telemetry()
                report("moved", moved.angle, moved.fault, moved.temperature)
            finally:
                if move_attempted:
                    hand.set_positions(restore)
                    time.sleep(args.settle_s)
                    restored = hand.read_telemetry()
                    report("restored", restored.angle, restored.fault, restored.temperature)
            print(f"PASS: {args.dof} moved from {initial.angle[index]} toward {target} and was commanded back to {initial.angle[index]}.")
            return 0
        finally:
            hand.close()
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
