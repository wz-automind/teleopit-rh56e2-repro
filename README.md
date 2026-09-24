<h1 align="center">Teleopit RH56E2</h1>

<p align="center">
  PICO-driven Unitree G1 teleoperation with Inspire RH56E2 / 因时 E2 hands.
  <br/>
  Built on Teleopit, somehand, and pico-bridge with pinned, reproducible versions.
</p>

<p align="center">
  <a href="docs/en/README.md">English Docs</a> •
  <a href="docs/zh/README.md">中文文档</a> •
  <a href="CHANGELOG.md">Changelog</a> •
  <a href="THIRD_PARTY.md">Upstreams</a>
</p>

---

## Architecture

| Foundation | Responsibility in this repository |
| --- | --- |
| [Teleopit](https://github.com/BotRunner64/Teleopit) | G1 whole-body retargeting, policy inference, simulation, sim2real state machine and safety runtime |
| [somehand](https://github.com/BotRunner64/somehand) | PICO hand-landmark retargeting to the RH56E2 kinematic model |
| [pico-bridge](https://github.com/BotRunner64/pico-bridge) | PICO headset, controller, hand and body tracking transport |
| This repository | RH56E2 models/configs, Modbus TCP adapter, integration configs, reproducible installation and staged hardware checks |

```text
PICO 4 Ultra
  └─ pico-bridge tracking
       ├─ Teleopit body retargeting → policy → G1
       └─ Teleopit 26→21 hand landmarks → somehand → RH56E2 adapter
                                                      ├─ MuJoCo simulation
                                                      └─ guarded Modbus TCP hardware
```

The upstream versions are fixed in [`manifest.json`](manifest.json). Integration files under `overlay/` use the same destination paths as Teleopit and somehand; the installer checks out those exact upstream revisions and applies the integration. This avoids carrying modified copies of both complete upstream projects while keeping every added file reviewable.

## Highlights

- G1 + dual RH56E2 MuJoCo simulation driven by PICO body and hand tracking.
- Left, right, and dual Inspire RH56E2 configurations for somehand.
- Standard-library Modbus TCP driver with FC03 telemetry and guarded FC16 commands.
- Hardware writes disabled by default; duplicate endpoints, faults, over-temperature, and stale tracking are gated.
- Teleopit-style `scripts/setup`, `scripts/run`, and `scripts/dev` entry points.
- Mirrored English and Chinese documentation from installation through staged real-hardware testing.

## Quick start

Ubuntu/Linux with Python 3.10 or 3.11 is recommended.

Create the Miniforge environment once:

```bash
source /home/unitree/miniforge3/bin/activate
conda create -n teleopit python=3.11 -y
```

Then install and run with that same environment:

```bash
source /home/unitree/miniforge3/bin/activate teleopit
git clone https://github.com/wz-automind/teleopit-rh56e2-repro.git
cd teleopit-rh56e2-repro
bash scripts/setup/install.sh --profile sim --download-pico-apk
cd ~/Teleopit
python scripts/run/run_sim_rh56e2.py \
  --config-name pico4_sim_rh56e2 \
  controller.policy_path=ckpt/track_g1.onnx
```

This follows Teleopit's normal `python scripts/run/...` command style. The E2
variant changes only the entry point/configuration needed by the combined G1 +
RH56E2 simulation. Installation and simulation do not write RH56E2 hardware.

## Real-hardware commands

On the deployed Unitree host, use the existing `teleopit` Miniforge environment
and `/home/unitree/Teleopit`. The standard `pico4_sim2real` command runs
whole-body teleoperation without dexterous hands; the
`pico4_sim2real_rh56e2` variant adds the two E2 endpoints and enables hand
writes. They are alternatives and must not run at the same time. Copy the exact
commands and complete the staged checks in the [English usage guide](docs/en/usage.md#15-full-g1--rh56e2-hardware-test)
or [Chinese usage guide](docs/zh/usage.md#15-完整-g1--rh56e2-真机测试).

For the verified onboard topology (`eth1`, host `192.168.123.164`, E2 hands
`192.168.123.210/.211:6000`, PICO-facing IP `192.168.50.62`), use the
read-only check and guarded launcher:

```bash
cd ~/teleopit-rh56e2-repro
bash scripts/dev/check_unitree_g1_rh56e2.sh
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES \
  bash scripts/run/run_unitree_g1_rh56e2.sh
```

All addresses and the interface remain configurable through environment
variables; the usage guides also cover generic and external-host deployments.

## Documentation

| Topic | English | 中文 |
| --- | --- | --- |
| Documentation home | [docs/en/README.md](docs/en/README.md) | [docs/zh/README.md](docs/zh/README.md) |
| Complete setup and operation | [Usage guide](docs/en/usage.md) | [完整使用手册](docs/zh/usage.md) |
| Architecture and request flow | [Architecture](docs/en/reference/architecture.md) | [架构与数据流](docs/zh/reference/architecture.md) |
| Inspire RH56E2 / 因时 E2 | [RH56E2 reference](docs/en/reference/rh56e2.md) | [RH56E2 参考](docs/zh/reference/rh56e2.md) |
| Standalone Python SDK | [SDK reference](docs/en/reference/sdk.md) | [SDK 参考](docs/zh/reference/sdk.md) |
| Hardware review and acceptance | [Hardware control review](docs/en/hardware-check.md) | [真机控制检查](docs/zh/hardware-check.md) |
| Upstream versions and updates | [Upstream maintenance](docs/en/reference/upstreams.md) | [上游维护](docs/zh/reference/upstreams.md) |

## Hardware status

The protocol, mapping, configuration, and safety interlocks are covered by deterministic source tests. The repository has not physically accepted your exact G1, two RH56E2 hands, power supply, network, firmware, payload, or emergency-stop setup. Complete the staged procedure in the usage guide before enabling writes.
