# Third-party components

This repository is an integration project. It does not claim ownership of the
upstream projects or vendor robot descriptions listed below.

| Component | Role | Version source | License/source |
| --- | --- | --- | --- |
| Teleopit | Whole-body runtime, G1 policy and state machine | `manifest.json` | [BotRunner64/Teleopit](https://github.com/BotRunner64/Teleopit), Apache-2.0 |
| somehand | PICO landmark-to-hand retargeting | `manifest.json` | [BotRunner64/somehand](https://github.com/BotRunner64/somehand), Apache-2.0 |
| pico-bridge | PICO headset/controller/hand/body transport | `manifest.json` | [BotRunner64/pico-bridge](https://github.com/BotRunner64/pico-bridge) |
| xr_teleoperate | Reference for Inspire six-DOF ordering and normalized mapping | `manifest.json` | [unitreerobotics/xr_teleoperate](https://github.com/unitreerobotics/xr_teleoperate) |
| Inspire RH56E2 files | URDF/MJCF geometry and hardware behavior | vendor files/manual | Preserve the terms supplied with the original vendor material |

The installer fetches upstream code and released artifacts rather than
vendoring their full histories. Review each upstream and vendor license before
redistribution or commercial deployment.
