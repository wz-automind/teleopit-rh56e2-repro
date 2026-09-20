#!/usr/bin/env python3
"""Read-only installation and RH56E2 hardware preflight."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

TELEOPIT_COMMIT = "f9263865c581802ad531854b8e547e2403a945f3"
SOMEHAND_COMMIT = "f0a6b42e151ca10a6eec3e24c24c10cd13c40314"


def main() -> int:
    parser = argparse.ArgumentParser(description="Teleopit + RH56E2 read-only preflight")
    parser.add_argument("--teleopit-dir", type=Path, default=Path.home() / "Teleopit")
    parser.add_argument("--somehand-dir", type=Path, default=None)
    parser.add_argument("--profile", choices=("sim", "pico", "real"), default="sim")
    parser.add_argument("--hardware", action="store_true", help="connect and read hand telemetry; never writes")
    parser.add_argument("--left-host")
    parser.add_argument("--right-host")
    parser.add_argument("--port", type=int, default=6000)
    parser.add_argument("--unit-id", type=lambda value: int(value, 0), default=0xFF)
    parser.add_argument("--timeout", type=float, default=0.8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    teleopit = args.teleopit_dir.expanduser().resolve()
    somehand = (args.somehand_dir or teleopit / "third_party" / "somehand").expanduser().resolve()
    checks: list[dict[str, Any]] = []

    check(checks, "python", sys.version_info >= (3, 10), f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    check(checks, "teleopit directory", teleopit.is_dir(), str(teleopit))
    check(checks, "somehand directory", somehand.is_dir(), str(somehand))
    if (teleopit / ".git").exists():
        check(checks, "Teleopit pin", git_head(teleopit).startswith(TELEOPIT_COMMIT), git_head(teleopit))
    if (somehand / ".git").exists():
        check(checks, "somehand pin", git_head(somehand).startswith(SOMEHAND_COMMIT), git_head(somehand))

    required = (
        teleopit / "teleopit" / "configs" / "pico4_sim_rh56e2.yaml",
        teleopit / "teleopit" / "configs" / "pico4_sim2real_rh56e2.yaml",
        teleopit / "teleopit" / "sim2real" / "hands" / "rh56e2.py",
        teleopit / "assets" / "robots" / "unitree_g1" / "g1_29dof_rh56e2.xml",
        somehand / "configs" / "retargeting" / "bihand" / "inspire_rh56e2_bihand.yaml",
        teleopit / "ckpt" / "track_g1.onnx",
    )
    for path in required:
        check(checks, f"file {path.name}", path.is_file(), str(path))

    for module in ("numpy", "mujoco", "hydra", "onnxruntime"):
        check(checks, f"module {module}", importlib.util.find_spec(module) is not None, "installed" if importlib.util.find_spec(module) else "missing")
    if args.profile in ("pico", "real"):
        check(checks, "module pico_bridge", importlib.util.find_spec("pico_bridge") is not None, "required for Pico input")
    if args.profile == "real":
        check(checks, "module g1_bridge_sdk", importlib.util.find_spec("g1_bridge_sdk") is not None, "required for G1 body control")

    hosts = [("left", args.left_host), ("right", args.right_host)]
    selected = [(side, host) for side, host in hosts if host]
    if args.hardware:
        check(checks, "hardware endpoint supplied", bool(selected), "use --left-host and/or --right-host")
        endpoint_values = [(host, args.port) for _, host in selected]
        check(checks, "unique hand endpoints", len(set(endpoint_values)) == len(endpoint_values), str(endpoint_values))
        driver_path = teleopit / "teleopit" / "sim2real" / "hands" / "rh56e2.py"
        if selected and driver_path.is_file():
            add_overlay_paths(teleopit)
            from teleopit.sim2real.hands.rh56e2 import (  # type: ignore
                ANGLE_ACT,
                CURRENT_ACT,
                FAULT_ACT,
                FORCE_ACT,
                STATE_ACT,
                TEMPERATURE_ACT,
                Rh56e2ModbusClient,
            )

            for side, host in selected:
                client = Rh56e2ModbusClient(host, args.port, unit_id=args.unit_id, timeout_s=args.timeout)
                try:
                    client.connect()
                    diagnostics = {
                        "angle": client.read_holding(ANGLE_ACT, 6),
                        "force": client.read_holding(FORCE_ACT, 6),
                        "current": client.read_holding(CURRENT_ACT, 6),
                        "fault": tuple(client.read_bytes(FAULT_ACT, 6)),
                        "state": tuple(client.read_bytes(STATE_ACT, 6)),
                        "temperature": tuple(client.read_bytes(TEMPERATURE_ACT, 6)),
                    }
                    safe = not any(diagnostics["fault"]) and max(diagnostics["temperature"]) <= 70
                    check(checks, f"{side} hand telemetry", safe, diagnostics)
                except (OSError, RuntimeError, ValueError) as exc:
                    check(checks, f"{side} hand telemetry", False, f"{type(exc).__name__}: {exc}")
                finally:
                    client.close()

    passed = all(item["ok"] for item in checks)
    if args.json:
        print(json.dumps({"ok": passed, "checks": checks, "writes_performed": False}, ensure_ascii=False, indent=2))
    else:
        for item in checks:
            print(f"[{'PASS' if item['ok'] else 'FAIL'}] {item['name']}: {item['detail']}")
        print("PASS: read-only preflight completed; no Modbus write was sent." if passed else "FAIL: fix the failed checks before continuing.")
    return 0 if passed else 1


def add_overlay_paths(teleopit: Path) -> None:
    sys.path.insert(0, str(teleopit))


def git_head(directory: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(directory), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def check(items: list[dict[str, Any]], name: str, ok: bool, detail: Any) -> None:
    items.append({"name": name, "ok": bool(ok), "detail": detail})


if __name__ == "__main__":
    raise SystemExit(main())
