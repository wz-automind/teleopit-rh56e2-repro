# Bilingual Usage Guides Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add matching Chinese and English usage guides that take a new operator from Linux prerequisites and Python virtual-environment setup through simulation, read-only hardware checks, guarded RH56E2 bench motion, G1 standing validation, and full real-robot testing.

**Architecture:** Keep the two guides structurally identical and make every command use repository-relative paths plus the installer-managed `$HOME/Teleopit/.venv`. Add a small single-hand bench utility so the documented staged acceptance process has an executable, deliberately gated motion test instead of requiring ad-hoc Python snippets.

**Tech Stack:** Markdown, Python 3.10+, Bash, Teleopit v0.5.0, somehand 0.3.0, Modbus TCP.

**Spec:** User request in this task and `docs/真机控制检查.md`.

## Global Constraints

- The Chinese and English guides must have the same section order and commands.
- Installation and read-only preflight must never write hand registers.
- Bench motion must require both `--write` and the exact confirmation phrase `MOVE_RH56E2`.
- Full G1 control must retain the existing `ENABLE_G1_REAL=YES` and `ENABLE_RH56E2_WRITES=YES` gates.
- Clearly separate command frequency from end-to-end latency and static code compatibility from physical verification.
- Do not commit credentials, tokens, device serial numbers, private IP assumptions, or generated virtual environments.

---

### Task 1: Add a guarded single-hand bench test

**Files:**
- Create: `scripts/rh56e2_bench_test.py`
- Create: `tests/test_rh56e2_bench_test.py`

**Interfaces:**
- Consumes these symbols from the installed overlay:
  - `Rh56e2ModbusClient`
  - `ANGLE_ACT`
  - `ANGLE_SET`
  - `SPEED_SET`
  - `FAULT_ACT`
  - `TEMPERATURE_ACT`
- Produces: a CLI that is read-only by default and can move one selected DOF by a bounded relative delta only after explicit confirmation.

- [x] **Step 1: Write parser and target-calculation tests**

Test the target calculation:

```python
bounded_target(500, 50) == 550
```

Also test that values clamp to the inclusive range `0..1000`, and that motion authorization rejects missing or incorrect confirmation text.

- [x] **Step 2: Run the focused tests and confirm they fail before implementation**

Run: `python -m unittest tests.test_rh56e2_bench_test -v`

Expected: import failure because `scripts.rh56e2_bench_test` does not exist.

- [x] **Step 3: Implement the read-only default and guarded relative move**

The CLI reads angle, fault, and temperature first. Motion requires this exact gate:

```text
--write --confirm MOVE_RH56E2
```

After authorization, it writes a low speed, moves one DOF by at most 100 units while sending `-1` to the other five, reads feedback, restores the initial target, and closes the socket.

- [x] **Step 4: Run tests and compilation**

Run: `python -m unittest tests.test_rh56e2_bench_test -v`

Expected: all tests pass without a network connection.

### Task 2: Write matching Chinese and English guides

**Files:**
- Create: `docs/USAGE.zh-CN.md`
- Create: `docs/USAGE.en.md`

**Interfaces:**
- Consumes these repository entry points:
  - `scripts/install.sh`
  - `scripts/validate.sh`
  - `scripts/rh56e2_preflight.py`
  - `scripts/rh56e2_bench_test.py`
  - `scripts/run_real.sh`
- Produces: operator-facing procedures with identical headings and command blocks.

- [x] **Step 1: Document prerequisites, clone, virtual environment, installation, and configuration**

Include generated paths, activation commands, environment variables, PICO networking, and two-hand IP requirements.

- [x] **Step 2: Document simulation and validation**

Include offline validation, PICO simulation launch, expected success indicators, and stop conditions.

- [x] **Step 3: Document staged hardware testing**

Include single-hand read-only preflight, guarded relative motion, two-hand preflight, G1 dry-run, supported standing test, full real launch, remote-control state transitions, emergency stop, and post-run checks.

- [x] **Step 4: Add troubleshooting and command reference**

Cover missing assets/modules, network timeouts, duplicate IPs, nonzero fault bytes, overtemperature, no G1 LowState, and PICO tracking loss.

### Task 3: Link the guides and verify parity

**Files:**
- Modify: `README.md`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: both usage guides and the bench utility.
- Produces: discoverable language links and automated source checks.

- [x] **Step 1: Add language links near the README introduction**

Link `docs/USAGE.zh-CN.md` as 中文使用手册 and `docs/USAGE.en.md` as English Usage Guide.

- [x] **Step 2: Include the bench utility in CI compilation and unit tests**

Keep the existing `compileall` and unittest discovery commands; ensure the new files are included by those directory-level commands.

- [x] **Step 3: Verify all commands, links, and bilingual section parity**

Run Python compilation, all unit tests, Markdown link checks for repository-relative targets, and compare the ordered headings in the two guides.

- [ ] **Step 4: Publish through a reviewed GitHub change**

Create a branch and pull request, wait for CI, then merge only if checks pass.

