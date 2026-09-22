# Upstream maintenance

## Pinned foundations

`manifest.json` is the machine-readable source of truth. The current integration
targets Teleopit v0.5.0, somehand 0.3.0, and pico-bridge v0.2.1. Teleopit and
somehand are pinned by full commit SHA; released pico-bridge wheel/APK artifacts
are pinned by version and SHA-256.

## Why overlays are used

This repository is not a snapshot of three unrelated histories. The installer
checks out the exact Teleopit and somehand sources, installs the released
pico-bridge package, and copies integration files to their normal upstream
paths. The result has Teleopit's runtime layout while this repository's review
surface remains limited to RH56E2-specific additions.

An overlay is therefore a path-compatible integration layer, not a runtime
monkey patch: `overlay/teleopit/sim2real/hands/rh56e2.py` becomes
`$TELEOPIT_DIR/teleopit/sim2real/hands/rh56e2.py` during installation.

## Update procedure

1. Read the upstream changelogs and migration notes.
2. Update one upstream at a time in `manifest.json`, `pyproject.toml`, and `scripts/install.sh`.
3. Reapply the overlay to a clean checkout; never test an unexplained dirty upstream tree.
4. Run compilation, unit tests, Ruff, shell syntax, and offline model validation.
5. Run PICO simulation and verify sides, axes, modes, pause/resume, and stale tracking.
6. Repeat read-only telemetry and staged single-DOF tests before continuous hardware control.
7. Record the tested versions and untested physical conditions in `CHANGELOG.md` and the pull request.

## Compatibility points to review

- Teleopit hand protocols, worker construction, Hydra config keys, Pico snapshot types, and G1 state transitions.
- somehand public `somehand.api`, YAML schema, joint names, qpos indexing, model axes, and solver output.
- pico-bridge wheel/API version, frame fields, 26-joint ordering, timestamps, reconnect behavior, and APK/wheel hashes.
- RH56E2 firmware Unit ID, register behavior, address configuration, response framing, joint directions, temperature semantics, and hold command.

Do not update a version number alone and call the combination compatible. Static
tests and physical acceptance are separate evidence.

[Architecture](architecture.md) · [Third-party components](../../../THIRD_PARTY.md)
