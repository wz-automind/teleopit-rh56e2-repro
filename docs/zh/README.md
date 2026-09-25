# Teleopit RH56E2 文档

Teleopit RH56E2 是建立在 Teleopit、somehand 和 pico-bridge 基础上的集成发行仓库。它增加因时 Inspire RH56E2 的仿真、手部重定向和受保护真机控制，同时保留各上游项目原有的职责边界。

## 从这里开始

| 主题 | 文档 |
| --- | --- |
| 从干净主机到仿真和真机测试 | [完整使用手册](usage.md) |
| 组件职责和运行时请求流 | [架构与数据流](reference/architecture.md) |
| RH56E2 模型、通道、寄存器、配置与安全 | [RH56E2 参考](reference/rh56e2.md) |
| 独立只读和受保护写入 API | [Python SDK 参考](reference/sdk.md) |
| 固定版本与上游升级流程 | [上游维护](reference/upstreams.md) |


## 支持边界

仓库测试覆盖源码集成、协议帧、映射、配置门控和文档结构；它不能替代针对具体机器人、固件、电源、网络、负载和工作区的物理安全认证。

[English documentation](../en/README.md) · [仓库首页](../../README.md)
