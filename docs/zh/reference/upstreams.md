# 上游维护

## 固定的基础项目

`manifest.json` 是机器可读的事实来源。当前集成面向 Teleopit v0.5.0、somehand 0.3.0 和 pico-bridge v0.2.1。Teleopit 与 somehand 使用完整 commit SHA 固定；pico-bridge wheel/APK 使用版本和 SHA-256 固定。

## 为什么使用 overlay

本仓库不是三个无关历史的代码快照。`manifest.json` 记录经过审查的 Teleopit、
somehand 和 pico-bridge 版本。完整且准备好的 Teleopit 目录和本集成仓库都在
开发机打包并传到 G1；先解压 Teleopit，再把集成文件复制到其正常上游路径。最终
运行目录保持 Teleopit 的结构，而本仓库需要审查的范围只包含 RH56E2 相关增加。

因此 overlay 是“路径兼容的集成层”，不是运行时 monkey patch：离线合入时
`overlay/teleopit/sim2real/hands/rh56e2.py` 会复制为
`/home/unitree/Teleopit/teleopit/sim2real/hands/rh56e2.py`。

## 升级流程

1. 阅读上游更新日志和迁移说明。
2. 每次只升级一个上游，并同步修改 `manifest.json` 和 `pyproject.toml`。
3. 在开发机兼容副本上验证 overlay；打包完整的已测试 Teleopit，并在替换已部署副本前保留备份。
4. 运行编译、单测、Ruff、shell 语法和离线模型验证。
5. 运行 PICO 仿真，核对左右、轴向、模式、暂停/恢复和跟踪超时。
6. 连续真机控制前重新完成只读遥测和单自由度分阶段测试。
7. 在 PR 和仓库历史中记录已测试版本与未测试的物理条件。

## 必须复查的兼容点

- Teleopit 手部协议、worker 构造、Hydra 配置键、PICO 快照类型和 G1 状态切换。
- somehand 公共 `somehand.api`、YAML schema、关节名、qpos 索引、模型轴向和求解输出。
- pico-bridge wheel/API 版本、帧字段、26 关节顺序、时间戳、重连行为及 APK/wheel 哈希。
- RH56E2 固件 Unit ID、寄存器行为、地址配置、响应帧、关节方向、温度语义和保持命令。


[架构与数据流](architecture.md) · [第三方组件](../../../THIRD_PARTY.md)
