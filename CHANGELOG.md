# Changelog

## 0.2.0 - 2026-09-22

- Defined the repository as a pinned Teleopit integration distribution built
  on somehand and pico-bridge.
- Made Inspire RH56E2 / 因时 E2 support an explicit simulation and hardware
  contract.
- Added standard Python project metadata, grouped operational entry points,
  mirrored English/Chinese reference documentation, and repository checks.
- Separated RH56E2 Modbus TCP framing and transport from the Teleopit device
  adapter.
- Kept standard Teleopit commands unchanged, documented E2 commands as additive
  config/driver variants, and allowed guarded real launches to forward Hydra
  overrides such as `input.bridge_advertise_ip`.
- Added the exact Unitree deployment command pair using the `teleopit`
  Miniforge environment, `/home/unitree/Teleopit`, `eth1`, and explicit dual-E2
  endpoints; documented that the no-hand and E2 processes are alternatives.
- Replaced the stale Chinese installation note with a current quick-start,
  aligned every concrete G1 hardware example to `eth1`, and recorded an
  upstream-release freshness audit without adopting unreleased commits.
- Standardized installation, validation, simulation, and hardware launchers on
  the activated Miniforge `teleopit` environment; corrected the guarded
  launcher's `eth1` default and shared RH56E2 port override.

## 0.1.0 - 2026-09-20

- Added pinned upstream installation, G1 + RH56E2 simulation assets, PICO hand
  retargeting, guarded Modbus TCP hardware control, and staged hardware guides.
