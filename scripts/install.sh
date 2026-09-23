#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/lib/conda_env.sh"

TELEOPIT_DIR="${TELEOPIT_DIR:-$HOME/Teleopit}"
SOMEHAND_DIR="${SOMEHAND_DIR:-$TELEOPIT_DIR/third_party/somehand}"
TELEOPIT_COMMIT="f9263865c581802ad531854b8e547e2403a945f3"
SOMEHAND_COMMIT="f0a6b42e151ca10a6eec3e24c24c10cd13c40314"
PICO_APK_URL="https://github.com/BotRunner64/pico-bridge/releases/download/v0.2.1/PicoBridge_v0.2.1_20260522_release.apk"
PICO_APK_SHA256="ab96ad856ca737999723d4e50f8e5d4b20c5570f7f74000d5799dc656cc2c0d5"

PROFILE="sim"
ASSET_SOURCE="modelscope"
SKIP_ASSETS=0
DOWNLOAD_APK=0

usage() {
  cat <<'EOF'
Usage: scripts/install.sh [options]
  --profile sim|real              Install simulation/Pico runtime or add G1 bridge (default: sim)
  --asset-source modelscope|huggingface
  --skip-assets                   Do not download robot, GMR, checkpoint and BVH assets
  --download-pico-apk             Download and verify pico-bridge v0.2.1 APK
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --asset-source) ASSET_SOURCE="$2"; shift 2 ;;
    --skip-assets) SKIP_ASSETS=1; shift ;;
    --download-pico-apk) DOWNLOAD_APK=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$PROFILE" == "sim" || "$PROFILE" == "real" ]] || { echo "Invalid --profile: $PROFILE" >&2; exit 2; }
[[ "$ASSET_SOURCE" == "modelscope" || "$ASSET_SOURCE" == "huggingface" ]] || { echo "Invalid --asset-source: $ASSET_SOURCE" >&2; exit 2; }
require_teleopit_conda

clone_at() {
  local dir="$1" repository="$2" commit="$3"
  if [[ ! -d "$dir/.git" ]]; then
    mkdir -p "$(dirname "$dir")"
    git clone "$repository" "$dir"
  elif [[ -n "$(git -C "$dir" status --porcelain)" && ! -f "$dir/.rh56e2-overlay" ]]; then
    echo "Refusing to modify dirty upstream checkout: $dir" >&2
    exit 3
  fi
  git -C "$dir" fetch --quiet origin "$commit"
  git -C "$dir" checkout --quiet --detach "$commit"
  local actual
  actual="$(git -C "$dir" rev-parse HEAD)"
  [[ "$actual" == "$commit" ]] || { echo "Commit verification failed for $dir: $actual" >&2; exit 3; }
}

clone_at "$TELEOPIT_DIR" "https://github.com/BotRunner64/Teleopit.git" "$TELEOPIT_COMMIT"
clone_at "$SOMEHAND_DIR" "https://github.com/BotRunner64/somehand.git" "$SOMEHAND_COMMIT"

copy_tree() {
  local src="$1" dst="$2"
  mkdir -p "$dst"
  cp -a "$src"/. "$dst"/
}

copy_tree "$ROOT_DIR/overlay/teleopit" "$TELEOPIT_DIR/teleopit"
copy_tree "$ROOT_DIR/overlay/scripts" "$TELEOPIT_DIR/scripts"
copy_tree "$ROOT_DIR/overlay/assets" "$TELEOPIT_DIR/assets"
copy_tree "$ROOT_DIR/overlay/third_party/somehand" "$SOMEHAND_DIR"
printf '%s\n' "$TELEOPIT_COMMIT" > "$TELEOPIT_DIR/.rh56e2-overlay"
printf '%s\n' "$SOMEHAND_COMMIT" > "$SOMEHAND_DIR/.rh56e2-overlay"

"$TELEOPIT_PYTHON" -m pip install --upgrade pip setuptools wheel
"$TELEOPIT_PYTHON" -m pip install -e "$TELEOPIT_DIR[pico4]"
"$TELEOPIT_PYTHON" -m pip install -e "$SOMEHAND_DIR"
"$TELEOPIT_PYTHON" -m pip install -e "$ROOT_DIR" --no-deps

if [[ "$SKIP_ASSETS" -eq 0 ]]; then
  (
    cd "$TELEOPIT_DIR"
    "$TELEOPIT_PYTHON" scripts/setup/download_assets.py \
      --source "$ASSET_SOURCE" --only robots gmr ckpt bvh
  )
fi

if [[ "$PROFILE" == "real" ]]; then
  (
    cd "$TELEOPIT_DIR"
    bash scripts/setup/setup_g1_bridge.sh
  )
fi

if [[ "$DOWNLOAD_APK" -eq 1 ]]; then
  mkdir -p "$ROOT_DIR/downloads"
  APK="$ROOT_DIR/downloads/PicoBridge_v0.2.1_20260522_release.apk"
  if command -v curl >/dev/null 2>&1; then
    curl -fL "$PICO_APK_URL" -o "$APK"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$APK" "$PICO_APK_URL"
  else
    echo "curl or wget is required to download the PICO APK" >&2
    exit 4
  fi
  echo "$PICO_APK_SHA256  $APK" | sha256sum --check --status
  echo "Verified PICO APK: $APK"
fi

chmod +x "$TELEOPIT_DIR/scripts/run/run_sim_rh56e2.py" 2>/dev/null || true
echo "Installed RH56E2 overlay in $TELEOPIT_DIR"
echo "Next: TELEOPIT_DIR='$TELEOPIT_DIR' bash '$ROOT_DIR/scripts/validate.sh'"
