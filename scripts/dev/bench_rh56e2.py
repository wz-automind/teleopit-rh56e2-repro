#!/usr/bin/env python3
"""Run the guarded single-hand RH56E2 bench-test entry point."""

import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
runpy.run_path(str(ROOT / "scripts" / "rh56e2_bench_test.py"), run_name="__main__")
