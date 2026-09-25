# Architecture and request flow

## Component ownership

| Component | Owns | Does not own here |
| --- | --- | --- |
| pico-bridge 0.2.1 | PICO network receiver and headset/controller/hand/body frames | G1 policy, hand IK, RH56E2 protocol |
| Teleopit 0.5.0 | Input lifecycle, body retargeting, reference timeline, policy, G1 simulation/sim2real, hand worker lifecycle | RH56E2 kinematics and vendor registers |
| somehand 0.3.0 | YAML-loaded RH56E2 kinematics and landmark-to-joint optimization | PICO receiver lifecycle and hardware writes |
| RH56E2 integration | Models/configs, radians-to-raw mapping, Modbus TCP, health and write gates | G1 low-level control |

## Request flow

1. `pico_bridge.PicoBridge` receives PICO frames on the Teleopit host.
2. Teleopit's `Pico4InputProvider` consumes body tracking for the G1 reference and exposes the same receiver's hand snapshot. No second PICO receiver is started.
3. `pico_hand_to_landmarks()` converts one PICO hand's 26-joint state to the 21-landmark representation consumed by somehand.
4. `somehand.api.RetargetingEngine` loads the left/right RH56E2 YAML and MJCF, then solves a joint-space target.
5. `Rh56e2SomehandMapper` selects the six actuated joints in this order: pinky, ring, middle, index, thumb bend, thumb rotation.
6. `radians_to_raw()` maps model radians to RH56E2 units (`0` closed, `1000` open) and emits `HandPoseCommand` objects.
7. In simulation, the RH56E2 session applies the joint targets to the MuJoCo model. In sim2real, `HandRuntime` calls `Rh56e2Device`, which applies rate, change, fault, temperature, stale-frame, and write-enable gates before FC16.

## Runtime rates and latency

- PICO hand retargeting is configured for 60 Hz.
- The RH56E2 hardware worker defaults to 30 Hz.
- The G1 policy path runs at 50 Hz and PD control at 200 Hz.

These are stage update rates, not an end-to-end latency claim. Network jitter,
retargeting work, process scheduling, device response time, and G1 control all
contribute to measured latency.

## Source layout

```text
overlay/teleopit/                    files installed into Teleopit
  configs/                           Hydra integration configurations
  sim/                               dual-hand MuJoCo session
  sim2real/hands/rh56e2_protocol.py  registers, frames, TCP transport
  sim2real/hands/rh56e2.py           config, safety, somehand mapper, device
overlay/third_party/somehand/         RH56E2 MJCF and retargeting YAML
scripts/setup/                        installation entry points
scripts/run/                          simulation and sim2real entry points
scripts/dev/                          validation and guarded bench tools
```

`manifest.json` records the upstream revisions used for compatibility review.
For the deployed G1, this repository is packaged on a development computer,
transferred with SCP, and copied to identical relative paths inside the existing
`/home/unitree/Teleopit`. Back up that runtime before merging; do not clone a
second upstream checkout on G1.

## Failure behavior

- Missing or stale hand tracking sends hold values (`-1`) only when writes are enabled.
- Nonzero hand faults or excessive temperature block subsequent writes.
- Duplicate left/right endpoints fail configuration parsing.
- Hand worker failure is non-critical to Teleopit's G1 process, but does not imply that the remaining physical state is safe.
- Shutdown does not open the hand unless `open_on_shutdown` is explicitly enabled.

[RH56E2 reference](rh56e2.md) · [Complete usage guide](../usage.md)
