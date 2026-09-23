#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/scripts/lib/conda_env.sh"
require_teleopit_conda

TELEOPIT_DIR="${TELEOPIT_DIR:-$HOME/Teleopit}"
NETWORK_INTERFACE="${NETWORK_INTERFACE:-eth1}"
G1_HOST_IP="${G1_HOST_IP:-192.168.123.164}"
LEFT_HAND_IP="${LEFT_HAND_IP:-192.168.123.210}"
RIGHT_HAND_IP="${RIGHT_HAND_IP:-192.168.123.211}"
HAND_PORT="${HAND_PORT:-6000}"
PICO_ADVERTISE_IP="${PICO_ADVERTISE_IP:-192.168.50.62}"

if [[ ! -d "/sys/class/net/$NETWORK_INTERFACE" ]]; then
  echo "Network interface does not exist: $NETWORK_INTERFACE" >&2
  exit 2
fi

if [[ "$LEFT_HAND_IP" == "$RIGHT_HAND_IP" ]]; then
  echo "Left and right RH56E2 addresses must be different." >&2
  exit 2
fi

echo "Verified deployment profile:"
echo "  G1 host/control interface: $G1_HOST_IP via $NETWORK_INTERFACE"
echo "  RH56E2 left/right: $LEFT_HAND_IP:$HAND_PORT / $RIGHT_HAND_IP:$HAND_PORT"
echo "  PICO advertise IP: $PICO_ADVERTISE_IP"

if ! ip -o -4 addr show dev "$NETWORK_INTERFACE" | grep -Fq " $G1_HOST_IP/"; then
  echo "$NETWORK_INTERFACE does not own the expected host address $G1_HOST_IP." >&2
  exit 2
fi

for endpoint in "$LEFT_HAND_IP" "$RIGHT_HAND_IP"; do
  route="$(ip route get "$endpoint" 2>/dev/null || true)"
  if [[ -z "$route" || "$route" != *"dev $NETWORK_INTERFACE"* ]]; then
    echo "No route to $endpoint through $NETWORK_INTERFACE: ${route:-not found}" >&2
    exit 2
  fi
done

exec "$TELEOPIT_PYTHON" "$ROOT_DIR/scripts/rh56e2_preflight.py" \
  --teleopit-dir "$TELEOPIT_DIR" --profile real --hardware \
  --left-host "$LEFT_HAND_IP" --right-host "$RIGHT_HAND_IP" --port "$HAND_PORT" \
  "$@"
