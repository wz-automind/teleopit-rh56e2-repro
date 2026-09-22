# Repository Guidelines

## Project structure

This repository integrates three pinned upstreams. Teleopit owns whole-body
control and runtime state, somehand owns hand-pose retargeting, and pico-bridge
owns PICO transport. RH56E2-specific files live under `overlay/` at the paths
where the installer places them in those upstream projects. Operational scripts
follow Teleopit's `scripts/setup`, `scripts/run`, and `scripts/dev` groups.

## Code conventions

- Target Python 3.10+ and use four-space indentation.
- Use `snake_case` for modules and functions and `PascalCase` for classes.
- Add explicit type hints to public helpers and terse behavior-focused docstrings.
- Keep Modbus framing/transport separate from device safety and retargeting.
- Fail fast on malformed data or configuration; never pad, trim, or silently
  replace an invalid hardware command.
- Add no dependency that already belongs to Teleopit, somehand, or pico-bridge.

## Hardware safety

Hardware writes must default to disabled. New write paths require an explicit
interlock, fault/temperature checks, deterministic tests, and corresponding
English and Chinese documentation. Do not describe static source review as
physical validation.

## Tests and documentation

```bash
python -m compileall -q src overlay scripts tests
python -m unittest discover -s tests -v
pytest -q
ruff check src overlay/teleopit/sim2real/hands scripts tests
```

Keep `README.md` short. Detailed documentation belongs in matching files under
`docs/en` and `docs/zh`; write the English source first, then translate it with
the same headings, commands, defaults, and safety limits.
