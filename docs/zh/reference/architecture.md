# 架构与请求流

## 组件职责

| 组件 | 在本仓库中负责 | 在本仓库中不负责 |
| --- | --- | --- |
| pico-bridge 0.2.1 | PICO 网络接收器以及头显、手柄、手部、身体帧 | G1 策略、手部 IK、RH56E2 协议 |
| Teleopit 0.5.0 | 输入生命周期、身体重定向、参考时间线、策略、G1 仿真/真机、手部 worker 生命周期 | RH56E2 运动学和厂商寄存器 |
| somehand 0.3.0 | 通过 YAML 加载 RH56E2 运动学并完成地标到关节的优化 | PICO 接收器生命周期和真机写入 |
| RH56E2 集成层 | 模型/配置、弧度到原始值映射、Modbus TCP、健康检查和写入门控 | G1 底层控制 |

## 请求流

1. `pico_bridge.PicoBridge` 在 Teleopit 主机接收 PICO 帧。
2. Teleopit 的 `Pico4InputProvider` 使用身体跟踪生成 G1 参考，并从同一个接收器公开手部快照，不启动第二个 PICO 接收器。
3. `pico_hand_to_landmarks()` 把一只手的 PICO 26 关节状态转换为 somehand 使用的 21 地标表示。
4. `somehand.api.RetargetingEngine` 加载左右 RH56E2 YAML 和 MJCF，求解关节目标。
5. `Rh56e2SomehandMapper` 按小指、无名指、中指、食指、拇指弯曲、拇指旋转的顺序选择六个驱动关节。
6. `radians_to_raw()` 把模型弧度映射到 RH56E2 单位（`0` 闭合、`1000` 张开），输出 `HandPoseCommand`。
7. 仿真时，RH56E2 session 把关节目标写入 MuJoCo；真机时，`HandRuntime` 调用 `Rh56e2Device`，先经过频率、变化量、故障、温度、跟踪超时和写使能门控，再发送 FC16。

## 运行频率与延迟

- PICO 手部重定向配置为 60 Hz。
- RH56E2 真机 worker 默认 30 Hz。
- G1 策略路径为 50 Hz，PD 控制为 200 Hz。

这些是各阶段更新频率，不是端到端延迟。网络抖动、重定向计算、进程调度、设备响应时间和 G1 控制都会影响实测延迟。

## 源码结构

```text
overlay/teleopit/                    安装到 Teleopit 的文件
  configs/                           Hydra 集成配置
  sim/                               双手 MuJoCo session
  sim2real/hands/rh56e2_protocol.py  寄存器、协议帧、TCP 传输
  sim2real/hands/rh56e2.py           配置、安全、somehand 映射与设备层
overlay/third_party/somehand/         RH56E2 MJCF 和重定向 YAML
scripts/setup/                        安装入口
scripts/run/                          仿真与真机入口
scripts/dev/                          验证与受保护工作台工具
```

安装器检出 `manifest.json` 中的精确上游版本，再把 overlay 文件复制到完全一致的相对目标路径。标记文件记录已安装的基础版本，避免把无关的脏工作区误认为已验证环境。

## 失败行为

- 手部跟踪缺失或过期时，仅在写入已启用的情况下发送保持值 `-1`。
- 手部故障非零或温度过高时阻止后续写入。
- 左右手端点重复时配置解析直接失败。
- 手部 worker 失败不会结束 Teleopit 的 G1 进程，但这不代表剩余物理状态一定安全。
- 除非显式启用 `open_on_shutdown`，退出时不会主动张手。

[RH56E2 参考](rh56e2.md) · [完整使用手册](../../USAGE.zh-CN.md)
