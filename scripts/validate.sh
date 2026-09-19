#!/usr/bin/env bash
set -euo pipefail

TELEOPIT_DIR="${TELEOPIT_DIR:-$HOME/Teleopit}"
SOMEHAND_DIR="${SOMEHAND_DIR:-$TELEOPIT_DIR/third_party/somehand}"
cd "$TELEOPIT_DIR"

export PYTHONPATH="$SOMEHAND_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

python -m py_compile \
  teleopit/pipeline_rh56e2.py \
  teleopit/robots/mujoco_robot_rh56e2.py \
  teleopit/sim/loop_rh56e2.py \
  teleopit/sim/session_rh56e2.py \
  teleopit/sim/rh56e2_hands.py \
  scripts/run/run_sim_rh56e2.py

python -c "from pathlib import Path; import mujoco; p=Path('assets/robots/unitree_g1/g1_29dof_rh56e2.xml'); m=mujoco.MjModel.from_xml_path(str(p)); assert m.nu >= 41, m.nu; print(f'Model OK: nq={m.nq} nv={m.nv} nu={m.nu}')"

python -c "from pathlib import Path; from hydra import compose,initialize_config_dir; from teleopit.robots.mujoco_robot_rh56e2 import MuJoCoRobotRh56e2; d=str(Path('teleopit/configs').resolve()); c=initialize_config_dir(config_dir=d,version_base=None); c.__enter__(); cfg=compose(config_name='pico4_sim_rh56e2'); r=MuJoCoRobotRh56e2(cfg.robot); r.step(); assert r.data.ncon == 0, r.data.ncon; [r.step() for _ in range(999)]; print('Stability OK: 1000 steps'); c.__exit__(None,None,None)"

echo "Validation passed."
