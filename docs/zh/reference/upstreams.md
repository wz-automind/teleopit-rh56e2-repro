# 上游维护

## 固定的基础项目

`manifest.json` 是机器可读的事实来源。当前集成面向 Teleopit v0.5.0、somehand 0.3.0 和 pico-bridge v0.2.1。Teleopit 与 somehand 使用完整 commit SHA 固定；pico-bridge wheel/APK 使用版本和 SHA-256 固定。

## 版本新鲜度检查（2026-09-22）

- Teleopit `v0.5.0` 是最新正式版，固定提交与当前 `master` 相同。
- somehand `v0.3.0` 是最新正式版；当前 `master` 另有 9 个未发布提交并包含接口删改，因此在完成兼容性验证前不跟随 `master`。
- pico-bridge `v0.2.1` 是最新正式版，仓库同时固定 wheel 和 APK 的 SHA-256。
- `xr_teleoperate` 仅作为 E2 六自由度顺序和映射公式的参考；固定提交与当前 `main` 相同。

这里的“最新”指检查日期当时的最新正式发布版，不表示自动追踪上游开发分支。

## 为什么使用 overlay

本仓库不是三个无关历史的代码快照。安装器检出精确的 Teleopit 和 somehand 源码，安装已发布的 pico-bridge 包，再把集成文件复制到它们正常的上游路径。最终运行目录保持 Teleopit 的结构，而本仓库需要审查的范围只包含 RH56E2 相关增加。

因此 overlay 是“路径兼容的集成层”，不是运行时 monkey patch：安装时 `overlay/teleopit/sim2real/hands/rh56e2.py` 会成为 `$TELEOPIT_DIR/teleopit/sim2real/hands/rh56e2.py`。

## 升级流程

1. 阅读上游更新日志和迁移说明。
2. 每次只升级一个上游，并同步修改 `manifest.json`、`pyproject.toml` 和 `scripts/install.sh`。
3. 把 overlay 应用到干净检出；不要在来源不明的脏上游工作区测试。
4. 运行编译、单测、Ruff、shell 语法和离线模型验证。
5. 运行 PICO 仿真，核对左右、轴向、模式、暂停/恢复和跟踪超时。
6. 连续真机控制前重新完成只读遥测和单自由度分阶段测试。
7. 在 `CHANGELOG.md` 和 PR 中记录已测试版本与未测试的物理条件。

## 必须复查的兼容点

- Teleopit 手部协议、worker 构造、Hydra 配置键、PICO 快照类型和 G1 状态切换。
- somehand 公共 `somehand.api`、YAML schema、关节名、qpos 索引、模型轴向和求解输出。
- pico-bridge wheel/API 版本、帧字段、26 关节顺序、时间戳、重连行为及 APK/wheel 哈希。
- RH56E2 固件 Unit ID、寄存器行为、地址配置、响应帧、关节方向、温度语义和保持命令。

不能只改版本号就声称组合兼容。静态测试和物理验收是两类独立证据。

[架构与数据流](architecture.md) · [第三方组件](../../../THIRD_PARTY.md)

