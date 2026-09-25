# Teleopit + RH56E2 使用手册（中文）

本文从一台干净的 Ubuntu/Linux 主机开始，依次完成 Miniforge 环境、仿真、RH56E2 只读检查、单手低速测试、G1 站立测试和完整真机联调。命令对应仓库固定的 Teleopit v0.5.0、somehand 0.3.0 和 pico-bridge v0.2.1。

## 1. 范围与安全边界

- 仿真可以在没有机器人时完成；PICO 遥操作需要头显和同一局域网。
- `rh56e2_preflight.py` 与 bench 工具的默认模式只读，不会写 Modbus 寄存器。
- 单手动作必须额外给出 `--write --confirm MOVE_RH56E2`。
- 完整真机入口还要求 `ENABLE_G1_REAL=YES` 和 `ENABLE_RH56E2_WRITES=YES` 两道环境变量确认。

## 2. 系统与目录

安装完成后主要目录如下：

```text
teleopit-rh56e2-repro/       本仓库：安装、验证和安全入口
$HOME/Teleopit/              固定版本的 Teleopit 与覆盖层
$HOME/Teleopit/third_party/somehand/
$HOME/Teleopit/ckpt/track_g1.onnx
```

## 3. 前置条件

- Ubuntu 22.04/24.04 或兼容 Linux，x86_64，Python 3.10 或 3.11。
- Miniforge、`git`、Python 编译工具和网络访问。
- 真机需要 Unitree G1、左右 RH56E2、PICO 4 Ultra、可用急停、隔离测试区。
- RH56E2 使用稳定的 24 V 电源；手册给出的单手最大抓取电流为 4.5 A。

Ubuntu 基础依赖示例：

```bash
sudo apt update
sudo apt install -y git python3-dev build-essential
```

## 4. 克隆仓库

```bash
cd ~
git clone https://github.com/wz-automind/teleopit-rh56e2-repro.git
cd teleopit-rh56e2-repro
```

默认流程会把 Teleopit 安装到 `~/Teleopit`，把 somehand 安装到
`~/Teleopit/third_party/somehand`，因此不需要设置路径变量。高级用户如需其它位置，仍可在安装前设置 `TELEOPIT_DIR` 和 `SOMEHAND_DIR`。

## 5. 创建并使用 Miniforge 环境

首次部署时创建 Python 3.11 环境；如果 `teleopit` 已存在，可跳过前两行：

```bash
source /home/unitree/miniforge3/bin/activate
conda create -n teleopit python=3.11 -y
source /home/unitree/miniforge3/bin/activate teleopit

cd ~/teleopit-rh56e2-repro
bash scripts/setup/install.sh --profile sim --download-pico-apk
python -V
```

以后每次打开终端，先运行 `source /home/unitree/miniforge3/bin/activate teleopit`。
安装器会验证环境名、解释器路径和 Python 版本，然后检出固定 commit、复制
overlay、安装可编辑包并下载机器人、GMR、策略和 BVH 资源。

## 6. 配置并安装 PICO 应用

APK 下载到 `downloads/PicoBridge_v0.2.1_20260522_release.apk`，脚本会校验 SHA-256。通过开发者模式/ADB 安装 APK，启动后让 PICO 与控制主机处在同一局域网。防火墙需允许 pico-bridge 所用连接；主机 IP变化后要在 PICO 应用中同步更新。

先确认主机能看到 PICO，再进入机器人测试。跟踪丢失、网络频繁抖动或坐标方向异常时不要启用真机输出。

## 7. 离线验证

```bash
cd ~/teleopit-rh56e2-repro
bash scripts/dev/validate.sh
python scripts/dev/check_rh56e2.py \
  --teleopit-dir ~/Teleopit --profile sim
```

必须看到验证通过、固定版本和关键资源存在。此阶段不连接机器人，不会发送 Modbus 写请求。

## 8. 运行仿真

### 8.1 仿真内容与边界

场景使用 `teleopit/configs/pico4_sim_rh56e2.yaml`，包含 G1 29 自由度本体和左右 RH56E2 共 12 个手部执行器。PICO 身体数据进入 Teleopit 策略控制 G1，左右手跟踪经 somehand 重定向后只驱动仿真手。


### 8.2 启动前检查

1. 在 PICO 上打开 pico-bridge，填写控制主机在同一局域网中的 IP。
2. 确认主机防火墙允许 UDP/TCP 端口 `63901`，并确保该端口未被其它进程占用。
3. 确认策略文件存在：

```bash
test -f ~/Teleopit/ckpt/track_g1.onnx && echo "policy OK"
```

4. 再次做无硬件写入的完整检查：

```bash
cd ~/teleopit-rh56e2-repro
bash scripts/dev/validate.sh
```

### 8.3 启动实时 PICO 仿真

Teleopit 原有的 PICO 仿真命令保持不变：

```bash
cd ~/Teleopit
source /home/unitree/miniforge3/bin/activate teleopit
python scripts/run/run_sim.py \
  --config-name pico4_sim \
  controller.policy_path=ckpt/track_g1.onnx
```

E2 版本只在这个命令基础上换成 RH56E2 入口和配置：

```bash
python scripts/run/run_sim_rh56e2.py \
  --config-name pico4_sim_rh56e2 \
  controller.policy_path=ckpt/track_g1.onnx
```

集成仓库仍保留兼容入口 `scripts/run/run_sim_rh56e2.sh`。

终端应显示 `State: STANDING`、`Input: Pico4 live`、`Viewers: all` 和 `Hands: RH56E2`。收到 PICO 首帧后，按以下顺序操作：

| 键 | 作用 | 验证内容 |
|---|---|---|
| `Y` | 从 `STANDING` 进入全身 `MOCAP` | G1 和双手开始跟随 PICO |
| `B` | 在全身与仅手臂模式之间切换 | 确认模式切换不会造成姿态突跳 |
| `A` | 暂停/恢复跟踪 | 暂停时仿真保持最后目标 |
| `X` | 返回 `STANDING` | 模型回到站立控制状态 |
| `Q` | 正常退出 | 关闭查看器并结束进程 |

`Ctrl+C` 可作为终端退出的备用方式。键盘输入需要终端窗口具有焦点。

### 8.4 仿真验收标准

逐项确认后再考虑真机：

- MuJoCo 窗口能打开，G1 在 `STANDING` 中保持稳定，没有持续下沉、爆炸或高频抖动。
- `Y` 后身体方向与操作者一致；左右手没有互换。
- 两只手各 6 个执行器有响应，拇指旋转和四指屈伸方向正确，关节不穿模或卡在极限。
- `A` 暂停时姿态保持，恢复时没有明显跳变；`X` 能可靠返回 `STANDING`。
- 终端没有持续出现丢帧、超时、NaN、策略维度或模型资源错误。

配置中的 `policy_hz: 50` 和 `pd_hz: 200` 分别是策略与仿真 PD 更新频率。

### 8.5 仿真常见问题

| 现象 | 处理 |
|---|---|
| 一直显示等待 PICO | 检查 PICO 中填写的主机 IP、同一局域网、防火墙和 `63901` 端口；在 60 秒超时前重新启动 PICO 应用 |
| `Y` 后仍不进入 `MOCAP` | PICO 尚未提供有效身体/手部帧；先恢复跟踪，再观察终端是否收到首帧 |
| 窗口打不开 | 检查显卡驱动、OpenGL、`DISPLAY`/Wayland；SSH 环境需要正确的图形转发或本地桌面 |
| 找不到策略或模型 | 回到第 5 节重跑安装（不要使用 `--skip-assets`），然后执行 `scripts/dev/validate.sh` |
| 左右手或关节方向不对 | 停留在仿真，记录具体手和自由度；不要继续第 9 节以后的真机流程 |

## 9. 安装真机组件

回到本仓库，在同一个 Teleopit 目录上增加 G1 bridge：

```bash
cd ~/teleopit-rh56e2-repro
bash scripts/setup/install.sh --profile real
source /home/unitree/miniforge3/bin/activate teleopit
```

验证：

```bash
python scripts/dev/check_rh56e2.py \
  --teleopit-dir ~/Teleopit --profile real
```

## 10. 配置 RH56E2 电源与网络

一次只给一只手上电并配置。很多设备可能具有相同出厂地址 `192.168.11.210`；双手同网段前必须把其中一只改成唯一地址，例如左手 `.210`、右手 `.211`。

主机有线网卡设置为同一子网的静态地址，例如 `192.168.11.100/24`，端口默认 `6000`，Unit ID 默认 `0xFF`。先检查：

```bash
ping -c 3 192.168.11.210
ping -c 3 192.168.11.211
```

两只手不能使用相同的 IP/端口组合。接线、极性、保险、接地和电源容量必须由现场人员核对。

## 11. 单手只读预检

先断开 G1，只连接一只空载手：

```bash
cd ~/teleopit-rh56e2-repro
python scripts/dev/check_rh56e2.py \
  --teleopit-dir ~/Teleopit --profile sim --hardware \
  --left-host 192.168.11.210
```

确认六路角度可读、故障字节全为 0、温度合理。该命令只读。若固件明确要求其它 Unit ID，再加例如 `--unit-id 1`；不要靠随机尝试写寄存器排障。

## 12. 单手低速工作台测试

确保手固定牢固、无负载、手指行程内无物体。先用默认只读模式：

```bash
python scripts/dev/bench_rh56e2.py \
  --teleopit-dir ~/Teleopit --host 192.168.11.210 \
  --dof index --delta 50
```

确认读数无误后，现场人员准备断电/急停，再允许一次动作：

```bash
python scripts/dev/bench_rh56e2.py \
  --teleopit-dir ~/Teleopit --host 192.168.11.210 \
  --dof index --delta 50 --speed 50 \
  --write --confirm MOVE_RH56E2
```

## 13. 双手只读预检

双手地址确认唯一后再同时接入：

```bash
python scripts/dev/check_rh56e2.py \
  --teleopit-dir ~/Teleopit --profile real --hardware \
  --left-host 192.168.11.210 --right-host 192.168.11.211
```

任何一侧连接、故障或温度检查失败都应停止，不要进入完整控制。

## 14. G1 dry-run 与站立测试

确认当前部署的 G1 有线接口为 `eth1`（若主机实际名称不同则替换），机器人悬挂或处于厂家规定测试姿态：

```bash
cd ~/Teleopit
python scripts/run/standalone_standing.py \
  --policy ckpt/track_g1.onnx \
  --network-interface eth1 \
  --dry-run
```

dry-run 正常后，在厂家流程、急停和现场监护到位时去掉 `--dry-run`：

```bash
python scripts/run/standalone_standing.py \
  --policy ckpt/track_g1.onnx \
  --network-interface eth1
```

只有 G1 能稳定进入和退出站立状态，才继续全链路遥操作。

## 15. 完整 G1 + RH56E2 真机测试

`~/Teleopit` 是实际运行目录，已经包含本仓库安装进去的 E2 覆盖层；
`~/teleopit-rh56e2-repro` 是安装、只读检查和受保护启动入口。进入
`Teleopit` 并不表示“没有灵巧手”，是否控制 E2 由
`pico4_sim2real_rh56e2` 配置决定。

### 机载运行（当前已验证部署）

当前部署参数为：Unitree 主机/G1 控制网卡 `eth1`，主机地址
`192.168.123.164`，左、右 E2 分别为 `192.168.123.210:6000` 和
`192.168.123.211:6000`，PICO 可访问的主机 Wi-Fi 地址为
`192.168.50.62`。先运行只读检查，再显式打开两道真机确认：

```bash
source /home/unitree/miniforge3/bin/activate teleopit
cd ~/teleopit-rh56e2-repro
bash scripts/dev/check_unitree_g1_rh56e2.sh

ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES \
  bash scripts/run/run_unitree_g1_rh56e2.sh
```

脚本参数仍可通过同名环境变量覆盖，因此不会把仓库限制为这一套网络。例如改过
手地址时，可在命令前设置 `LEFT_HAND_IP`、`RIGHT_HAND_IP`；改过 PICO 所在
Wi-Fi 时可设置 `PICO_ADVERTISE_IP`。

### 通用直接命令

先启动 PICO 应用并确认跟踪稳定。在 Unitree 主机上激活已有的 `teleopit`
Conda 环境并进入 Teleopit 目录。不带灵巧手的全身遥操仍使用原 Teleopit 命令：

```bash
source /home/unitree/miniforge3/bin/activate teleopit
cd /home/unitree/Teleopit

# 全身遥操启动指令（不包含灵巧手）
python scripts/run/run_sim2real.py \
  --config-name pico4_sim2real \
  controller.policy_path=ckpt/track_g1.onnx \
  input.bridge_advertise_ip=192.168.50.62 \
  real_robot.network_interface=eth1
```

需要控制左右 E2 时，仍使用同一个 Teleopit 入口，只更换 E2 配置并追加双手连接参数：

```bash
source /home/unitree/miniforge3/bin/activate teleopit
cd /home/unitree/Teleopit

# 全身遥操启动指令（包含左右 E2）
python scripts/run/run_sim2real.py \
  --config-name pico4_sim2real_rh56e2 \
  controller.policy_path=ckpt/track_g1.onnx \
  input.bridge_advertise_ip=192.168.50.62 \
  real_robot.network_interface=eth1 \
  hands.rh56e2.left_host=192.168.11.210 \
  hands.rh56e2.right_host=192.168.11.211 \
  hands.rh56e2.port=6000 \
  hands.rh56e2.write_enabled=true
```

这两条命令是二选一，不能同时运行。需要控制 E2 时，先停止不包含灵巧手的
进程，再启动包含 E2 的命令。E2 命令会向实体灵巧手写入目标，因此必须先通过
第 11-14 节检查，并保持机器人无负载、限制动作范围、硬件急停随时可用。

本仓库还保留了可选的受保护启动器；它会再次执行真机预检，然后启动同一套
E2 配置：

```bash
cd ~/teleopit-rh56e2-repro
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES \
LEFT_HAND_IP=192.168.11.210 RIGHT_HAND_IP=192.168.11.211 \
NETWORK_INTERFACE=eth1 \
bash scripts/run/run_sim2real_rh56e2.sh \
  input.bridge_advertise_ip=192.168.50.62
```

入口会再次运行真机预检，缺少任一确认、地址重复或遥测异常时停止。首次运行保持机器人无负载并限制动作范围。

### 外部主机运行

外部主机必须有一块能直达机器人交换网络的有线网卡（例如 `enp4s0`），并为它
配置一个不冲突的 `192.168.123.x/24` 地址；Wi-Fi 只能用于 SSH 或 PICO 数据，
不能代替 G1/E2 的机器人侧有线链路。确认外部主机可以访问
`192.168.123.164`、`192.168.123.210:6000` 和
`192.168.123.211:6000` 后，按实际地址覆盖通用入口：

```bash
cd ~/teleopit-rh56e2-repro
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES \
NETWORK_INTERFACE=enp4s0 \
G1_HOST_IP=192.168.123.164 \
LEFT_HAND_IP=192.168.123.210 RIGHT_HAND_IP=192.168.123.211 \
PICO_ADVERTISE_IP=<外部主机的-Wi-Fi-IP> \
bash scripts/run/run_unitree_g1_rh56e2.sh
```

`g1_host_cli`、`run_sim2real.py`、机载启动器和外部主机启动器都会争用同一套
G1 控制通道；同一时间只能有一个控制进程。SSH 只是远程打开终端，不会改变
控制数据使用哪块网卡。

## 16. 状态切换与停止

- `Start`：进入 `STANDING`。
- `Y`：从站立进入 `MOCAP` 遥操作。
- `X`：返回 `STANDING`。
- `Q`：正常退出进程。
- `B` 或 PICO `A`：暂停/恢复。
- `L1 + R1`：进入 `DAMPING` 紧急停止状态。

先验证暂停和退出，再扩大动作。出现跟踪丢失、异常振动、关节方向错误、网络延迟突增、过温或故障码时立即停止；需要时使用硬件急停/断电，不能只依赖软件按键。

`Ctrl+C` 只是在当前终端发送中断；终端没有焦点、程序使用原始键盘输入或进程
不在前台时可能看起来没有反应。先按 `X` 返回站立，再按 `Q`。仍无法退出时，
在另一个 SSH 终端中先查看进程，再依次发送中断和终止信号：

```bash
pgrep -af 'g1_host_cli|run_sim2real|run_real|standalone_standing'
pkill -INT -f 'scripts/run/run_sim2real.py'
# 确认仍未退出后再使用：
pkill -TERM -f 'scripts/run/run_sim2real.py'
```

处理软件进程前后都要确保硬件急停可用；异常运动时先用硬件急停，不要等待终端响应。

## 17. 运行后检查

停止控制后再次执行第 13 节的双手只读预检，记录角度、故障和温度；检查电源、电缆和机械固定。代码当前采用 `open_on_failure=false`、`open_on_shutdown=false`，异常时不会主动张手；跟踪超时使用 `-1` 保持当前目标。是否安全仍取决于负载和现场风险评估。

## 18. 故障排查

| 现象 | 检查 |
|---|---|
| 缺少模型、策略或配置 | 重跑 `scripts/setup/install.sh`（不要加 `--skip-assets`），再运行 `scripts/dev/validate.sh` |
| `ModuleNotFoundError` | 确认 `CONDA_DEFAULT_ENV=teleopit` 且 `which python` 指向 Miniforge 环境，必要时重跑相应 profile 安装 |
| RH56E2 超时 | 检查电源、静态 IP、子网、6000 端口、防火墙和 Unit ID |
| 按 `.11.210/.11.211` 超时 | `.11.x` 只是通用示例；当前已验证部署使用 `.123.210/.123.211`，先运行 `check_unitree_g1_rh56e2.sh` |
| 双手只能连一只 | 分别上电核对地址；消除重复 IP 后再同时接入 |
| 故障字节非零/温度过高 | 停止写入和上电排查，按厂商手册处理，不要软件清故障后强行运行 |
| 收不到 G1 LowState | 检查网卡名、G1 模式、物理链路和 `g1_bridge_sdk` |
| PICO 姿态跳变/丢失 | 检查同网段、无线质量、PICO 应用地址和跟踪环境，保持写入关闭 |
| `Ctrl+C` 没反应 | 先硬件止动并按 `X`、`Q`；再从第二个终端用 `pgrep` 确认目标后发送 `INT`/`TERM` |

## 19. 命令速查

```bash
# 安装仿真环境
bash scripts/setup/install.sh --profile sim --download-pico-apk
# 离线验证
bash scripts/dev/validate.sh
# 安装真机组件
bash scripts/setup/install.sh --profile real
# 单手只读检查
python scripts/dev/check_rh56e2.py --teleopit-dir "$HOME/Teleopit" --profile sim --hardware --left-host 192.168.11.210
# 完整真机入口（仅在分阶段验收全部通过后）
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES LEFT_HAND_IP=192.168.11.210 RIGHT_HAND_IP=192.168.11.211 NETWORK_INTERFACE=eth1 bash scripts/run/run_sim2real_rh56e2.sh
# 当前 Unitree 机载部署：只读检查 / 受保护启动
bash scripts/dev/check_unitree_g1_rh56e2.sh
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES bash scripts/run/run_unitree_g1_rh56e2.sh
```

协议、寄存器、模型映射和仍待完成的物理验收见 [真机控制检查](hardware-check.md)。
