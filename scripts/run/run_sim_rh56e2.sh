#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/scripts/lib/conda_env.sh"
require_teleopit_conda

TELEOPIT_DIR="${TELEOPIT_DIR:-$HOME/Teleopit}"
ENTRYPOINT="$TELEOPIT_DIR/scripts/run/run_sim_rh56e2.py"

[[ -f "$ENTRYPOINT" ]] || { echo "Missing installed RH56E2 simulation entry point: $ENTRYPOINT" >&2; exit 2; }

cd "$TELEOPIT_DIR"
exec "$TELEOPIT_PYTHON" "$ENTRYPOINT" "$@"
