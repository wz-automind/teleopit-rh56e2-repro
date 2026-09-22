# Upstream Style Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the repository into a clearly defined Teleopit integration distribution with first-class somehand, pico-bridge, and Inspire RH56E2 support, matching upstream code, layout, testing, and documentation conventions.

**Architecture:** Keep reviewed upstream sources pinned and external, while overlay files retain their exact Teleopit/somehand destination paths. Add standard Python project metadata, split Modbus protocol concerns from the Teleopit device adapter, expose Teleopit-style script groups, and reorganize documentation into mirrored English and Chinese trees.

**Tech Stack:** Python 3.10+, Hydra/OmegaConf, MuJoCo, somehand 0.3.0, pico-bridge 0.2.1, Modbus TCP, pytest, Ruff, Bash.

**Spec:** `docs/design/repository-alignment.md`

## Global Constraints

- Teleopit remains the whole-body runtime and state-machine owner.
- somehand remains the public hand-retargeting API owner.
- pico-bridge remains the PICO tracking transport owner.
- Inspire RH56E2 / 因时 E2 is a first-class simulation and hardware integration.
- All hardware writes remain disabled by default and physically unverified behavior is labeled.
- English and Chinese documentation trees must have matching paths and heading order.
- Existing root script entry points remain compatible.

---

### Task 1: Establish an upstream-style project contract

**Files:**
- Create: `pyproject.toml`
- Create: `AGENTS.md`
- Create: `CHANGELOG.md`
- Create: `THIRD_PARTY.md`
- Modify: `manifest.json`
- Test: `tests/test_repository_contract.py`

**Interfaces:**
- Consumes: pinned commits and release hashes in `manifest.json`.
- Produces: installable project metadata, dev tooling settings, ownership rules, and machine-checked required upstreams.

- [x] **Step 1: Write repository-contract tests**

Assert that `pyproject.toml` declares Python 3.10+, all three upstream packages,
pytest/Ruff settings, and the manifest identifies RH56E2 as the supported hand.

- [x] **Step 2: Run the focused test and confirm failure**

Run: `python -m unittest tests.test_repository_contract -v`

Expected: failure because `pyproject.toml` does not exist.

- [x] **Step 3: Add metadata and contribution rules**

Use PEP 621 metadata, direct pinned dependencies, `pytest` test paths, Ruff's
Python 3.10 target, and explicit third-party ownership/license boundaries.

- [x] **Step 4: Run the focused test**

Run: `python -m unittest tests.test_repository_contract -v`

Expected: all repository-contract tests pass.

### Task 2: Separate RH56E2 protocol and runtime responsibilities

**Files:**
- Create: `overlay/teleopit/sim2real/hands/rh56e2_protocol.py`
- Modify: `overlay/teleopit/sim2real/hands/rh56e2.py`
- Modify: `tests/test_rh56e2.py`

**Interfaces:**
- Produces: `Rh56e2ModbusClient`, `build_read_frame`, `build_write_frame`,
  `parse_read_response`, `parse_write_response`, and register constants from
  `rh56e2_protocol.py`.
- Consumes: those protocol interfaces from the Teleopit-style device adapter.

- [x] **Step 1: Change protocol tests to import the dedicated module**

The existing FC03/FC16 tests import from
`teleopit.sim2real.hands.rh56e2_protocol` and initially fail.

- [x] **Step 2: Extract the protocol module**

Move frame construction, response parsing, register constants, socket client,
and integer wire validators without changing behavior.

- [x] **Step 3: Keep the device adapter focused**

Import the protocol surface into `rh56e2.py`; retain config parsing, safety,
somehand mapping, and `build_rh56e2` there.

- [x] **Step 4: Verify protocol and mapping tests**

Run: `python -m unittest tests.test_rh56e2 -v`

Expected: all protocol, config, and mapping tests pass.

### Task 3: Add Teleopit-style operational entry points

**Files:**
- Create: `scripts/setup/install.sh`
- Create: `scripts/dev/validate.sh`
- Create: `scripts/dev/check_rh56e2.py`
- Create: `scripts/dev/bench_rh56e2.py`
- Create: `scripts/run/run_sim_rh56e2.sh`
- Create: `scripts/run/run_sim2real_rh56e2.sh`
- Test: `tests/test_repository_contract.py`

**Interfaces:**
- Consumes: the existing root entry points and `$TELEOPIT_DIR`.
- Produces: discoverable setup/dev/run commands arranged like Teleopit while
  retaining current root commands for compatibility.

- [x] **Step 1: Add entry-point presence tests**

Assert all six grouped entry points exist and the run scripts forward arbitrary
Hydra overrides unchanged.

- [x] **Step 2: Add small compatibility launchers**

Each launcher resolves the repository root without assuming the caller's
working directory and delegates with `exec`/`runpy` so exit codes are preserved.

- [ ] **Step 3: Validate shell and Python syntax**

Run: `bash -n scripts/setup/install.sh scripts/dev/validate.sh scripts/run/*.sh`
and `python -m compileall -q scripts`.

### Task 4: Build mirrored detailed documentation

**Files:**
- Rewrite: `README.md`
- Create: `docs/en/README.md`
- Create: `docs/zh/README.md`
- Create: `docs/en/reference/architecture.md`
- Create: `docs/zh/reference/architecture.md`
- Create: `docs/en/reference/rh56e2.md`
- Create: `docs/zh/reference/rh56e2.md`
- Create: `docs/en/reference/upstreams.md`
- Create: `docs/zh/reference/upstreams.md`
- Modify: `docs/USAGE.en.md`
- Modify: `docs/USAGE.zh-CN.md`
- Test: `tests/test_usage_docs.py`

**Interfaces:**
- Consumes: the code and command surfaces from Tasks 1-3.
- Produces: a concise bilingual landing page plus detailed mirrored guides for users and maintainers.

- [x] **Step 1: Create matching documentation indexes**

Both indexes link installation/full usage, architecture, RH56E2, upstream
maintenance, hardware review, and troubleshooting material.

- [x] **Step 2: Document the exact ownership and request flow**

Describe PICO → pico-bridge → Teleopit → somehand → RH56E2, including data
shapes, rates, paths, safety gates, and which repository owns each stage.

- [x] **Step 3: Document RH56E2 as a first-class adapter**

Include six-channel ordering, model/config paths, Modbus registers, left/right
IP rules, simulation commands, staged hardware commands, and limitations.

- [x] **Step 4: Update the full usage guides to canonical script paths**

Keep root compatibility commands visible, but make `scripts/setup`,
`scripts/dev`, and `scripts/run` the primary documented interface.

- [x] **Step 5: Verify documentation parity and links**

Run the full unit suite and repository-relative Markdown link checker.

### Task 5: Align CI and publish

**Files:**
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `pyproject.toml`, source files, entry points, and tests.
- Produces: CI checks for compilation, pytest/unit tests, Ruff, shell syntax,
  bilingual structure, and repository contracts.

- [x] **Step 1: Install development checks in CI**

Install `pytest` and `ruff` beside the existing lightweight runtime dependencies.

- [ ] **Step 2: Run all deterministic checks locally**

Run compilation, unittest discovery, pytest, Ruff, Markdown links, and shell
syntax where Bash is available.

- [ ] **Step 3: Publish through a pull request**

Create a branch and PR, wait for CI, and merge only when all checks succeed.

### Task 6: Make E2 commands additive to upstream commands

**Files:**
- Modify: `scripts/run_real.sh`
- Modify: `README.md`
- Modify: `docs/USAGE.en.md`
- Modify: `docs/USAGE.zh-CN.md`
- Test: `tests/test_repository_contract.py`
- Test: `tests/test_usage_docs.py`

**Interfaces:**
- Consumes: Teleopit's `run_sim.py` and `run_sim2real.py` command surfaces.
- Produces: matching upstream command examples followed by E2-specific config
  and hand overrides; the guarded real launcher forwards extra Hydra overrides.

- [x] **Step 1: Add failing command-alignment tests**

Require both guides to show the unchanged upstream sim and sim2real commands,
then the E2 variants based on those commands. Require the real launcher to
forward `"$@"` after its guarded RH56E2 defaults.

- [x] **Step 2: Verify the new tests fail**

Run: `python -m unittest tests.test_repository_contract tests.test_usage_docs -v`

Expected: failure because the guides omit the upstream/E2 command pairs and
`scripts/run_real.sh` drops additional Hydra overrides.

- [x] **Step 3: Align launch behavior and documentation**

Append `"$@"` to the real Teleopit invocation. Replace mandatory path exports
in the default guide with `cd ~/teleopit-rh56e2-repro` and `cd ~/Teleopit`.
Document the upstream command first and its E2 extension immediately after it.

- [ ] **Step 4: Run deterministic verification**

Run: `python -m compileall -q src overlay scripts tests`,
`python -m unittest discover -s tests -v`, and
`bash -n scripts/run_real.sh scripts/run/*.sh`.

Expected: all checks pass; hardware is not contacted.

