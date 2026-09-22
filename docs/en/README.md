# Teleopit RH56E2 documentation

Teleopit RH56E2 is an integration distribution built on Teleopit, somehand,
and pico-bridge. It adds first-class Inspire RH56E2 simulation, hand
retargeting, and guarded hardware control without replacing the responsibilities
of its upstream projects.

## Start here

| Topic | Document |
| --- | --- |
| From a clean host to simulation and hardware tests | [Complete usage guide](../USAGE.en.md) |
| Component ownership and runtime request flow | [Architecture](reference/architecture.md) |
| RH56E2 models, channels, registers, config, and safety | [RH56E2 reference](reference/rh56e2.md) |
| Pinned versions and the upstream update procedure | [Upstream maintenance](reference/upstreams.md) |
| Static review and outstanding physical checks | [Hardware control review](../真机控制检查.md) |
| Release history | [Changelog](../../CHANGELOG.md) |

## Recommended reading order

1. Read the architecture page to understand which project owns each stage.
2. Follow the complete usage guide through installation and simulation.
3. Read the RH56E2 reference before connecting hand power or Ethernet.
4. Complete every staged hardware check; do not start with full-body control.

## Support boundary

The checked-in tests validate source integration, protocol frames, mappings,
configuration gates, and documentation structure. They cannot certify a
particular robot, firmware, power supply, network, payload, or workcell.

[中文文档](../zh/README.md) · [Repository README](../../README.md)
