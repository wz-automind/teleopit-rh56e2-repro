#!/usr/bin/env bash
set -euo pipefail

TELEOPIT_DIR="${TELEOPIT_DIR:-$HOME/Teleopit}"
PYTHON="$TELEOPIT_DIR/.venv/bin/python"
ENTRYPOINT="$TELEOPIT_DIR/scripts/run/run_sim_rh56e2.py"

[[ -x "$PYTHON" ]] || { echo "Missing virtual environment: $PYTHON" >&2; exit 2; }
[[ -f "$ENTRYPOINT" ]] || { echo "Missing installed RH56E2 simulation entry point: $ENTRYPOINT" >&2; exit 2; }

cd "$TELEOPIT_DIR"
exec "$PYTHON" "$ENTRYPOINT" "$@"
