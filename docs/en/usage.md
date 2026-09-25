# Teleopit + RH56E2 Usage Guide (English)

This guide follows the offline deployment that was used on the robot. G1
initially has no Teleopit source tree. A development computer prepares both a
complete Teleopit archive and this RH56E2 integration archive, transfers both
to G1 with SSH/SCP, unpacks Teleopit, and then merges the RH56E2 overlay and SDK
into `/home/unitree/Teleopit`. G1 does not clone either repository online.

## 1. Scope and safety boundary

- Simulation works without a robot; PICO teleoperation requires the headset on the same LAN.
- `rh56e2_preflight.py` and the default bench-tool mode are read-only and do not write Modbus registers.
- Single-hand motion additionally requires `--write --confirm MOVE_RH56E2`.
- The full hardware entry point also requires both `ENABLE_G1_REAL=YES` and `ENABLE_RH56E2_WRITES=YES`.
- Passing code and static tests is not physical safety acceptance. Perform first motion unloaded and at low speed, with an operator at the emergency stop and nobody near the G1.

## 2. System and directories

The G1 uses these two directories:

```text
/home/unitree/teleopit-rh56e2-repro/  unpacked integration repository: validation and safety entry points
/home/unitree/Teleopit/               transferred complete Teleopit: final runtime directory
/home/unitree/Teleopit/third_party/somehand/
/home/unitree/Teleopit/ckpt/track_g1.onnx
```

## 3. Prerequisites

- The development computer needs `git`, `tar`, `scp`, and GitHub access to make the offline bundle.
- G1 initially has no Teleopit source tree; the development computer supplies `/home/unitree/Teleopit` as an archive.
- G1 has `/home/unitree/miniforge3/envs/teleopit`, using Python 3.10 or 3.11 with the original Teleopit hardware dependencies.
- A discrete GPU with working OpenGL/Vulkan drivers is recommended for simulation.
- Hardware work requires a Unitree G1, left and right RH56E2 hands, PICO 4 Ultra, a working emergency stop, an isolated test area, and wired networking.
- Power each RH56E2 from a stable 24 V supply. The manual specifies 4.5 A maximum grasping current per hand. Do not draw power from an unverified G1 connector.

Install missing tools on the development computer if necessary:

```bash
sudo apt update
sudo apt install -y git openssh-client tar
```

## 4. Clone and package on the development computer

Run these commands on the development computer, not on G1:

```bash
cd ~
git clone https://github.com/wz-automind/teleopit-rh56e2-repro.git
cd teleopit-rh56e2-repro

git archive --format=tar.gz \
  --prefix=teleopit-rh56e2-repro/ \
  --output=../teleopit-rh56e2-repro-latest.tar.gz \
  HEAD
```

This archive contains only committed integration files. It excludes `.git`,
temporary worktrees, and local caches.

The complete Teleopit source and asset directory is required for the first
deployment. Create its archive from the development computer's home directory:

```bash
cd ~
tar --exclude='Teleopit/.git' \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  -czf Teleopit-latest.tar.gz Teleopit
```

The Teleopit source archive does not contain the Conda environment. G1 continues
to use `/home/unitree/miniforge3/envs/teleopit`. Do not copy a development
computer's Conda directory onto G1 because CPU architecture and locally compiled
dependencies may differ.

## 5. Transfer to G1, install Teleopit, and merge the E2 integration

From the development computer, transfer both archives through G1's Wi-Fi/SSH
address:

```bash
scp ~/teleopit-rh56e2-repro-latest.tar.gz \
  unitree@192.168.50.62:/home/unitree/
scp ~/Teleopit-latest.tar.gz \
  unitree@192.168.50.62:/home/unitree/
```

SSH to G1 and unpack the integration repository. Preserve an older integration
directory by renaming it instead of deleting it:

```bash
ssh unitree@192.168.50.62

cd /home/unitree
stamp="$(date +%Y%m%d-%H%M%S)"
if [ -d teleopit-rh56e2-repro ]; then
  mv teleopit-rh56e2-repro "teleopit-rh56e2-repro-backup-$stamp"
fi
tar -xzf teleopit-rh56e2-repro-latest.tar.gz -C /home/unitree
```

G1 initially has no Teleopit. Restore the complete directory before copying any
E2 overlay files. The backup branch makes the same commands safe for a later
redeployment:

```bash
cd /home/unitree
if [ -d Teleopit ]; then
  mv Teleopit "Teleopit-backup-$stamp"
fi
tar -xzf Teleopit-latest.tar.gz -C /home/unitree
test -d /home/unitree/Teleopit/teleopit

cd /home/unitree/teleopit-rh56e2-repro
cp -a overlay/teleopit/. /home/unitree/Teleopit/teleopit/
cp -a overlay/scripts/. /home/unitree/Teleopit/scripts/
cp -a overlay/assets/. /home/unitree/Teleopit/assets/
mkdir -p /home/unitree/Teleopit/third_party/somehand
cp -a overlay/third_party/somehand/. \
  /home/unitree/Teleopit/third_party/somehand/

source /home/unitree/miniforge3/bin/activate teleopit
python -m pip install --no-build-isolation -e . --no-deps
```

On later RH56E2-only updates, `/home/unitree/Teleopit` already exists: transfer
only the new integration archive, back up the current Teleopit directory, and
repeat the overlay-copy and SDK-install commands. Do not extract an older
`Teleopit-latest.tar.gz` over a working updated runtime.

For later G1 shells, continue to run
`source /home/unitree/miniforge3/bin/activate teleopit` first. This procedure
does not run `git clone` on G1 or download either repository online.

## 6. Configure and install the PICO app

Use the pico-bridge app already installed on PICO. Put PICO and G1 Wi-Fi on the same LAN and set the control-host address to `192.168.50.62`. Allow the pico-bridge connection through the firewall and update the PICO app whenever G1's Wi-Fi address changes.

Confirm that the host sees the PICO before testing a robot. Do not enable hardware output if tracking drops, the network is unstable, or coordinate directions are wrong.

## 7. Offline validation

```bash
cd ~/teleopit-rh56e2-repro
bash scripts/dev/validate.sh
python scripts/dev/check_rh56e2.py \
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
source /home/unitree/miniforge3/bin/activate teleopit
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
| Policy or model is missing | Confirm that the transferred `/home/unitree/Teleopit` contains `ckpt` and assets; if not, rebuild and transfer `Teleopit-latest.tar.gz` from the development computer instead of reinstalling online on G1 |
| Left/right hand or joint direction is wrong | Stay in simulation, record the exact hand and DOF, and do not continue to the hardware steps after Section 8 |

## 9. Confirm the transferred hardware components

The offline merge does not redownload the G1 bridge. Confirm that the existing
Conda environment and the Teleopit directory transferred in Section 5 together
provide the hardware runtime, and check the newly merged SDK:

```bash
source /home/unitree/miniforge3/bin/activate teleopit
cd /home/unitree/teleopit-rh56e2-repro
python -c 'import g1_bridge_sdk, teleopit; from teleopit_rh56e2.sdk import RH56E2Hand; print("runtime imports OK")'
python scripts/dev/check_rh56e2.py \
  --teleopit-dir /home/unitree/Teleopit --profile real
```

If `g1_bridge_sdk` is missing, either G1's preinstalled Conda environment or the
transferred Teleopit package is incomplete. Repair the environment or rebuild
the compatible package on the development computer; do not clone Teleopit on
the robot.

## 10. Configure RH56E2 power and networking

### How the deployed E2 endpoints were identified

We did not infer port `6000` from the G1 address or choose it at random. First,
the G1-side interface and subnet were confirmed, then the powered hand
addresses were checked in the neighbor table. The RH56E2 Modbus TCP protocol
configuration specifies TCP port `6000`; a TCP connection test and a read-only
Modbus FC03 request then confirmed that the endpoints were E2 controllers:

```bash
ip -4 address show eth1
ip route
ip neigh show dev eth1

nc -vz -w 2 192.168.123.210 6000
nc -vz -w 2 192.168.123.211 6000

cd /home/unitree/teleopit-rh56e2-repro
bash scripts/dev/check_unitree_g1_rh56e2.sh
```

In the verified installation, `eth1` owned `192.168.123.164/24`, the two E2
controllers were `192.168.123.210` and `192.168.123.211`, and both accepted TCP
connections on `6000`. An open TCP port alone does not identify an E2: the last
command performs read-only Modbus FC03 telemetry reads and must return plausible
six-channel data with no faults. Do not identify a device by sending random
register writes. If `nc` is unavailable, use the read-only check directly.

### Generic address configuration

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
python scripts/dev/check_rh56e2.py \
  --teleopit-dir ~/Teleopit --profile sim --hardware \
  --left-host 192.168.11.210
```

Confirm that six angles are readable, every fault byte is zero, and temperatures are plausible. This command is read-only. Add, for example, `--unit-id 1` only if the firmware/manual specifies a different Unit ID; do not troubleshoot by randomly writing registers.

## 12. Low-speed single-hand bench test

Secure the hand, remove all payload, and keep the finger workspace clear. Start in the default read-only mode:

```bash
python scripts/dev/bench_rh56e2.py \
  --teleopit-dir ~/Teleopit --host 192.168.11.210 \
  --dof index --delta 50
```

After checking the readings, have an operator ready to remove power/use the emergency stop, then allow one motion:

```bash
python scripts/dev/bench_rh56e2.py \
  --teleopit-dir ~/Teleopit --host 192.168.11.210 \
  --dof index --delta 50 --speed 50 \
  --write --confirm MOVE_RH56E2
```

The tool changes one DOF, writes `-1` to hold the other five, and limits the delta to ±100. It then writes that DOF back to its initial feedback value. Any nonzero fault byte or over-temperature reading blocks motion. Repeat for the other hand and required DOFs; do not make continuous two-hand tracking the first powered test.

## 13. Read-only dual-hand preflight

Connect both hands only after confirming unique addresses:

```bash
python scripts/dev/check_rh56e2.py \
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
python scripts/run/standalone_standing.py \
  --policy ckpt/track_g1.onnx \
  --network-interface eth1 \
  --dry-run
```

After a successful dry-run, remove `--dry-run` only with the manufacturer procedure, emergency stop, and on-site supervision in place:

```bash
python scripts/run/standalone_standing.py \
  --policy ckpt/track_g1.onnx \
  --network-interface eth1
```

Proceed only after the G1 can enter and leave the standing state reliably.

## 15. Full G1 + RH56E2 hardware test

`~/Teleopit` is the runtime checkout and includes the E2 overlay installed by
this repository. `~/teleopit-rh56e2-repro` contains installation, read-only
checks, and guarded launchers. Entering `Teleopit` does not mean that dexterous
hand support is absent; selecting `pico4_sim2real_rh56e2` enables it.

### Onboard operation (currently verified deployment)

The verified deployment uses `eth1` on the Unitree host, host address
`192.168.123.164`, left and right E2 endpoints `192.168.123.210:6000` and
`192.168.123.211:6000`, and the PICO-reachable host Wi-Fi address
`192.168.50.62`. Run the read-only check first, then explicitly enable both
hardware gates:

```bash
source /home/unitree/miniforge3/bin/activate teleopit
cd ~/teleopit-rh56e2-repro
bash scripts/dev/check_unitree_g1_rh56e2.sh

ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES \
  bash scripts/run/run_unitree_g1_rh56e2.sh
```

Every value remains overridable through its named environment variable, so the
repository is not tied to this network. For example, set `LEFT_HAND_IP` and
`RIGHT_HAND_IP` after changing hand addresses, or `PICO_ADVERTISE_IP` after
moving the PICO link to another Wi-Fi network.

### Generic direct commands

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

### External-host operation

An external host needs a wired interface that directly reaches the robot
switch (for example `enp4s0`) and a unique `192.168.123.x/24` address. Wi-Fi
may carry SSH and PICO traffic, but it does not replace the wired G1/E2 robot
link. After the external host can reach `192.168.123.164`,
`192.168.123.210:6000`, and `192.168.123.211:6000`, override the generic
launcher with the actual host values:

```bash
cd ~/teleopit-rh56e2-repro
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES \
NETWORK_INTERFACE=enp4s0 \
G1_HOST_IP=192.168.123.164 \
LEFT_HAND_IP=192.168.123.210 RIGHT_HAND_IP=192.168.123.211 \
PICO_ADVERTISE_IP=<external-host-Wi-Fi-IP> \
bash scripts/run/run_unitree_g1_rh56e2.sh
```

`g1_host_cli`, `run_sim2real.py`, the onboard launcher, and an external-host
launcher contend for the same G1 control channel. Only one control process may
run at a time. SSH only opens a remote shell; it does not select the interface
used for robot control.

## 16. State transitions and stopping

- `Start`: enter `STANDING`.
- `Y`: enter `MOCAP` teleoperation from standing.
- `X`: return to `STANDING`.
- `Q`: exit the process normally.
- `B` or PICO `A`: pause/resume.
- `L1 + R1`: enter the emergency `DAMPING` state.

Test pause and exit before increasing motion. Stop immediately on tracking loss, abnormal vibration, wrong joint direction, a latency spike, over-temperature, or a fault code. Use the hardware emergency stop/remove power when necessary; do not rely only on software buttons.

`Ctrl+C` only sends an interrupt from the current terminal. It can appear to do
nothing when the terminal lacks focus, raw keyboard input is active, or the
process is not in the foreground. First press `X` to return to standing and
then `Q`. If it still does not exit, inspect and signal it from a second SSH
terminal:

```bash
pgrep -af 'g1_host_cli|run_sim2real|run_real|standalone_standing'
pkill -INT -f 'scripts/run/run_sim2real.py'
# Only if it is still present after inspection:
pkill -TERM -f 'scripts/run/run_sim2real.py'
```

Keep the hardware emergency stop available throughout. For abnormal motion,
use the hardware stop immediately rather than waiting for terminal input.

## 17. Post-run checks

After stopping control, rerun the dual-hand read-only preflight from section 13 and record angles, faults, and temperatures. Inspect the supply, cables, and mechanical mounts. The current code uses `open_on_failure=false` and `open_on_shutdown=false`, so it does not intentionally open on a fault; a tracking timeout sends `-1` to hold the current target. Whether that behavior is safe still depends on the payload and site risk assessment.

## 18. Troubleshooting

| Symptom | Check |
|---|---|
| Missing model, policy, or configuration | Check whether `/home/unitree/Teleopit` came from the complete offline bundle; if necessary, transfer `Teleopit-latest.tar.gz` again and reapply the overlay |
| `ModuleNotFoundError` | Confirm `CONDA_DEFAULT_ENV=teleopit` and that `which python` points to `/home/unitree/miniforge3/envs/teleopit`; if only the SDK is missing, rerun `python -m pip install --no-build-isolation -e . --no-deps` from the integration repository |
| RH56E2 timeout | Check power, static IP, subnet, port 6000, firewall, and Unit ID |
| `.11.210/.11.211` time out | `.11.x` is a generic example; the verified deployment uses `.123.210/.123.211`. Run `check_unitree_g1_rh56e2.sh` first |
| Only one of two hands connects | Power separately and verify addresses; remove duplicate IPs before reconnecting both |
| Nonzero fault bytes/high temperature | Stop writes and power troubleshooting; follow the vendor manual instead of forcing operation after a software reset |
| No G1 LowState | Check interface name, G1 mode, physical link, and `g1_bridge_sdk` |
| PICO pose jumps/drops | Check subnet, Wi-Fi quality, app host address, and tracking environment; keep writes disabled |
| `Ctrl+C` has no effect | Stop hardware first and try `X`, `Q`; then use `pgrep` in a second terminal to identify the exact process before sending `INT`/`TERM` |

## 19. Command reference

```bash
# Development computer: build and transfer complete Teleopit plus the integration bundle
cd ~
tar --exclude='Teleopit/.git' --exclude='*/__pycache__' --exclude='*.pyc' -czf Teleopit-latest.tar.gz Teleopit
cd ~/teleopit-rh56e2-repro
git archive --format=tar.gz --prefix=teleopit-rh56e2-repro/ --output=../teleopit-rh56e2-repro-latest.tar.gz HEAD
scp ~/Teleopit-latest.tar.gz ~/teleopit-rh56e2-repro-latest.tar.gz unitree@192.168.50.62:/home/unitree/
# G1 first deployment: unpack complete Teleopit before applying the integration overlay
tar -xzf /home/unitree/Teleopit-latest.tar.gz -C /home/unitree
tar -xzf /home/unitree/teleopit-rh56e2-repro-latest.tar.gz -C /home/unitree
# Offline validation
bash scripts/dev/validate.sh
# Read-only single-hand check
python scripts/dev/check_rh56e2.py --teleopit-dir "$HOME/Teleopit" --profile sim --hardware --left-host 192.168.11.210
# Full hardware entry point (only after all staged acceptance checks pass)
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES LEFT_HAND_IP=192.168.11.210 RIGHT_HAND_IP=192.168.11.211 NETWORK_INTERFACE=eth1 bash scripts/run/run_sim2real_rh56e2.sh
# Verified Unitree onboard deployment: read-only check / guarded launch
bash scripts/dev/check_unitree_g1_rh56e2.sh
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES bash scripts/run/run_unitree_g1_rh56e2.sh
```

See the [RH56E2 reference](reference/rh56e2.md) for protocol details, register mappings, model mappings, and safety limits.
