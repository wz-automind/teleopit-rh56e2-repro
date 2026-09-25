# Teleopit RH56E2 documentation

Teleopit RH56E2 is an integration distribution built on Teleopit, somehand,
and pico-bridge. It adds first-class Inspire RH56E2 simulation, hand
retargeting, and guarded hardware control without replacing the responsibilities
of its upstream projects.

## Start here

| Topic | Document |
| --- | --- |
| From a clean host to simulation and hardware tests | [Complete usage guide](usage.md) |
| Component ownership and runtime request flow | [Architecture](reference/architecture.md) |
| RH56E2 models, channels, registers, config, and safety | [RH56E2 reference](reference/rh56e2.md) |
| Standalone read and guarded-write API | [Python SDK reference](reference/sdk.md) |
| Pinned versions and the upstream update procedure | [Upstream maintenance](reference/upstreams.md) |

## Support boundary

The checked-in tests validate source integration, protocol frames, mappings,
configuration gates, and documentation structure. They cannot certify a
particular robot, firmware, power supply, network, payload, or workcell.

[中文文档](../zh/README.md) · [Repository README](../../README.md)
