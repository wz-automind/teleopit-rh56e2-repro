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

经过审查的上游版本记录在 [`manifest.json`](manifest.json)。先在开发机完成环境、
集成和仿真，再把完整 Teleopit、本集成仓库、pico-bridge wheel 以及备用的
ARM64 Miniforge 安装包通过 SSH/SCP 传到 G1。G1 不在线克隆这些仓库。

## 功能

- PICO 身体与手部跟踪驱动的 G1 + 双 RH56E2 MuJoCo 仿真。
- somehand 左手、右手和双手 RH56E2 配置。
- 使用标准库实现的 Modbus TCP 驱动，支持 FC03 遥测和受保护的 FC16 指令。
- 硬件写入默认关闭，并检查重复端点、故障、过温和跟踪超时。
- 与 Teleopit 一致的 `scripts/setup`、`scripts/run` 和 `scripts/dev` 入口。
- 从离线部署、仿真到分阶段真机测试的中文操作文档。

## 快速部署

完整顺序是“开发机安装与仿真 → 打包 → SCP 传输 → SSH 登录 G1 配置”。仿真
步骤见[完整使用手册第 7 节](docs/zh/usage.md#7-在部署-g1-前运行仿真)。仿真通过后，
在开发机执行：

```bash
set -e
cd ~/teleopit-rh56e2-repro

UNITREE_SDK_DIR="$HOME/Teleopit/third_party/g1_bridge_sdk/thirdparty/unitree_sdk2"
if [ ! -d "$UNITREE_SDK_DIR/.git" ]; then
  mkdir -p "$(dirname "$UNITREE_SDK_DIR")"
  git clone https://github.com/unitreerobotics/unitree_sdk2.git "$UNITREE_SDK_DIR"
fi
git -C "$UNITREE_SDK_DIR" fetch origin c753829882fba461ed07ba25aaabee0a25d83663
git -C "$UNITREE_SDK_DIR" checkout --detach c753829882fba461ed07ba25aaabee0a25d83663

git archive --format=tar.gz --prefix=teleopit-rh56e2-repro/ \
  --output=../teleopit-rh56e2-repro-latest.tar.gz HEAD

cd ~
tar --exclude='*/.git' --exclude='*/__pycache__' \
  --exclude='*.pyc' --exclude='*/.venv' --exclude='*/build' \
  --exclude='*/dist' --exclude='Teleopit/data/datasets' \
  --exclude='Teleopit/outputs' --exclude='Teleopit/recordings' \
  -czf Teleopit-latest.tar.gz Teleopit
curl -fL \
  https://github.com/conda-forge/miniforge/releases/download/26.7.2-0/Miniforge3-26.7.2-0-Linux-aarch64.sh \
  -o Miniforge3-26.7.2-0-Linux-aarch64.sh
curl -fL \
  https://github.com/BotRunner64/pico-bridge/releases/download/v0.2.1/pico_bridge-0.2.1-py3-none-any.whl \
  -o pico_bridge-0.2.1-py3-none-any.whl
echo '89b786c8d2c8b0fda7553914c1314ae4ddaa094503802f279377b19ac4463cb2  Miniforge3-26.7.2-0-Linux-aarch64.sh' | sha256sum --check

scp ~/Teleopit-latest.tar.gz ~/teleopit-rh56e2-repro-latest.tar.gz \
  ~/Miniforge3-26.7.2-0-Linux-aarch64.sh \
  ~/pico_bridge-0.2.1-py3-none-any.whl \
  unitree@192.168.50.62:/home/unitree/
```

`scp` 通过 SSH 通道传输文件。随后用 `ssh unitree@192.168.50.62` 登录 G1。G1
既可能没有 Teleopit，也可能没有 Conda：先按[使用手册第 9 节](docs/zh/usage.md#9-通过-ssh-传输并配置-g1)
检测现有 Conda；检测不到时才安装传入的 ARM64 Miniforge，再创建环境：

```bash
# 先执行手册第 9 节的 Conda 检测/安装代码块，然后：
conda create -n teleopit python=3.11 -y  # 仅在环境不存在时
conda activate teleopit
```

接着解压完整 Teleopit、应用 RH56E2 overlay，并在 G1 的 ARM64 环境中安装 SDK。
不要复制开发机的 Conda 目录；完整检测、备份和安装命令见中文使用手册。

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
互斥入口，不能同时运行。复制真机命令前必须完成[使用手册第 16 节](docs/zh/usage.md#16-完整-g1--rh56e2-真机测试)之前的所有分阶段检查。

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
