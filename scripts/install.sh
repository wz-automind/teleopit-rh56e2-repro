#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TELEOPIT_DIR="${TELEOPIT_DIR:-$HOME/Teleopit}"
SOMEHAND_DIR="${SOMEHAND_DIR:-$TELEOPIT_DIR/third_party/somehand}"
TELEOPIT_COMMIT="f926386"
SOMEHAND_COMMIT="f0a6b42e151ca10a6eec3e24c24c10cd13c40314"

clone_at() {
  local dir="$1" url="$2" commit="$3"
  if [[ ! -d "$dir/.git" ]]; then
    mkdir -p "$(dirname "$dir")"
    git clone https://github.com/BotRunner64/"$url".git "$dir"
  fi
  git -C "$dir" fetch --quiet --all --tags
  git -C "$dir" checkout --quiet "$commit"
}

clone_at "$TELEOPIT_DIR" Teleopit "$TELEOPIT_COMMIT"
clone_at "$SOMEHAND_DIR" somehand "$SOMEHAND_COMMIT"

copy_tree() {
  local src="$1" dst="$2"
  mkdir -p "$dst"
  cp -a "$src"/. "$dst"/
}

copy_tree "$ROOT_DIR/overlay/teleopit" "$TELEOPIT_DIR/teleopit"
copy_tree "$ROOT_DIR/overlay/scripts" "$TELEOPIT_DIR/scripts"
copy_tree "$ROOT_DIR/overlay/assets" "$TELEOPIT_DIR/assets"
copy_tree "$ROOT_DIR/overlay/third_party/somehand" "$SOMEHAND_DIR"

chmod +x "$TELEOPIT_DIR/scripts/run/run_sim_rh56e2.py" 2>/dev/null || true
echo "RH56E2 overlay installed. TELEOPIT_DIR=$TELEOPIT_DIR"
