#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TELEOPIT_DIR="${TELEOPIT_DIR:-$HOME/Teleopit}"
SOMEHAND_DIR="${SOMEHAND_DIR:-$TELEOPIT_DIR/third_party/somehand}"
PYTHON="${PYTHON:-$TELEOPIT_DIR/.venv/bin/python}"

[[ -x "$PYTHON" ]] || { echo "Missing Python environment: $PYTHON" >&2; exit 2; }
cd "$TELEOPIT_DIR"
export PYTHONPATH="$SOMEHAND_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

"$PYTHON" -m py_compile \
  teleopit/pipeline_rh56e2.py \
  teleopit/robots/mujoco_robot_rh56e2.py \
  teleopit/sim/loop_rh56e2.py \
  teleopit/sim/session_rh56e2.py \
  teleopit/sim/rh56e2_hands.py \
  teleopit/sim2real/hands/rh56e2_protocol.py \
  teleopit/sim2real/hands/rh56e2.py \
  teleopit/sim2real/hands/worker.py \
  scripts/run/run_sim_rh56e2.py \
  "$ROOT_DIR/scripts/rh56e2_preflight.py" \
  "$ROOT_DIR/scripts/dev/check_rh56e2.py" \
  "$ROOT_DIR/scripts/dev/bench_rh56e2.py"

"$PYTHON" -m unittest discover -s "$ROOT_DIR/tests" -v

"$PYTHON" -c "from pathlib import Path; import mujoco; p=Path('assets/robots/unitree_g1/g1_29dof_rh56e2.xml'); m=mujoco.MjModel.from_xml_path(str(p)); assert m.nu >= 41, m.nu; print(f'Model OK: nq={m.nq} nv={m.nv} nu={m.nu}')"

"$PYTHON" -c "from pathlib import Path; from hydra import compose,initialize_config_dir; from teleopit.robots.mujoco_robot_rh56e2 import MuJoCoRobotRh56e2; d=str(Path('teleopit/configs').resolve()); c=initialize_config_dir(config_dir=d,version_base=None); c.__enter__(); cfg=compose(config_name='pico4_sim_rh56e2'); r=MuJoCoRobotRh56e2(cfg.robot); r.step(); assert r.data.ncon == 0, r.data.ncon; [r.step() for _ in range(999)]; print('Stability OK: 1000 steps'); c.__exit__(None,None,None)"

"$PYTHON" "$ROOT_DIR/scripts/rh56e2_preflight.py" \
  --teleopit-dir "$TELEOPIT_DIR" --somehand-dir "$SOMEHAND_DIR" --profile sim

echo "Validation passed. No hardware writes were performed."
