# RH56E2 Python SDK

## Installation and import

Install this repository into the active Python environment. `--no-deps` keeps
the pinned Teleopit environment in control of its dependencies.

```bash
python -m pip install --no-deps -e .
```

```python
from teleopit_rh56e2.sdk import (
    DeviceSafetyError,
    RH56E2ConnectionError,
    RH56E2Hand,
    RH56E2Pair,
    WriteDisabledError,
)
```

`RH56E2Hand(host, port=6000, *, unit_id=0xFF, timeout=0.5,
write_enabled=False, max_temperature_c=70)` is the public single-hand API.
Connect only after the hand, power, Ethernet addressing, emergency stop, and
clear work area have been checked.

## Read-only single hand

Reads are available after connection and do not require write opt-in. The
context manager connects on entry and closes the socket on exit, including when
an exception is raised.

```python
from teleopit_rh56e2.sdk import RH56E2Hand

with RH56E2Hand("192.168.123.210") as hand:
    telemetry = hand.read_telemetry()
    print(telemetry.angle, telemetry.temperature)
```

`192.168.123.210` is a verified deployment example only; use the address
assigned in your environment. A hand is not connected until `connect()` or
context-manager entry has completed.

## Guarded single-hand writes

> **Physical-motion warning:** `write_enabled=True` permits physical movement.
> Use it only after read-only checks pass, with the hand unloaded or otherwise
> controlled, a clear work area, and an operator ready to stop motion.

Writes are disabled by default. Each `set_speed` or `set_positions` call first
refreshes fault and temperature telemetry; a nonzero fault, a temperature above
`max_temperature_c` (default `70`), or unreadable health blocks the command.

```python
from teleopit_rh56e2.sdk import RH56E2Hand

with RH56E2Hand("192.168.123.210", write_enabled=True) as hand:
    hand.set_speed([200, 200, 200, 200, 200, 200])
    hand.set_positions([500, 500, 500, 500, 500, -1])
```

Every command has exactly six integer channels. `set_speed` accepts `0..1000`.
`set_positions` accepts `0..1000`; only positions also accept `-1`, the
firmware hold/no-change sentinel. The SDK rejects short vectors, floats,
booleans, out-of-range values, and `-1` speeds rather than padding, clipping,
or converting them.

## Dual hand

Construct a pair from explicitly named, distinct endpoints. `RH56E2Pair`
rejects duplicate `(host, port)` endpoints, connects left then right, and closes
the left hand if right-hand connection fails.

```python
from teleopit_rh56e2.sdk import RH56E2Hand, RH56E2Pair

left = RH56E2Hand("192.168.123.210", write_enabled=True)
right = RH56E2Hand("192.168.123.211", write_enabled=True)

with RH56E2Pair(left, right) as pair:
    snapshots = pair.read_telemetry()
    print(snapshots["left"].angle, snapshots["right"].angle)
    pair.set_speeds(left=[200] * 6, right=[200] * 6)
    pair.set_positions(left=[500] * 6, right=[500] * 6)
```

`192.168.123.210` and `192.168.123.211` are the verified deployment example;
both environment-specific addresses may differ. Do not use a pair until each
hand has passed independent read-only and physical-direction checks.

## Telemetry and limits

`read_telemetry()` returns an immutable `RH56E2Telemetry` snapshot. Its six
tuple fields are `angle`, `force`, `current`, `fault`, `state`, and
`temperature`; do not mutate a snapshot and do not treat an earlier snapshot as
approval for a later write. The SDK performs a fresh health read immediately
before every write.

The six-channel controller convention is unchanged: `0..1000` is the allowed
command range, and `-1` is available only as the position hold/no-change
sentinel. Direction, physical travel, and safe speed depend on the deployed
hand and must be verified on hardware.

## Errors and cleanup

Handle connection, disabled-write, and device-safety failures explicitly. The
SDK does not silently reconnect or retry a write, because repeating a command
may be unsafe.

```python
from teleopit_rh56e2.sdk import (
    DeviceSafetyError,
    RH56E2ConnectionError,
    RH56E2Hand,
    WriteDisabledError,
)

try:
    with RH56E2Hand("192.168.123.210", write_enabled=True) as hand:
        hand.set_positions([500] * 6)
except WriteDisabledError:
    raise RuntimeError("enable writes only after completing the safety checks")
except DeviceSafetyError as error:
    raise RuntimeError(f"write blocked by hand health: {error}") from error
except RH56E2ConnectionError as error:
    raise RuntimeError(f"check the hand network connection: {error}") from error
```

> **Physical-motion warning:** `write_enabled=True` permits physical movement.
> Never treat software tests as physical acceptance or safety certification for
> a hand, firmware, power supply, payload, network, or workcell.

Use context managers for normal operation. If manual lifecycle management is
necessary, call `connect()` before `read_telemetry`, `set_speed`, or
`set_positions`, and always call `close()` in a `finally` block.
