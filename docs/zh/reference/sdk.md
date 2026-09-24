# RH56E2 Python SDK

## Installation and import

将本仓库安装到当前 Python 环境。`--no-build-isolation --no-deps` 使已固定
版本的 Teleopit 环境继续负责其构建和运行时依赖项。

```bash
python -m pip install --no-build-isolation --no-deps -e .
```

```python
from teleopit_rh56e2.sdk import (
    DeviceSafetyError,
    RH56E2ConnectionError,
    RH56E2Hand,
    RH56E2Pair,
    RH56E2ValidationError,
    WriteDisabledError,
)
```

`RH56E2Hand(host, port=6000, *, unit_id=0xFF, timeout=0.5,
write_enabled=False, max_temperature_c=70)` 是公开的单手 API。仅在已检查
手、供电、以太网地址、急停和清空工作区后连接。

## Read-only single hand

连接后即可读取，且无需开启写入。上下文管理器会在进入时连接，并在退出时
关闭 socket，即使发生异常也一样。

```python
from teleopit_rh56e2.sdk import RH56E2Hand

with RH56E2Hand("192.168.123.210") as hand:
    telemetry = hand.read_telemetry()
    print(telemetry.angle, telemetry.temperature)
```

`192.168.123.210` 只是已验证部署示例；请使用本环境中分配的地址。在
`connect()` 或进入上下文管理器完成前，手并未连接。

## Guarded single-hand writes

> **Physical-motion warning:** `write_enabled=True` permits physical movement.
> 只有在只读检查通过、手空载或已受控、工作区清空且操作员准备停止运动后，
> 才可以启用它。

写入默认关闭。每次 `set_speed` 或 `set_positions` 调用都会先刷新故障和温度
遥测；故障非零、温度超过 `max_temperature_c`（默认 `70`，支持的配置范围为
`1..100`）或健康状态无法读取都会阻止命令。构造时的 `write_enabled` 设置为
只读；如需更改，必须创建新的手实例。

```python
from teleopit_rh56e2.sdk import RH56E2Hand

with RH56E2Hand("192.168.123.210", write_enabled=True) as hand:
    hand.set_speed([200, 200, 200, 200, 200, 200])
    hand.set_positions([500, 500, 500, 500, 500, -1])
```

每条命令都有恰好六个整数通道。`set_speed` 接受 `0..1000`。`set_positions`
接受 `0..1000`；仅位置还接受 `-1`，即固件的保持/不改变哨兵值。SDK 会拒绝
短向量、浮点数、布尔值、越界值和速度 `-1`，不会填充、裁剪或转换它们。

## Dual hand

从明确命名且不同的端点构造双手。`RH56E2Pair` 拒绝重复的 `(host, port)`
端点，按左后右连接；如果右手连接失败，会关闭左手。

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

`192.168.123.210` 和 `192.168.123.211` 是已验证部署示例；两个环境专用地址
都可能不同。在每只手均已分别通过只读和物理方向检查前，不要使用双手。

双手命令会在任一侧发送前预先验证两侧命令及两只手的本地写入/连接状态。
实际写入按左后右顺序执行，并非原子操作：左侧命令成功后，右侧仍可能发生
设备或网络故障。

## Telemetry and limits

`read_telemetry()` 返回不可变的 `RH56E2Telemetry` 快照。它有六个元组字段：
`angle`、`force`、`current`、`fault`、`state` 和 `temperature`；不要修改快照，
也不要将较早快照视为之后写入的许可。SDK 会在每次写入前立即读取新的健康状态。

六通道控制器约定不变：`0..1000` 是允许的命令范围，且 `-1` 只可作为位置的
保持/不改变哨兵值。方向、物理行程和安全速度取决于部署的手，必须在硬件上验证。

## Errors and cleanup

请显式处理连接、写入关闭和设备安全失败。SDK 不会静默重连或重试写入，因为
重复命令可能不安全。

```python
from teleopit_rh56e2.sdk import (
    DeviceSafetyError,
    RH56E2ConnectionError,
    RH56E2Hand,
    RH56E2ValidationError,
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
except RH56E2ValidationError as error:
    raise RuntimeError(f"invalid SDK configuration or command: {error}") from error
```

> **Physical-motion warning:** `write_enabled=True` permits physical movement.
> 绝不能将软件测试视为针对某只手、固件、电源、负载、网络或工作区的物理验收
> 或安全认证。

正常操作请使用上下文管理器。若必须手动管理生命周期，请在 `read_telemetry`、
`set_speed` 或 `set_positions` 前调用 `connect()`，并始终在 `finally` 块中调用
`close()`。
