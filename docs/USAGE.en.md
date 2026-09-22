# Teleopit + RH56E2 Usage Guide (English)

This guide starts with a clean Ubuntu/Linux host and covers the Python virtual environment, simulation, read-only RH56E2 checks, a single-hand low-speed test, G1 standing validation, and the full hardware path. The commands target the pinned Teleopit v0.5.0, somehand 0.3.0, and pico-bridge v0.2.1 revisions in this repository.

## 1. Scope and safety boundary

- Simulation works without a robot; PICO teleoperation requires the headset on the same LAN.
- `rh56e2_preflight.py` and the default bench-tool mode are read-only and do not write Modbus registers.
- Single-hand motion additionally requires `--write --confirm MOVE_RH56E2`.
- The full hardware entry point also requires both `ENABLE_G1_REAL=YES` and `ENABLE_RH56E2_WRITES=YES`.
- Passing code and static tests is not physical safety acceptance. Perform first motion unloaded and at low speed, with an operator at the emergency stop and nobody near the G1.

## 2. System and directories

The main paths after installation are:

```text
teleopit-rh56e2-repro/       this repository: install, validation, safety entry points
$HOME/Teleopit/              pinned Teleopit plus the overlay
$HOME/Teleopit/.venv/        Python virtual environment
$HOME/Teleopit/third_party/somehand/
$HOME/Teleopit/ckpt/track_g1.onnx
```

The data flow is PICO body/hand tracking → pico-bridge → Teleopit state machine and policy → G1. Hand tracking also flows through somehand retargeting → RH56E2 over Modbus TCP. The configured 120/60/50/200 Hz values are update rates for individual stages, not end-to-end latency; measure actual latency on the deployed host, network, and hardware.

## 3. Prerequisites

- Ubuntu 22.04/24.04 or compatible Linux, x86_64, Python 3.10 or 3.11.
- `git`, Python venv support, build tools, and internet access.
- A discrete GPU with working OpenGL/Vulkan drivers is recommended for simulation.
- Hardware work requires a Unitree G1, left and right RH56E2 hands, PICO 4 Ultra, a working emergency stop, an isolated test area, and wired networking.
- Power each RH56E2 from a stable 24 V supply. The manual specifies 4.5 A maximum grasping current per hand. Do not draw power from an unverified G1 connector.

Example Ubuntu prerequisites:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-dev build-essential
```

## 4. Clone the repository

```bash
cd ~
git clone https://github.com/wz-automind/teleopit-rh56e2-repro.git
cd teleopit-rh56e2-repro
```

The default workflow installs Teleopit at `~/Teleopit` and somehand at
`~/Teleopit/third_party/somehand`, so path variables are not required. Advanced
users may still set `TELEOPIT_DIR` and `SOMEHAND_DIR` before installation. Do
not point them at another Teleopit checkout with unknown uncommitted changes;
the installer refuses to overwrite such a checkout.

## 5. Create and use the Python virtual environment

The installer creates `~/Teleopit/.venv`; no manual `pip install` is required:

```bash
cd ~/teleopit-rh56e2-repro
bash scripts/setup/install.sh --profile sim --download-pico-apk
cd ~/Teleopit
source .venv/bin/activate
python -V
```

If the default `python3` is not 3.10/3.11, select one explicitly:

```bash
bash scripts/setup/install.sh --profile sim --download-pico-apk --python python3.11
```

The installer checks out pinned commits, copies the overlay, installs editable packages, and downloads robot, GMR, policy, and BVH assets. Do not commit `.venv`, downloaded assets, device credentials, or tokens.

## 6. Configure and install the PICO app

The APK is downloaded to `downloads/PicoBridge_v0.2.1_20260522_release.apk`, and its SHA-256 is verified. Install it through developer mode/ADB, launch it, and put the PICO and control host on the same LAN. Allow the pico-bridge connection through the firewall and update the host address in the PICO app whenever the host IP changes.

Confirm that the host sees the PICO before testing a robot. Do not enable hardware output if tracking drops, the network is unstable, or coordinate directions are wrong.

## 7. Offline validation

```bash
cd ~/teleopit-rh56e2-repro
bash scripts/dev/validate.sh
~/Teleopit/.venv/bin/python scripts/dev/check_rh56e2.py \
  --teleopit-dir ~/Teleopit --profile sim
```

The checks must report success, pinned revisions, and all required assets. This stage does not contact a robot and sends no Modbus write.

## 8. Run simulation

### 8.1 What the simulation contains and does not contain

This is **MuJoCo sim2sim**, not RH56E2 hardware control. The scene uses `teleopit/configs/pico4_sim_rh56e2.yaml` and contains the 29-DOF G1 body plus 12 actuators across the left and right RH56E2 hands. PICO body tracking feeds the Teleopit policy for G1, while left/right hand tracking is retargeted by somehand and drives only the simulated hands. This command does not connect to a G1, open an RH56E2 Modbus socket, or write hardware registers.

The default configuration requires a PICO 4 Ultra for live body and hand tracking. Without a PICO, Section 7 can still validate installation, load the model, and run the 1,000-step stability check, but this live teleoperation entry point waits for PICO data and is not an input-free automatic demo. It listens on `0.0.0.0:63901` by default and waits 60 seconds for the first frame.

### 8.2 Pre-launch checks

1. Open pico-bridge on the PICO and enter the control host IP on the same LAN.
2. Allow port `63901` through the host firewall for the transport used by the installed pico-bridge version, and ensure no other process owns the port.
3. Confirm that the policy exists:

```bash
test -f ~/Teleopit/ckpt/track_g1.onnx && echo "policy OK"
```

4. Repeat the full no-hardware-write validation:

```bash
cd ~/teleopit-rh56e2-repro
bash scripts/dev/validate.sh
```

### 8.3 Start live PICO simulation

Teleopit's unchanged PICO simulation command is:

```bash
cd ~/Teleopit
source .venv/bin/activate
python scripts/run/run_sim.py \
  --config-name pico4_sim \
  controller.policy_path=ckpt/track_g1.onnx
```

The E2 version extends that command with the RH56E2-aware entry point and
configuration:

```bash
python scripts/run/run_sim_rh56e2.py \
  --config-name pico4_sim_rh56e2 \
  controller.policy_path=ckpt/track_g1.onnx
```

The compatibility launcher `scripts/run/run_sim_rh56e2.sh` remains available
from the integration repository, but the direct Python form above matches
Teleopit's upstream command style.

The terminal should show `State: STANDING`, `Input: Pico4 live`, `Viewers: all`, and `Hands: RH56E2`. After the first PICO frame arrives, use this sequence:

| Key | Action | What to verify |
|---|---|---|
| `Y` | Enter full-body `MOCAP` from `STANDING` | G1 and both hands start following PICO |
| `B` | Toggle full-body versus arms-only mode | Mode changes do not cause a pose jump |
| `A` | Pause/resume tracking | The simulation holds the last target while paused |
| `X` | Return to `STANDING` | The model returns to standing control |
| `Q` | Exit normally | Viewers close and the process ends |

`Ctrl+C` is a fallback terminal exit. The terminal window must have focus for keyboard controls.

### 8.4 Simulation acceptance criteria

Verify every item before considering hardware:

- The MuJoCo window opens and G1 remains stable in `STANDING`, without continuous sinking, divergence, or high-frequency oscillation.
- After `Y`, body directions match the operator and left/right hands are not swapped.
- All six actuators per hand respond; thumb rotation and finger flexion directions are correct, without model penetration or joints stuck at limits.
- `A` holds the pose and resumes without an obvious jump; `X` reliably returns to `STANDING`.
- The terminal does not continuously report dropped frames, timeouts, NaNs, policy-dimension errors, or missing model assets.

The configured `policy_hz: 50` and `pd_hz: 200` are policy and simulation-PD update rates, not PICO-to-display end-to-end latency.

### 8.5 Simulation troubleshooting

| Symptom | Action |
|---|---|
| Continues waiting for PICO | Check the host IP entered in PICO, LAN membership, firewall, and port `63901`; restart the PICO app before the 60-second timeout |
| `Y` does not enter `MOCAP` | PICO has not supplied a valid body/hand frame; restore tracking and confirm that the terminal receives the first frame |
| Viewer does not open | Check the GPU driver, OpenGL, and `DISPLAY`/Wayland; SSH requires working graphics forwarding or a local desktop |
| Policy or model is missing | Repeat the Section 5 install without `--skip-assets`, then run `scripts/dev/validate.sh` |
| Left/right hand or joint direction is wrong | Stay in simulation, record the exact hand and DOF, and do not continue to the hardware steps after Section 8 |

## 9. Install hardware components

Return to this repository and add the G1 bridge to the same Teleopit directory:

```bash
cd ~/teleopit-rh56e2-repro
bash scripts/setup/install.sh --profile real
source ~/Teleopit/.venv/bin/activate
```

Do not run hardware scripts from a different Python environment. Validate it:

```bash
~/Teleopit/.venv/bin/python scripts/dev/check_rh56e2.py \
  --teleopit-dir ~/Teleopit --profile real
```

## 10. Configure RH56E2 power and networking

Power and configure one hand at a time. Multiple devices may share the factory address `192.168.11.210`; before attaching both to one subnet, assign a unique address to one, for example left `.210` and right `.211`. These are examples, not addresses to copy blindly into an existing network.

Give the host wired interface a static address on the same subnet, such as `192.168.11.100/24`. The default port is `6000` and default Unit ID is `0xFF`. Check reachability first:

```bash
ping -c 3 192.168.11.210
ping -c 3 192.168.11.211
```

The two hands must not use the same IP/port pair. On-site personnel must verify wiring, polarity, fusing, grounding, and supply capacity.

## 11. Read-only single-hand preflight

Disconnect the G1 and attach one unloaded hand:

```bash
cd ~/teleopit-rh56e2-repro
~/Teleopit/.venv/bin/python scripts/dev/check_rh56e2.py \
  --teleopit-dir ~/Teleopit --profile sim --hardware \
  --left-host 192.168.11.210
```

Confirm that six angles are readable, every fault byte is zero, and temperatures are plausible. This command is read-only. Add, for example, `--unit-id 1` only if the firmware/manual specifies a different Unit ID; do not troubleshoot by randomly writing registers.

## 12. Low-speed single-hand bench test

Secure the hand, remove all payload, and keep the finger workspace clear. Start in the default read-only mode:

```bash
~/Teleopit/.venv/bin/python scripts/dev/bench_rh56e2.py \
  --teleopit-dir ~/Teleopit --host 192.168.11.210 \
  --dof index --delta 50
```

After checking the readings, have an operator ready to remove power/use the emergency stop, then allow one motion:

```bash
~/Teleopit/.venv/bin/python scripts/dev/bench_rh56e2.py \
  --teleopit-dir ~/Teleopit --host 192.168.11.210 \
  --dof index --delta 50 --speed 50 \
  --write --confirm MOVE_RH56E2
```

The tool changes one DOF, writes `-1` to hold the other five, and limits the delta to ±100. It then writes that DOF back to its initial feedback value. Any nonzero fault byte or over-temperature reading blocks motion. Repeat for the other hand and required DOFs; do not make continuous two-hand tracking the first powered test.

## 13. Read-only dual-hand preflight

Connect both hands only after confirming unique addresses:

```bash
~/Teleopit/.venv/bin/python scripts/dev/check_rh56e2.py \
  --teleopit-dir ~/Teleopit --profile real --hardware \
  --left-host 192.168.11.210 --right-host 192.168.11.211
```

Stop if either connection, fault, or temperature check fails. Do not proceed to full control.

## 14. G1 dry-run and standing test

Confirm that the deployed G1 wired interface is `eth1` (or replace it with the
actual name reported by the host) and place/suspend the robot in the
manufacturer-approved test posture:

```bash
cd ~/Teleopit
.venv/bin/python scripts/run/standalone_standing.py \
  --policy ckpt/track_g1.onnx \
  --network-interface eth1 \
  --dry-run
```

After a successful dry-run, remove `--dry-run` only with the manufacturer procedure, emergency stop, and on-site supervision in place:

```bash
.venv/bin/python scripts/run/standalone_standing.py \
  --policy ckpt/track_g1.onnx \
  --network-interface eth1
```

Proceed only after the G1 can enter and leave the standing state reliably.

## 15. Full G1 + RH56E2 hardware test

Start the PICO app and confirm stable tracking. On the deployed Unitree host,
activate the existing `teleopit` Conda environment and enter the Teleopit
checkout. The unchanged upstream command controls the whole body without the
dexterous hands:

```bash
source /home/unitree/miniforge3/bin/activate teleopit
cd /home/unitree/Teleopit

# Whole-body teleoperation (without dexterous hands)
python scripts/run/run_sim2real.py \
  --config-name pico4_sim2real \
  controller.policy_path=ckpt/track_g1.onnx \
  input.bridge_advertise_ip=192.168.50.62 \
  real_robot.network_interface=eth1
```

To control both E2 hands, start from the same command, select the E2
configuration, and append only the hand connection parameters:

```bash
source /home/unitree/miniforge3/bin/activate teleopit
cd /home/unitree/Teleopit

# Whole-body teleoperation (with dual RH56E2 hands)
python scripts/run/run_sim2real.py \
  --config-name pico4_sim2real_rh56e2 \
  controller.policy_path=ckpt/track_g1.onnx \
  input.bridge_advertise_ip=192.168.50.62 \
  real_robot.network_interface=eth1 \
  hands.rh56e2.left_host=192.168.11.210 \
  hands.rh56e2.right_host=192.168.11.211 \
  hands.rh56e2.port=6000 \
  hands.rh56e2.write_enabled=true
```

These two commands are alternatives and must not run at the same time. Stop the
no-hand process before starting the E2 command. The E2 command enables physical
hand writes, so run it only after sections 11-14 pass and with the robot unloaded,
its motion range restricted, and hardware emergency stop ready.

The repository also provides an optional guarded launcher. It repeats the
hardware preflight before it starts the same E2 configuration:

```bash
cd ~/teleopit-rh56e2-repro
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES \
LEFT_HAND_IP=192.168.11.210 RIGHT_HAND_IP=192.168.11.211 \
NETWORK_INTERFACE=eth1 \
bash scripts/run/run_sim2real_rh56e2.sh \
  input.bridge_advertise_ip=192.168.50.62
```

The entry point repeats the hardware preflight and stops on missing confirmations, duplicate addresses, or telemetry failures. Keep the robot unloaded and restrict motion range on the first run.

## 16. State transitions and stopping

- `Start`: enter `STANDING`.
- `Y`: enter `MOCAP` teleoperation from standing.
- `X`: return to `STANDING`.
- `B` or PICO `A`: pause/resume.
- `L1 + R1`: enter the emergency `DAMPING` state.

Test pause and exit before increasing motion. Stop immediately on tracking loss, abnormal vibration, wrong joint direction, a latency spike, over-temperature, or a fault code. Use the hardware emergency stop/remove power when necessary; do not rely only on software buttons.

## 17. Post-run checks

After stopping control, rerun the dual-hand read-only preflight from section 13 and record angles, faults, and temperatures. Inspect the supply, cables, and mechanical mounts. The current code uses `open_on_failure=false` and `open_on_shutdown=false`, so it does not intentionally open on a fault; a tracking timeout sends `-1` to hold the current target. Whether that behavior is safe still depends on the payload and site risk assessment.

## 18. Troubleshooting

| Symptom | Check |
|---|---|
| Missing model, policy, or configuration | Rerun `scripts/setup/install.sh` without `--skip-assets`, then run `scripts/dev/validate.sh` |
| `ModuleNotFoundError` | Use `$TELEOPIT_DIR/.venv/bin/python`; rerun the appropriate profile installation if needed |
| RH56E2 timeout | Check power, static IP, subnet, port 6000, firewall, and Unit ID |
| Only one of two hands connects | Power separately and verify addresses; remove duplicate IPs before reconnecting both |
| Nonzero fault bytes/high temperature | Stop writes and power troubleshooting; follow the vendor manual instead of forcing operation after a software reset |
| No G1 LowState | Check interface name, G1 mode, physical link, and `g1_bridge_sdk` |
| PICO pose jumps/drops | Check subnet, Wi-Fi quality, app host address, and tracking environment; keep writes disabled |

## 19. Command reference

```bash
# Install simulation environment
bash scripts/setup/install.sh --profile sim --download-pico-apk
# Offline validation
bash scripts/dev/validate.sh
# Install hardware components
bash scripts/setup/install.sh --profile real
# Read-only single-hand check
$HOME/Teleopit/.venv/bin/python scripts/dev/check_rh56e2.py --teleopit-dir "$HOME/Teleopit" --profile sim --hardware --left-host 192.168.11.210
# Full hardware entry point (only after all staged acceptance checks pass)
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES LEFT_HAND_IP=192.168.11.210 RIGHT_HAND_IP=192.168.11.211 NETWORK_INTERFACE=eth1 bash scripts/run/run_sim2real_rh56e2.sh
```

See [Hardware Control Review](真机控制检查.md) for protocol details, register mappings, model mappings, and outstanding physical acceptance work.

