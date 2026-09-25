# Upstream maintenance

## Pinned foundations

`manifest.json` is the machine-readable source of truth. The current integration
targets Teleopit v0.5.0, somehand 0.3.0, and pico-bridge v0.2.1. Teleopit and
somehand are pinned by full commit SHA; released pico-bridge wheel/APK artifacts
are pinned by version and SHA-256.

## Why overlays are used

This repository is not a snapshot of three unrelated histories.
`manifest.json` records the reviewed Teleopit, somehand, and pico-bridge
versions, while the deployed G1 already has a working Teleopit environment.
This repository is packaged on a development computer, transferred to G1, and
copied into the existing Teleopit paths. The runtime keeps Teleopit's layout
while this repository's review surface remains limited to RH56E2 additions.

An overlay is therefore a path-compatible integration layer, not a runtime
monkey patch: `overlay/teleopit/sim2real/hands/rh56e2.py` is copied to
`/home/unitree/Teleopit/teleopit/sim2real/hands/rh56e2.py` during the offline merge.

## Update procedure

1. Read the upstream changelogs and migration notes.
2. Update one upstream at a time in `manifest.json` and `pyproject.toml`.
3. Validate the overlay on a development copy; back up G1's existing Teleopit before hardware deployment.
4. Run compilation, unit tests, Ruff, shell syntax, and offline model validation.
5. Run PICO simulation and verify sides, axes, modes, pause/resume, and stale tracking.
6. Repeat read-only telemetry and staged single-DOF tests before continuous hardware control.
7. Record the tested versions and untested physical conditions in the pull request and repository history.

## Compatibility points to review

- Teleopit hand protocols, worker construction, Hydra config keys, Pico snapshot types, and G1 state transitions.
- somehand public `somehand.api`, YAML schema, joint names, qpos indexing, model axes, and solver output.
- pico-bridge wheel/API version, frame fields, 26-joint ordering, timestamps, reconnect behavior, and APK/wheel hashes.
- RH56E2 firmware Unit ID, register behavior, address configuration, response framing, joint directions, temperature semantics, and hold command.


[Architecture](architecture.md) · [Third-party components](../../../THIRD_PARTY.md)
