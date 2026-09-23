# RH56E2 Python SDK Design

## Goal

Provide a standalone, dependency-light Python SDK for the Inspire RH56E2 and
make Teleopit consume that SDK instead of maintaining a second Modbus
implementation. The first release covers the hardware behavior already used by
this repository: single- and dual-hand connection management, six-channel
telemetry, speed commands, and position commands.

The SDK must be useful without Teleopit, somehand, PICO, or NumPy. Hardware
writes remain disabled by default and require explicit opt-in.

## Package Architecture

The canonical implementation will live under `src/teleopit_rh56e2/sdk/`:

```text
teleopit_rh56e2.sdk
├── __init__.py       public exports
├── protocol.py       Modbus TCP framing and synchronous transport
├── models.py         telemetry value objects and public exceptions
├── hand.py           single-hand public API and safety gates
└── dual.py           dual-hand lifecycle and coordinated operations
```

`protocol.py` will use only Python's standard library. It will own MBAP/PDU
encoding, response validation, socket timeouts, exact-length reads, and
connection cleanup. It will not contain Teleopit configuration or hand-pose
retargeting.

`hand.py` will turn protocol registers into a stable device API. It will own
command validation, write interlocking, health refresh, fault checks, and
temperature checks. `dual.py` will compose two single-hand clients without
duplicating protocol or safety behavior.

The Teleopit overlay will retain configuration parsing and PICO/somehand pose
mapping. Its RH56E2 device adapter will delegate communication and safety to
the SDK. The former
`teleopit.sim2real.hands.rh56e2_protocol` module will remain as a deprecated
compatibility re-export so current imports do not fail.

## Public API

The main single-hand constructor is:

```python
RH56E2Hand(
    host: str,
    port: int = 6000,
    *,
    unit_id: int = 0xFF,
    timeout: float = 0.5,
    write_enabled: bool = False,
    max_temperature_c: int = 70,
)
```

It supports `connect()`, `close()`, and context-manager use. Its first-version
operations are:

- `read_telemetry() -> RH56E2Telemetry`
- `set_speed(values: Sequence[int]) -> None`
- `set_positions(values: Sequence[int]) -> None`

Every speed or position command must contain exactly six integers. Positions
accept controller values `0..1000` and the existing `-1` hold sentinel. Inputs
are rejected rather than padded, truncated, clipped, or silently converted.

`RH56E2Telemetry` is an immutable data object containing six values each for
angle, force, current, fault, state, and temperature. It provides the data
needed by both standalone programs and the Teleopit adapter without exposing
raw Modbus frames.

`RH56E2Pair` accepts distinct left and right `RH56E2Hand` instances (or
equivalent endpoint configuration), connects and closes both, reads both
telemetry snapshots, and sends explicitly separated left/right speed or
position commands. It rejects duplicate `(host, port)` endpoints. If the
second connection fails, it closes the first before propagating the error.

## Safety and Errors

Read operations are always available after connection. Write operations require
`write_enabled=True` at construction. Otherwise they raise
`WriteDisabledError` without sending a Modbus request.

Before every hardware write, the hand must have current health information.
The implementation will read or refresh fault and temperature values, then
reject the command when telemetry is unavailable, any fault byte is nonzero,
or any temperature exceeds `max_temperature_c`. This check applies equally to
standalone SDK use and Teleopit use.

The public exception hierarchy will distinguish:

- SDK validation and configuration errors;
- connection and timeout failures;
- malformed or exception Modbus responses;
- disabled writes;
- device fault and over-temperature safety refusals.

The SDK will not silently reconnect or retry a write because a repeated command
may be unsafe. Callers may reconnect explicitly after inspecting the failure.
The first release does not add convenience gestures such as full-open,
full-close, or grasp sequences.

## Installation and Compatibility

The repository installer will install this repository into the active
`teleopit` environment in editable mode with `--no-deps`, after the pinned
runtime dependencies are installed. This makes
`from teleopit_rh56e2.sdk import RH56E2Hand` available on the Unitree host
without causing pip to resolve a second Teleopit checkout.

The existing direct Teleopit commands, Hydra configuration keys, preflight
tools, bench tool, and guarded launchers remain valid. The Teleopit adapter will
translate its existing configuration into SDK clients, so users do not need to
change G1 + E2 startup commands.

The old Teleopit protocol module will contain imports only and emit a standard
deprecation warning when imported directly. It will be retained for the current
release so repository tools and downstream scripts have a migration window.

## Documentation and Examples

English and Chinese SDK reference pages will have matching headings and
commands. They will include:

- a read-only single-hand example;
- a guarded single-hand speed and position example;
- a dual-hand example with distinct endpoints;
- the `0..1000` controller convention and `-1` hold behavior;
- explicit warnings that `write_enabled=True` permits physical movement;
- exception handling and guaranteed `close()` through context managers.

The README will link to the detailed references but remain concise.

## Testing and Acceptance

Protocol unit tests will move to the canonical SDK import path. A local fake
device or socket fixture will verify connection lifecycle, telemetry parsing,
partial reads, timeouts, closed connections, malformed frames, and Modbus
exception responses without requiring physical hardware.

Device tests will verify:

- writes are disabled by default and send no bytes;
- commands require exactly six valid values;
- fault, stale/unavailable health, and over-temperature conditions block writes;
- valid opted-in speed and position writes use the documented registers;
- duplicate dual-hand endpoints are rejected;
- partial dual-hand connection failure closes the connected side;
- context managers close sockets after success and exceptions.

Compatibility tests will verify that the former Teleopit protocol imports
resolve to SDK implementations and that the Teleopit adapter calls the SDK
while retaining current configuration and launcher behavior.

Repository acceptance requires compile checks, the complete unittest and pytest
suites, Ruff, mirrored English/Chinese documentation checks, and an installer
contract test confirming that the SDK is importable. These checks demonstrate
software behavior only; physical E2 acceptance remains a separate staged
hardware procedure.

## Out of Scope

- Registers and commands not used by the current verified control path.
- Async I/O, ROS bindings, remote services, or a graphical control panel.
- Automatic discovery, automatic IP configuration, and silent reconnects.
- Publishing a separate package to PyPI in this iteration.
- Claiming physical safety certification or hardware acceptance from tests.
