# Teleopit RH56E2 文档

Teleopit RH56E2 是建立在 Teleopit、somehand 和 pico-bridge 基础上的集成发行仓库。它增加因时 Inspire RH56E2 的仿真、手部重定向和受保护真机控制，同时保留各上游项目原有的职责边界。

## 从这里开始

| 主题 | 文档 |
| --- | --- |
| 从开发机打包到 G1 离线合入与真机测试 | [完整使用手册](usage.md) |
| 组件职责和运行时请求流 | [架构与数据流](reference/architecture.md) |
| RH56E2 模型、通道、寄存器、配置与安全 | [RH56E2 参考](reference/rh56e2.md) |
| 独立只读和受保护写入 API | [Python SDK 参考](reference/sdk.md) |
| 固定版本与上游升级流程 | [上游维护](reference/upstreams.md) |
## 推荐阅读顺序

1. 先读架构文档，明确每个环节由哪个项目负责。
2. 按完整使用手册把仓库或完整 Teleopit 包传到 G1，并合入已有运行目录。
3. 连接手部电源或网线前阅读 RH56E2 和 Python SDK 参考。
4. 逐级完成真机测试，不要第一次就启动全身控制。

## 支持边界

仓库测试覆盖源码集成、协议帧、映射、配置门控和文档结构；它不能替代针对具体机器人、固件、电源、网络、负载和工作区的物理安全认证。

[English documentation](../en/README.md) · [仓库首页](../../README.md)
