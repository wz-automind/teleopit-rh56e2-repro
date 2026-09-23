# RH56E2 Python SDK Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, safe-by-default RH56E2 Python SDK and make the existing Teleopit E2 integration consume it without changing operator commands.

**Architecture:** Move the canonical standard-library Modbus transport into `teleopit_rh56e2.sdk`, layer immutable telemetry and guarded single-/dual-hand APIs above it, and retain the Teleopit protocol module as a compatibility re-export. The Teleopit overlay remains responsible only for Hydra configuration and PICO/somehand mapping.

**Tech Stack:** Python 3.10+, standard-library `socket`/`struct`/`threading`, dataclasses, unittest/pytest, Ruff, Bash, Teleopit overlay

**Spec:** `docs/superpowers/specs/2026-09-23-rh56e2-python-sdk-design.md`

## Global Constraints

- The standalone SDK must not depend on Teleopit, somehand, PICO, or NumPy.
- Python 3.10 is the minimum supported version.
- Hardware writes default to disabled and require `write_enabled=True`.
- Every write requires valid fault and temperature telemetry immediately before the command.
- Commands contain exactly six integers; position values are `-1` or `0..1000`, speed values are `0..1000`, and invalid values are rejected without padding, clipping, or coercing floats.
- Preserve all current Teleopit Hydra keys, scripts, and G1 + E2 startup commands.
- Keep `teleopit.sim2real.hands.rh56e2_protocol` as a deprecated compatibility import for this release.
- Tests prove software behavior only and must not claim physical hardware acceptance.

## Review Focus

- Boolean values passed as command integers must be rejected even though `bool` subclasses `int`.
- NaN/infinite/zero/negative timeouts and invalid ports/unit IDs must fail before opening a socket.
- A short socket read or peer close must fail deterministically and never return partial telemetry.
- A failed second-hand connection must close the first hand and leave the pair disconnected.
- A telemetry read followed by a fault/temperature change must not permit a write using stale health data.

---

### Task 1: Canonical Modbus Protocol Package

**Files:**
- Create: `src/teleopit_rh56e2/sdk/models.py`
- Create: `src/teleopit_rh56e2/sdk/protocol.py`
- Create: `tests/test_sdk_protocol.py`
- Modify: `src/teleopit_rh56e2/sdk/__init__.py` (created in this task)
- Modify: `src/teleopit_rh56e2/__init__.py`

**Interfaces:**
- Consumes: Python socket-compatible objects with `sendall`, `recv`, `shutdown`, and `close`.
- Produces: `RH56E2Error`, `RH56E2ConnectionError`, `ModbusProtocolError`, register constants, frame helpers, and `RH56E2ModbusClient(host, port=6000, *, unit_id=0xFF, timeout=0.5)` with `connect()`, `read_holding()`, `read_bytes()`, `write_holding()`, and `close()`.

- [ ] **Step 1: Write failing protocol and validation tests**

Create `tests/test_sdk_protocol.py` by moving the existing frame assertions from `tests/test_rh56e2.py` to imports from `teleopit_rh56e2.sdk.protocol`, then add:

```python
def test_constructor_rejects_invalid_network_values(self):
    for kwargs in ({"port": 0}, {"port": 65536}, {"unit_id": -1}, {"unit_id": 256}, {"timeout": 0}, {"timeout": float("nan")}):
        with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
            RH56E2ModbusClient("192.0.2.10", **kwargs)

def test_write_rejects_bool_and_float_registers(self):
    for value in (True, 1.0):
        with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
            build_write_frame(1, 0xFF, ANGLE_SET, [value] * 6)
```

Use a `FakeSocket` whose `recv()` returns configured chunks to assert exact-length reads, peer-close failure, and `close()` idempotence.

- [ ] **Step 2: Run the new tests and verify RED**

Run: `python -m unittest tests.test_sdk_protocol -v`

Expected: FAIL because `teleopit_rh56e2.sdk.protocol` does not exist.

- [ ] **Step 3: Implement the canonical protocol module**

Define the base exceptions in `models.py`. Move the behavior from `overlay/teleopit/sim2real/hands/rh56e2_protocol.py` into `src/teleopit_rh56e2/sdk/protocol.py`. Rename the client to `RH56E2ModbusClient`, validate constructor arguments before socket creation, reject `bool`/non-integral register values, retain `-1 -> 0xFFFF`, wrap connect/send/receive socket failures as `RH56E2ConnectionError`, and allow a socket factory injection used only by tests:

```python
class RH56E2ModbusClient:
    def __init__(self, host: str, port: int = 6000, *, unit_id: int = 0xFF,
                 timeout: float = 0.5, socket_factory: Callable[..., socket.socket] = socket.socket): ...
```

Export public protocol names from `src/teleopit_rh56e2/sdk/__init__.py`; keep the package root exporting only `__version__`.

- [ ] **Step 4: Run protocol tests and static checks**

Run: `python -m unittest tests.test_sdk_protocol -v && python -m compileall -q src/teleopit_rh56e2/sdk`

Expected: all protocol tests PASS and compileall exits 0.

- [ ] **Step 5: Commit the protocol package**

```bash
git add src/teleopit_rh56e2 tests/test_sdk_protocol.py
git commit -m "feat: add canonical RH56E2 Modbus protocol"
```

### Task 2: Safe Single-Hand SDK

**Files:**
- Modify: `src/teleopit_rh56e2/sdk/models.py`
- Create: `src/teleopit_rh56e2/sdk/hand.py`
- Modify: `src/teleopit_rh56e2/sdk/__init__.py`
- Create: `tests/test_sdk_hand.py`

**Interfaces:**
- Consumes: `RH56E2ModbusClient` and register constants from Task 1.
- Produces: immutable `RH56E2Telemetry`; additional exceptions `WriteDisabledError` and `DeviceSafetyError` under `RH56E2Error`; `RH56E2Hand(host, port=6000, *, unit_id=0xFF, timeout=0.5, write_enabled=False, max_temperature_c=70, client=None)`.

- [ ] **Step 1: Write failing telemetry and read-path tests**

Create a `FakeClient` that records reads/writes. Assert context-manager connect/close behavior and exact telemetry fields:

```python
def test_read_telemetry_returns_immutable_six_channel_snapshot(self):
    hand = RH56E2Hand("192.0.2.10", client=FakeClient())
    hand.connect()
    sample = hand.read_telemetry()
    self.assertEqual(sample.angle, (100, 101, 102, 103, 104, 105))
    self.assertEqual(sample.fault, (0, 0, 0, 0, 0, 0))
    with self.assertRaises(dataclasses.FrozenInstanceError):
        sample.angle = ()
```

Also assert read-before-connect raises a clear `ConnectionError`.

- [ ] **Step 2: Run the read tests and verify RED**

Run: `python -m unittest tests.test_sdk_hand -v`

Expected: FAIL because `RH56E2Hand` and `RH56E2Telemetry` do not exist.

- [ ] **Step 3: Implement models and the read path**

Implement `RH56E2Telemetry` as `@dataclass(frozen=True)` with tuple fields `angle`, `force`, `current`, `fault`, `state`, and `temperature`. Convert force registers from unsigned wire values to signed 16-bit integers; preserve the other documented values. Implement connection lifecycle, `endpoint`, context-manager methods, and `read_telemetry()` using `ANGLE_ACT`, `FORCE_ACT`, `CURRENT_ACT`, `FAULT_ACT`, `STATE_ACT`, and `TEMPERATURE_ACT`.

- [ ] **Step 4: Write failing write-interlock and fresh-health tests**

Add tests asserting:

```python
def test_write_is_disabled_by_default_and_sends_nothing(self):
    client = FakeClient()
    hand = connected_hand(client=client)
    with self.assertRaises(WriteDisabledError):
        hand.set_positions([500] * 6)
    self.assertEqual(client.writes, [])

def test_each_write_refreshes_health_before_sending(self):
    client = FakeClient(fault_reads=[(0,) * 6, (1, 0, 0, 0, 0, 0)])
    hand = connected_hand(client=client, write_enabled=True)
    hand.set_positions([500] * 6)
    with self.assertRaises(DeviceSafetyError):
        hand.set_positions([501] * 6)
    self.assertEqual(len(client.writes_to(ANGLE_SET)), 1)
```

Cover over-temperature, unreadable health, exactly-six validation, `bool`, float, out-of-range speed/position, and `-1` allowed only for positions.

- [ ] **Step 5: Implement guarded speed and position writes**

Implement `set_speed()` and `set_positions()`. Both call a private fresh-health read immediately before `write_holding`; both reject writes before any protocol request when disabled or structurally invalid. Use `SPEED_SET` and `ANGLE_SET` respectively and raise `DeviceSafetyError` for fault/temperature/unreadable health.

- [ ] **Step 6: Run all single-hand tests**

Run: `python -m unittest tests.test_sdk_hand -v`

Expected: all tests PASS.

- [ ] **Step 7: Commit the single-hand SDK**

```bash
git add src/teleopit_rh56e2/sdk tests/test_sdk_hand.py
git commit -m "feat: add guarded RH56E2 hand API"
```

### Task 3: Dual-Hand SDK

**Files:**
- Create: `src/teleopit_rh56e2/sdk/dual.py`
- Modify: `src/teleopit_rh56e2/sdk/__init__.py`
- Create: `tests/test_sdk_pair.py`

**Interfaces:**
- Consumes: `RH56E2Hand`, `RH56E2Telemetry` from Task 2.
- Produces: `RH56E2Pair(left: RH56E2Hand, right: RH56E2Hand)` with lifecycle, `read_telemetry() -> dict[str, RH56E2Telemetry]`, `set_speeds(*, left, right)`, and `set_positions(*, left, right)`.

- [ ] **Step 1: Write failing pair lifecycle tests**

```python
def test_duplicate_endpoints_are_rejected(self):
    with self.assertRaisesRegex(ValueError, "distinct"):
        RH56E2Pair(RH56E2Hand("192.0.2.10"), RH56E2Hand("192.0.2.10"))

def test_second_connect_failure_closes_first(self):
    left, right = FakeHand(), FakeHand(connect_error=ConnectionError("offline"))
    with self.assertRaises(ConnectionError):
        RH56E2Pair(left, right).connect()
    self.assertEqual(left.close_calls, 1)
```

Also test pair context cleanup after an exception and left/right values never swap.

- [ ] **Step 2: Run the pair tests and verify RED**

Run: `python -m unittest tests.test_sdk_pair -v`

Expected: FAIL because `RH56E2Pair` does not exist.

- [ ] **Step 3: Implement the pair as a thin composition layer**

Validate distinct endpoints in `__init__`, connect left then right with rollback, close both even if one close fails, and delegate reads/writes without adding retries or bypassing either hand's safety gate.

- [ ] **Step 4: Run pair and SDK tests**

Run: `python -m unittest tests.test_sdk_protocol tests.test_sdk_hand tests.test_sdk_pair -v`

Expected: all SDK tests PASS.

- [ ] **Step 5: Commit dual-hand support**

```bash
git add src/teleopit_rh56e2/sdk tests/test_sdk_pair.py
git commit -m "feat: add dual RH56E2 SDK manager"
```

### Task 4: Migrate Teleopit and Tools to the SDK

**Files:**
- Replace: `overlay/teleopit/sim2real/hands/rh56e2_protocol.py`
- Modify: `overlay/teleopit/sim2real/hands/rh56e2.py`
- Modify: `scripts/rh56e2_preflight.py`
- Modify: `scripts/rh56e2_bench_test.py`
- Modify: `tests/test_rh56e2.py`
- Create: `tests/test_sdk_compatibility.py`

**Interfaces:**
- Consumes: SDK APIs from Tasks 1-3 and existing `Rh56e2Config`/Teleopit `HandDevice` contract.
- Produces: unchanged Teleopit configuration and runtime behavior; old protocol names re-exported from the SDK with `Rh56e2ModbusClient` aliasing `RH56E2ModbusClient`.

- [ ] **Step 1: Write failing compatibility and delegation tests**

Assert old constants/frame helpers/class aliases are identical to SDK exports and add a patched-client test proving `Rh56e2Device.send_pose()` delegates to `RH56E2Hand.set_positions()` rather than calling `write_holding()` itself.

```python
def test_legacy_protocol_client_aliases_sdk(self):
    from teleopit.sim2real.hands.rh56e2_protocol import Rh56e2ModbusClient
    from teleopit_rh56e2.sdk import RH56E2ModbusClient
    self.assertIs(Rh56e2ModbusClient, RH56E2ModbusClient)
```

- [ ] **Step 2: Run compatibility tests and verify RED**

Run: `python -m unittest tests.test_sdk_compatibility -v`

Expected: FAIL because the overlay still owns its protocol implementation and device writes.

- [ ] **Step 3: Replace the old protocol module with re-exports**

Import public constants/helpers/errors from `teleopit_rh56e2.sdk.protocol`, define `Rh56e2ModbusClient = RH56E2ModbusClient`, and issue `DeprecationWarning` with `stacklevel=2`. Do not retain copied framing or transport code.

- [ ] **Step 4: Make `Rh56e2Device` delegate to SDK hands**

Construct one `RH56E2Hand` per configured side, preserving endpoint, unit ID, timeout, write gate, and maximum temperature. Keep rate limiting, minimum-change suppression, and shutdown policy in the Teleopit adapter; delegate connect, telemetry, speed, and position operations to the SDK.

- [ ] **Step 5: Migrate preflight and bench tools to public SDK imports**

The preflight must create `RH56E2Hand(..., write_enabled=False)` and call `read_telemetry()`. The bench tool must retain `--write --confirm MOVE_RH56E2`, create the hand with `write_enabled=args.write`, and use `set_speed()`/`set_positions()`; its restoration command remains in `finally`.

- [ ] **Step 6: Run integration and legacy tests**

Run: `python -m unittest tests.test_rh56e2 tests.test_rh56e2_bench_test tests.test_sdk_compatibility -v`

Expected: all tests PASS with expected deprecation warnings captured by tests.

- [ ] **Step 7: Commit the migration**

```bash
git add overlay/teleopit/sim2real/hands scripts/rh56e2_preflight.py scripts/rh56e2_bench_test.py tests
git commit -m "refactor: use RH56E2 SDK in Teleopit runtime"
```

### Task 5: Install and Validate the SDK

**Files:**
- Modify: `scripts/install.sh`
- Modify: `scripts/validate.sh`
- Modify: `tests/test_repository_contract.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: editable repository root and active `teleopit` Conda interpreter.
- Produces: importable `teleopit_rh56e2.sdk` in installed environments without resolving a second dependency graph.

- [ ] **Step 1: Write failing installer contract tests**

Require `scripts/install.sh` to contain:

```python
self.assertIn('pip install -e "$ROOT_DIR" --no-deps', install_text)
self.assertIn("from teleopit_rh56e2.sdk import RH56E2Hand", validate_text)
```

Also assert `pyproject.toml` includes the SDK package through the existing `src` package discovery and adds no runtime dependency.

- [ ] **Step 2: Run the repository contract test and verify RED**

Run: `python -m unittest tests.test_repository_contract -v`

Expected: FAIL because the installer does not install the repository package.

- [ ] **Step 3: Install the SDK package without dependency resolution**

After installing pinned Teleopit and somehand, add:

```bash
"$TELEOPIT_PYTHON" -m pip install -e "$ROOT_DIR" --no-deps
```

Add a validation command that imports `RH56E2Hand`, constructs a read-only instance without connecting, verifies its endpoint, and exits.

- [ ] **Step 4: Run contract and import checks**

Run: `python -m unittest tests.test_repository_contract -v && python -c 'from teleopit_rh56e2.sdk import RH56E2Hand; assert RH56E2Hand("192.0.2.10").endpoint == ("192.0.2.10", 6000)'`

Expected: tests PASS and the import command exits 0.

- [ ] **Step 5: Commit installation support**

```bash
git add scripts/install.sh scripts/validate.sh tests/test_repository_contract.py pyproject.toml
git commit -m "build: install and validate RH56E2 SDK"
```

### Task 6: Bilingual SDK Documentation and Final Verification

**Files:**
- Create: `docs/en/reference/sdk.md`
- Create: `docs/zh/reference/sdk.md`
- Modify: `docs/en/README.md`
- Modify: `docs/zh/README.md`
- Modify: `README.md`
- Modify: `tests/test_usage_docs.py`

**Interfaces:**
- Consumes: final public SDK imports and method signatures.
- Produces: mirrored operator-facing English and Chinese SDK references and discoverable links.

- [ ] **Step 1: Write failing mirrored-documentation tests**

Require both reference files and these shared fragments:

```python
for fragment in ("RH56E2Hand", "RH56E2Pair", "read_telemetry", "set_speed", "set_positions", "write_enabled=True", "192.168.123.210", "192.168.123.211"):
    self.assertIn(fragment, english)
    self.assertIn(fragment, chinese)
```

Require both documentation indexes and the root README to link the SDK reference.

- [ ] **Step 2: Run documentation tests and verify RED**

Run: `python -m unittest tests.test_usage_docs -v`

Expected: FAIL because the SDK reference pages do not exist.

- [ ] **Step 3: Write the English SDK reference**

Document installation/import, read-only single-hand use, guarded single-hand speed/position writes, dual-hand use with distinct endpoints, immutable telemetry fields, `0..1000`/`-1` semantics, exception handling, context-manager cleanup, and physical-motion warnings. Use `192.168.123.210` and `.211` only as the verified deployment example and state that environment-specific addresses may differ.

- [ ] **Step 4: Write the matching Chinese reference and add links**

Use identical headings, code, defaults, limits, and warnings in `docs/zh/reference/sdk.md`. Add concise index and README links; do not duplicate the full guide in the README.

- [ ] **Step 5: Run full repository verification**

Run:

```bash
python -m compileall -q src overlay scripts tests
python -m unittest discover -s tests -v
pytest -q
ruff check src overlay/teleopit/sim2real/hands scripts tests
git diff --check
```

Expected: every command exits 0, all tests pass, and Ruff/diff checks report no errors.

- [ ] **Step 6: Confirm no duplicate protocol implementation remains**

Run: `rg -n "def build_read_frame|class RH56E2ModbusClient|class Rh56e2ModbusClient" src overlay`

Expected: implementations exist only under `src/teleopit_rh56e2/sdk/protocol.py`; the overlay contains only imports/aliases.

- [ ] **Step 7: Commit documentation and verification contracts**

```bash
git add README.md docs/en docs/zh tests/test_usage_docs.py
git commit -m "docs: add RH56E2 SDK usage guides"
```
