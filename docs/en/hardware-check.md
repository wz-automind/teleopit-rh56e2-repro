# RH56E2 Hardware Control Review

## Review conclusion

As of 2026-09-22, the code has reached **static compatibility** and supports a **read-only connectivity preflight**, but it must not be labeled “hardware validated.” The exact G1, two RH56E2 hands, power supply, network, firmware, payload, and emergency-stop setup have not completed physical acceptance testing.

| Check | Conclusion | Evidence / remaining work |
|---|---|---|
| Six-DoF order | Matches | The simulation, RH56E2 manual, and Unitree `xr_teleoperate` all use pinky, ring, middle, index, thumb bend, and thumb rotation |
| somehand output range | Matches | Four fingers use 0–1.7 rad, thumb bend 0–0.5 rad, and thumb rotation -0.1–1.3 rad; the Unitree formula maps them to 0–1000 |
| RH56E2 communication | Code matches the manual | Modbus TCP FC03/FC16, port 6000, target angle register 1486, actual angle register 1546, and related telemetry are implemented; the unit ID and firmware response still require hardware confirmation |
| Dual-hand networking | Guarded | The code rejects duplicate IP:port endpoints; one hand must still be assigned a different factory IP before both are connected |
| G1 body control | Reuses upstream | Uses the Teleopit v0.5.0 G1 bridge, 50 Hz policy path, and 200 Hz DDS/PD path; supported-standing and emergency-stop acceptance remain required |
| Electrical | Parameters checked | One hand requires 24 V, approximately 0.2 A at idle, approximately 1.2 A average without load, and up to approximately 4.5 A while grasping; wiring, grounding, and supply capacity require on-site verification |
| Fault and temperature handling | Software gates implemented | Writes are refused when any of the six fault bytes is nonzero or temperature exceeds 70°C; this conservative software threshold does not replace the manufacturer limits |
| End-to-end hardware | Not validated | Record physical results for stages A–E below |

## Runtime request flow

### Body path

```text
PICO 4 body pose
  -> pico-bridge network frames
  -> Teleopit PICO worker (up to 120 Hz polling)
  -> human-to-G1 reference retargeting and buffering
  -> G1 policy (50 Hz)
  -> safety manager: state machine, joint position/velocity, Kp ramp
  -> g1_bridge_sdk / DDS PD control (200 Hz)
  -> 29 G1 body joints
```

The 120/50/200 Hz values are update rates for individual stages, not end-to-end latency. Actual latency also includes PICO capture, Wi-Fi, scheduling, inference, and DDS execution, and must be measured from timestamps on the deployed system.

### Hand path

```text
PICO 4 left/right hand, 26 joints
  -> Teleopit hand snapshot
  -> pico_hand_to_landmarks converts to the somehand 21-landmark definition
  -> left/right somehand SLSQP retargeting (configured at 60 Hz)
  -> select six active RH56E2 joint angles
  -> Unitree Inspire formula (max - q) / (max - min)
  -> six 0–1000 targets
  -> RH56E2 Modbus TCP FC16, register 1486
  -> six actuators in each hand
```

Feedback uses FC03: angle 1546, force 1582, current 1594, fault 1606, state 1612, and temperature 1618. The default command limit is 30 Hz and health data is refreshed every 0.5 seconds; these values are also not network-latency measurements.

## Relationship to `xr_teleoperate`

The Inspire controller in Unitree's official repository uses G1/Unitree-side DDS services (DFX/FTP topics and `inspire_sdkpy`). This project connects directly to the hand's Modbus TCP port according to the E2 manual. The communication backends are not interchangeable, but the following properties can be cross-checked:

- the six hardware channels use the same order;
- an Inspire target of 0 means closed and 1 means open;
- the four-finger, thumb-bend, and thumb-rotation angle ranges match;
- Unitree's normalization formula matches this project's `radians_to_raw()`.

The current E2 model and retargeting order are therefore compatible at the source level. The previously missing direct Modbus hardware backend is implemented, but physical acceptance testing is still required.

## Safety acceptance procedure

### A. Power-off inspection

- Verify the left/right hand models, firmware, connector pins, and harness; confirm 24 V and GND polarity.
- Size the supply with margin for both hands operating at peak current. The theoretical combined grasping peak is 9 A, before startup and other-load margin.
- Confirm protective grounding, shielded twisted-pair cabling, fuse/current limiting, and an accessible power disconnect.
- Secure the hands and G1. Keep people and fragile objects outside the motion envelope.

### B. Read-only single-hand test

Connect one hand at a time and run the preflight against the default `192.168.11.210:6000`. Record whether:

- all six actual angles remain within 0–1000;
- all six fault values are zero;
- temperature and current values are plausible;
- repeated connections remain stable.

Do not set `write_enabled=true` during this stage.

### C. Low-speed single-hand jog

Place the hand on an independent fixture. With low speed and a low force threshold, test each axis at 1000, 750, 500, 250, and 0. Pay particular attention to thumb-rotation direction and the physical open/closed definition. If hardware direction disagrees with the configuration, correct the mapping; do not drive against a mechanical stop.

Acceptance requires correct direction on every axis, no binding, no over-current or over-temperature condition, continuous feedback, and controlled behavior after network loss.

### D. Dual-hand connection

- Assign different IP addresses, power-cycle both hands separately, and verify that the addresses persist.
- Run the read-only preflight against both hands and confirm the data is not crossed.
- At low speed, command the same open/close motion and confirm consistent left/right semantics.
- Interrupt PICO hand tracking deliberately and confirm the driver sends `-1` hold values instead of continuing the previous trajectory.

### E. Complete G1 system

- First validate the G1 on a support frame with Teleopit's official standalone-standing procedure.
- Validate the body path with hand writes disabled.
- Enable the RH56E2 hands last, starting with low speed, no payload, and short sessions.
- Measure and record end-to-end latency, jitter, dropped frames, and stop behavior from the PICO timestamp to G1 and hand motion.

Only after stages A–E pass may that exact hardware combination be marked “usable for hardware control.”

## Immediate stop conditions

Stop immediately and remove motion enable if any fault byte is nonzero, temperature rises continuously or exceeds the limit, current is abnormal, a mechanism binds, network timeouts repeat, left/right addresses are crossed, the G1 becomes unstable, the emergency stop is unavailable, the operator loses PICO tracking, or a person enters the motion area.

[Documentation home](README.md) · [Complete usage guide](usage.md) · [RH56E2 reference](reference/rh56e2.md)
