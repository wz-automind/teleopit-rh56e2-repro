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

## 4. Clone the repository and configure paths

```bash
git clone https://github.com/wz-automind/teleopit-rh56e2-repro.git
cd teleopit-rh56e2-repro
export REPRO_DIR="$PWD"
export TELEOPIT_DIR="$HOME/Teleopit"
export SOMEHAND_DIR="$TELEOPIT_DIR/third_party/somehand"
```

To use different locations, set `TELEOPIT_DIR` and `SOMEHAND_DIR` before installation. Do not point them at another Teleopit checkout with unknown uncommitted changes; the installer refuses to overwrite such a checkout.

## 5. Create and use the Python virtual environment

The installer creates `$TELEOPIT_DIR/.venv`; no manual `pip install` is required:

```bash
cd "$REPRO_DIR"
bash scripts/install.sh --profile sim --download-pico-apk
source "$TELEOPIT_DIR/.venv/bin/activate"
python -V
```

If the default `python3` is not 3.10/3.11, select one explicitly:

```bash
bash scripts/install.sh --profile sim --download-pico-apk --python python3.11
```

The installer checks out pinned commits, copies the overlay, installs editable packages, and downloads robot, GMR, policy, and BVH assets. Do not commit `.venv`, downloaded assets, device credentials, or tokens.

## 6. Configure and install the PICO app

The APK is downloaded to `downloads/PicoBridge_v0.2.1_20260522_release.apk`, and its SHA-256 is verified. Install it through developer mode/ADB, launch it, and put the PICO and control host on the same LAN. Allow the pico-bridge connection through the firewall and update the host address in the PICO app whenever the host IP changes.

Confirm that the host sees the PICO before testing a robot. Do not enable hardware output if tracking drops, the network is unstable, or coordinate directions are wrong.

## 7. Offline validation

```bash
cd "$REPRO_DIR"
TELEOPIT_DIR="$TELEOPIT_DIR" bash scripts/validate.sh
"$TELEOPIT_DIR/.venv/bin/python" scripts/rh56e2_preflight.py \
  --teleopit-dir "$TELEOPIT_DIR" --profile sim
```

The checks must report success, pinned revisions, and all required assets. This stage does not contact a robot and sends no Modbus write.

## 8. Run simulation

```bash
cd "$TELEOPIT_DIR"
.venv/bin/python scripts/run/run_sim_rh56e2.py \
  controller.policy_path=ckpt/track_g1.onnx
```

Inspect the stationary model and joint directions before connecting the PICO. Verify that left/right hands are not swapped, thumb rotation is correct, and pausing tracking does not produce a pose jump. Stop with `Ctrl+C`. If the window does not open, check the graphics driver and `DISPLAY`/Wayland configuration.

## 9. Install hardware components

Return to this repository and add the G1 bridge to the same Teleopit directory:

```bash
cd "$REPRO_DIR"
bash scripts/install.sh --profile real
source "$TELEOPIT_DIR/.venv/bin/activate"
```

Do not run hardware scripts from a different Python environment. Validate it:

```bash
"$TELEOPIT_DIR/.venv/bin/python" scripts/rh56e2_preflight.py \
  --teleopit-dir "$TELEOPIT_DIR" --profile real
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
cd "$REPRO_DIR"
"$TELEOPIT_DIR/.venv/bin/python" scripts/rh56e2_preflight.py \
  --teleopit-dir "$TELEOPIT_DIR" --profile sim --hardware \
  --left-host 192.168.11.210
```

Confirm that six angles are readable, every fault byte is zero, and temperatures are plausible. This command is read-only. Add, for example, `--unit-id 1` only if the firmware/manual specifies a different Unit ID; do not troubleshoot by randomly writing registers.

## 12. Low-speed single-hand bench test

Secure the hand, remove all payload, and keep the finger workspace clear. Start in the default read-only mode:

```bash
"$TELEOPIT_DIR/.venv/bin/python" scripts/rh56e2_bench_test.py \
  --teleopit-dir "$TELEOPIT_DIR" --host 192.168.11.210 \
  --dof index --delta 50
```

After checking the readings, have an operator ready to remove power/use the emergency stop, then allow one motion:

```bash
"$TELEOPIT_DIR/.venv/bin/python" scripts/rh56e2_bench_test.py \
  --teleopit-dir "$TELEOPIT_DIR" --host 192.168.11.210 \
  --dof index --delta 50 --speed 50 \
  --write --confirm MOVE_RH56E2
```

The tool changes one DOF, writes `-1` to hold the other five, and limits the delta to ±100. It then writes that DOF back to its initial feedback value. Any nonzero fault byte or over-temperature reading blocks motion. Repeat for the other hand and required DOFs; do not make continuous two-hand tracking the first powered test.

## 13. Read-only dual-hand preflight

Connect both hands only after confirming unique addresses:

```bash
"$TELEOPIT_DIR/.venv/bin/python" scripts/rh56e2_preflight.py \
  --teleopit-dir "$TELEOPIT_DIR" --profile real --hardware \
  --left-host 192.168.11.210 --right-host 192.168.11.211
```

Stop if either connection, fault, or temperature check fails. Do not proceed to full control.

## 14. G1 dry-run and standing test

Identify the wired G1 interface (for example `eth0`) and place/suspend the robot in the manufacturer-approved test posture:

```bash
cd "$TELEOPIT_DIR"
.venv/bin/python scripts/run/standalone_standing.py \
  --policy ckpt/track_g1.onnx \
  --network-interface eth0 \
  --dry-run
```

After a successful dry-run, remove `--dry-run` only with the manufacturer procedure, emergency stop, and on-site supervision in place:

```bash
.venv/bin/python scripts/run/standalone_standing.py \
  --policy ckpt/track_g1.onnx \
  --network-interface eth0
```

Proceed only after the G1 can enter and leave the standing state reliably.

## 15. Full G1 + RH56E2 hardware test

Start the PICO app and confirm stable tracking. From this repository, run:

```bash
cd "$REPRO_DIR"
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES \
LEFT_HAND_IP=192.168.11.210 RIGHT_HAND_IP=192.168.11.211 \
NETWORK_INTERFACE=eth0 \
bash scripts/run_real.sh
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
| Missing model, policy, or configuration | Rerun `install.sh` without `--skip-assets`, then run `validate.sh` |
| `ModuleNotFoundError` | Use `$TELEOPIT_DIR/.venv/bin/python`; rerun the appropriate profile installation if needed |
| RH56E2 timeout | Check power, static IP, subnet, port 6000, firewall, and Unit ID |
| Only one of two hands connects | Power separately and verify addresses; remove duplicate IPs before reconnecting both |
| Nonzero fault bytes/high temperature | Stop writes and power troubleshooting; follow the vendor manual instead of forcing operation after a software reset |
| No G1 LowState | Check interface name, G1 mode, physical link, and `g1_bridge_sdk` |
| PICO pose jumps/drops | Check subnet, Wi-Fi quality, app host address, and tracking environment; keep writes disabled |

## 19. Command reference

```bash
# Install simulation environment
bash scripts/install.sh --profile sim --download-pico-apk
# Offline validation
TELEOPIT_DIR="$HOME/Teleopit" bash scripts/validate.sh
# Install hardware components
bash scripts/install.sh --profile real
# Read-only single-hand check
$HOME/Teleopit/.venv/bin/python scripts/rh56e2_preflight.py --teleopit-dir "$HOME/Teleopit" --profile sim --hardware --left-host 192.168.11.210
# Full hardware entry point (only after all staged acceptance checks pass)
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES LEFT_HAND_IP=192.168.11.210 RIGHT_HAND_IP=192.168.11.211 NETWORK_INTERFACE=eth0 bash scripts/run_real.sh
```

See [Hardware Control Review](真机控制检查.md) for protocol details, register mappings, model mappings, and outstanding physical acceptance work.
