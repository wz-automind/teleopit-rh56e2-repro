# Repository Alignment Specification

## Product identity

This repository is the RH56E2 integration distribution for Teleopit. Teleopit
owns whole-body control and the runtime state machine, somehand owns hand-pose
retargeting, and pico-bridge owns transport of PICO tracking data. This
repository owns the integration between those projects and the Inspire RH56E2
(因时 E2) simulation and hardware adapters.

## Upstream policy

- Record the reviewed Teleopit, somehand, and pico-bridge versions in
  `manifest.json`.
- Keep upstream projects external rather than copying their complete source
  histories into this repository.
- Store integration files under `overlay/` using the same destination paths
  they have inside Teleopit and somehand.
- Package the integration repository on a development computer and merge it
  offline into the backed-up Teleopit runtime already present on G1.
- Explain every upstream dependency, ownership boundary, and update procedure.

## Repository and code style

- Follow Teleopit's `teleopit/`, `scripts/{run,setup,dev}`, `tests/`, Hydra
  config, typed dataclass, and fail-fast validation conventions.
- Follow somehand's mirrored `docs/en` and `docs/zh` documentation layout.
- Keep the root README as a bilingual landing page with a short quick start;
  keep detailed procedures in the matching language directory.
- Keep identical relative Markdown paths below `docs/en` and `docs/zh`.
- Do not place language-specific Markdown files directly under `docs/`, and do
  not link an English procedure to a Chinese page or vice versa. Explicit
  language switches between the two documentation home pages are allowed.
- Keep maintainer-only design material under `docs/development` and outside
  the operator navigation.
- Target Python 3.10+, use explicit type hints for public helpers, pytest for
  tests, and Ruff for deterministic style checks.
- Keep protocol framing separate from the RH56E2 device/retargeting adapter.

## RH56E2 support contract

- Support left, right, and dual Inspire RH56E2 hands in MuJoCo.
- Retarget PICO hand tracking through the public somehand API.
- Connect hardware over Modbus TCP with the manual's six-channel order:
  pinky, ring, middle, index, thumb bend, thumb rotation.
- Keep all hardware writes disabled by default.
- Reject duplicate dual-hand endpoints, active faults, excessive temperature,
  malformed protocol responses, and stale tracking.
- Distinguish source-reviewed compatibility from hardware-verified behavior.

## Documentation contract

The English document is the source and the Chinese document at the same
relative path mirrors its meaning and section order. `usage.md` is the single
canonical operating guide in each language; `reference/rh56e2.md` keeps the
source-review and physical-acceptance boundary explicit. Documentation must
cover architecture, upstream responsibilities, installation, virtual
environments, PICO configuration, simulation, staged RH56E2 testing, G1
dry-run/standing, full hardware launch, emergency stop, troubleshooting, and
upstream update maintenance.
