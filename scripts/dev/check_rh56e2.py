#!/usr/bin/env python3
"""Run the repository's read-only RH56E2 preflight entry point."""

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
runpy.run_path(str(ROOT / "scripts" / "rh56e2_preflight.py"), run_name="__main__")
