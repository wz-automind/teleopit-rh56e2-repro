#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/conda_env.sh"
require_teleopit_conda

TELEOPIT_DIR="${TELEOPIT_DIR:-$HOME/Teleopit}"
LEFT_HAND_IP="${LEFT_HAND_IP:-}"
RIGHT_HAND_IP="${RIGHT_HAND_IP:-}"
HAND_PORT="${HAND_PORT:-6000}"
NETWORK_INTERFACE="${NETWORK_INTERFACE:-eth1}"

if [[ "${ENABLE_G1_REAL:-}" != "YES" || "${ENABLE_RH56E2_WRITES:-}" != "YES" ]]; then
  echo "Refusing to start real control. Set ENABLE_G1_REAL=YES and ENABLE_RH56E2_WRITES=YES after completing the acceptance checklist." >&2
  exit 2
fi
if [[ -z "$LEFT_HAND_IP" || -z "$RIGHT_HAND_IP" || "$LEFT_HAND_IP" == "$RIGHT_HAND_IP" ]]; then
  echo "LEFT_HAND_IP and RIGHT_HAND_IP must be set to two different RH56E2 addresses." >&2
  exit 2
fi

"$TELEOPIT_PYTHON" "$ROOT_DIR/scripts/rh56e2_preflight.py" \
  --teleopit-dir "$TELEOPIT_DIR" --profile real --hardware \
  --left-host "$LEFT_HAND_IP" --right-host "$RIGHT_HAND_IP" --port "$HAND_PORT"

cd "$TELEOPIT_DIR"
exec "$TELEOPIT_PYTHON" scripts/run/run_sim2real.py \
  --config-name pico4_sim2real_rh56e2 \
  "controller.policy_path=ckpt/track_g1.onnx" \
  "real_robot.network_interface=$NETWORK_INTERFACE" \
  "hands.rh56e2.left_host=$LEFT_HAND_IP" \
  "hands.rh56e2.right_host=$RIGHT_HAND_IP" \
  "hands.rh56e2.port=$HAND_PORT" \
  "hands.rh56e2.write_enabled=true" \
  "$@"
