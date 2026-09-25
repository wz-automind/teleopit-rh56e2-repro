<h1 align="center">Teleopit RH56E2</h1>

<p align="center">
  使用 PICO 驱动 Unitree G1 和因时 Inspire RH56E2 灵巧手的遥操作集成仓库。
  <br/>
  基于固定版本的 Teleopit、somehand 和 pico-bridge，支持可复现的离线部署。
</p>

<p align="center">
  <a href="docs/zh/README.md">中文文档</a> •
  <a href="docs/zh/usage.md">完整使用手册</a> •
  <a href="THIRD_PARTY.md">第三方项目</a>
</p>

---

## 项目结构

| 基础项目 | 在本仓库中的职责 |
| --- | --- |
| [Teleopit](https://github.com/BotRunner64/Teleopit) | G1 全身重定向、策略推理、仿真、sim2real 状态机和安全运行时 |
| [somehand](https://github.com/BotRunner64/somehand) | 将 PICO 手部关键点重定向到 RH56E2 运动学模型 |
| [pico-bridge](https://github.com/BotRunner64/pico-bridge) | 传输 PICO 头显、控制器、手部和身体跟踪数据 |
| 本仓库 | RH56E2 模型与配置、Modbus TCP 适配器、集成入口和分阶段真机检查 |

```text
PICO 4 Ultra
  └─ pico-bridge 跟踪数据
       ├─ Teleopit 身体重定向 → 策略 → G1
       └─ Teleopit 26→21 手部关键点 → somehand → RH56E2 适配器
                                                      ├─ MuJoCo 仿真
                                                      └─ 受保护的 Modbus TCP 真机控制
```

经过审查的上游版本记录在 [`manifest.json`](manifest.json)。开发机需要同时打包
完整 Teleopit 目录和本集成仓库，再通过 SSH/SCP 传到 G1。G1 先解压得到
`/home/unitree/Teleopit`，然后应用 RH56E2 overlay；G1 不在线克隆这两个仓库。

## 功能

- PICO 身体与手部跟踪驱动的 G1 + 双 RH56E2 MuJoCo 仿真。
- somehand 左手、右手和双手 RH56E2 配置。
- 使用标准库实现的 Modbus TCP 驱动，支持 FC03 遥测和受保护的 FC16 指令。
- 硬件写入默认关闭，并检查重复端点、故障、过温和跟踪超时。
- 与 Teleopit 一致的 `scripts/setup`、`scripts/run` 和 `scripts/dev` 入口。
- 从离线部署、仿真到分阶段真机测试的中文操作文档。

## 快速部署

在开发机制作完整 Teleopit 包和集成仓库包，然后传到 G1：

```bash
git clone https://github.com/wz-automind/teleopit-rh56e2-repro.git
cd teleopit-rh56e2-repro
git archive --format=tar.gz --prefix=teleopit-rh56e2-repro/ \
  --output=../teleopit-rh56e2-repro-latest.tar.gz HEAD

cd ~
tar --exclude='Teleopit/.git' --exclude='*/__pycache__' \
  --exclude='*.pyc' -czf Teleopit-latest.tar.gz Teleopit

scp ~/Teleopit-latest.tar.gz ~/teleopit-rh56e2-repro-latest.tar.gz \
  unitree@192.168.50.62:/home/unitree/
```

首次部署时 G1 没有 Teleopit 源码目录。必须先解压完整 Teleopit，再复制 RH56E2
overlay，并将本仓库 SDK 安装到 G1 已有的 `teleopit` Conda 环境。首次部署和后续
更新的完整命令见[中文使用手册](docs/zh/usage.md)。每次打开 G1 终端先执行：

```bash
source /home/unitree/miniforge3/bin/activate teleopit
```

## 真机入口

当前已验证的机载拓扑为：G1 控制网卡 `eth1`、主机地址
`192.168.123.164`、左右 E2 为 `192.168.123.210/.211:6000`、PICO 可访问地址
为 `192.168.50.62`。先运行只读检查，再使用带双重确认的启动入口：

```bash
cd ~/teleopit-rh56e2-repro
bash scripts/dev/check_unitree_g1_rh56e2.sh
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES \
  bash scripts/run/run_unitree_g1_rh56e2.sh
```

地址和网卡都可以通过环境变量覆盖。无灵巧手的全身遥操与带双 E2 的遥操是两种
互斥入口，不能同时运行。复制真机命令前必须完成[使用手册第 15 节](docs/zh/usage.md#15-完整-g1--rh56e2-真机测试)之前的所有分阶段检查。

## 文档

| 内容 | 文档 |
| --- | --- |
| 文档首页 | [docs/zh/README.md](docs/zh/README.md) |
| 完整安装、仿真和真机操作 | [完整使用手册](docs/zh/usage.md) |
| 组件职责和数据流 | [架构与数据流](docs/zh/reference/architecture.md) |
| RH56E2 模型、寄存器与安全限制 | [RH56E2 参考](docs/zh/reference/rh56e2.md) |
| 独立 Python SDK | [SDK 参考](docs/zh/reference/sdk.md) |
| 上游版本和升级流程 | [上游维护](docs/zh/reference/upstreams.md) |

## 真机安全状态

确定性测试覆盖协议、映射、配置和软件安全门控，但不能替代对具体 G1、两只
RH56E2、电源、网络、固件、负载和急停装置的物理验收。启用写入前必须按使用
手册完成分阶段检查，并在低速、空载、可立即急停的条件下进行首次动作。
