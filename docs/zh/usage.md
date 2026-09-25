# Teleopit + RH56E2 使用手册（中文）

本文按已经验证的“开发机准备并仿真、通过 SSH 通道传输、G1 本机创建环境和编译”
流程操作。开发机准备完整 Teleopit、RH56E2 集成仓库及安装文件；G1 不在线克隆
这些 Git 仓库。

## 1. 范围与安全边界

- 仿真可以在没有机器人时完成；PICO 遥操作需要头显和同一局域网。
- `rh56e2_preflight.py` 与 bench 工具的默认模式只读，不会写 Modbus 寄存器。
- 单手动作必须额外给出 `--write --confirm MOVE_RH56E2`。
- 完整真机入口还要求 `ENABLE_G1_REAL=YES` 和 `ENABLE_RH56E2_WRITES=YES` 两道环境变量确认。

## 2. 系统与目录

开发机和 G1 都使用两个独立目录，不把集成仓库误当成 Teleopit 本体：

```text
~/teleopit-rh56e2-repro/  集成仓库：E2 overlay、SDK、验证和安全入口
~/Teleopit/               完整 Teleopit：仿真与真机的实际运行目录
~/Teleopit/third_party/somehand/
~/Teleopit/ckpt/track_g1.onnx
```

## 3. 前置条件

- 开发机需要 Conda、`git`、`tar`、`curl`、`scp` 和 GitHub 网络访问。
- `teleopit` Conda 环境使用 Python 3.10 或 3.11；开发机与 G1 各自创建，不能跨 CPU 架构复制。
- G1 必须能通过 SSH 登录；示例 Wi-Fi/SSH 地址为 `192.168.50.62`。
- 真机需要 Unitree G1、左右 RH56E2、PICO 4 Ultra、可用急停、隔离测试区和机器人侧有线网卡。
- RH56E2 使用稳定的 24 V 电源；手册给出的单手最大抓取电流为 4.5 A。

开发机缺少基础工具时可安装：

```bash
sudo apt update
sudo apt install -y git openssh-client tar curl
```

## 4. 在开发机安装并集成

先在开发机创建环境，再克隆集成仓库。安装脚本会在开发机下载固定版本的
Teleopit、somehand、模型和策略，并合入 E2 修改；不要在 G1 上运行这个在线安装流程。

```bash
conda create -n teleopit python=3.11 -y
conda activate teleopit

cd ~
git clone https://github.com/wz-automind/teleopit-rh56e2-repro.git
cd teleopit-rh56e2-repro
TELEOPIT_DIR="$HOME/Teleopit" \
  bash scripts/setup/install.sh --profile sim --asset-source modelscope
```

如果 `~/Teleopit` 已经存在，先确认它是不是需要保留的工作目录。安装脚本不会把
非空的陌生目录当成全新安装覆盖；可继续使用已经完成集成的目录，或先手工备份后再安装。

## 5. 配置 PICO 应用

在 PICO 上安装并打开 pico-bridge，让 PICO 与开发机处在同一局域网，并把
控制主机地址设置为开发机在该局域网中的 IP。防火墙需允许 pico-bridge 使用的
端口 `63901`；主机地址变化后要在 PICO 应用中同步更新。

## 6. 开发机无硬件验证

```bash
conda activate teleopit
cd ~/teleopit-rh56e2-repro
bash scripts/dev/validate.sh
python scripts/dev/check_rh56e2.py \
  --teleopit-dir ~/Teleopit --profile sim
```

必须看到固定版本和关键资源验证通过。此阶段不连接机器人，不发送 Modbus 写请求。

## 7. 在部署 G1 前运行仿真

### 7.1 仿真内容与边界

场景使用 `teleopit/configs/pico4_sim_rh56e2.yaml`，包含 G1 29 自由度本体和
左右 RH56E2 共 12 个手部执行器。PICO 身体数据进入 Teleopit 策略控制 G1，
左右手跟踪经 somehand 重定向后只驱动仿真手。

### 7.2 启动前检查

1. 在 PICO 上打开 pico-bridge，填写开发机在同一局域网中的 IP。
2. 确认开发机防火墙允许端口 `63901`，并确保该端口未被其他进程占用。
3. 确认策略文件存在并再次验证：

```bash
conda activate teleopit
test -f ~/Teleopit/ckpt/track_g1.onnx && echo "policy OK"
cd ~/teleopit-rh56e2-repro
bash scripts/dev/validate.sh
```

### 7.3 启动实时 PICO 仿真

Teleopit 原有的 PICO 仿真命令为：

```bash
conda activate teleopit
cd ~/Teleopit
python scripts/run/run_sim.py \
  --config-name pico4_sim \
  controller.policy_path=ckpt/track_g1.onnx
```

E2 版本只更换入口和配置：

```bash
python scripts/run/run_sim_rh56e2.py \
  --config-name pico4_sim_rh56e2 \
  controller.policy_path=ckpt/track_g1.onnx
```

集成仓库仍保留兼容入口 `scripts/run/run_sim_rh56e2.sh`。

终端应显示 `State: STANDING`、`Input: Pico4 live`、`Viewers: all` 和
`Hands: RH56E2`。收到 PICO 首帧后按以下顺序操作：

| 键 | 作用 | 验证内容 |
|---|---|---|
| `Y` | 从 `STANDING` 进入全身 `MOCAP` | G1 和双手开始跟随 PICO |
| `B` | 在全身与仅手臂模式之间切换 | 确认模式切换不会造成姿态突跳 |
| `A` | 暂停/恢复跟踪 | 暂停时仿真保持最后目标 |
| `X` | 返回 `STANDING` | 模型回到站立控制状态 |
| `Q` | 正常退出 | 关闭查看器并结束进程 |

`Ctrl+C` 可作为终端退出的备用方式。键盘输入需要终端窗口具有焦点。

### 7.4 仿真验收标准

逐项确认后才能准备真机部署：

- MuJoCo 窗口能打开，G1 在 `STANDING` 中保持稳定，没有持续下沉、爆炸或高频抖动。
- `Y` 后身体方向与操作者一致；左右手没有互换。
- 两只手各 6 个执行器有响应，拇指旋转和四指屈伸方向正确，关节不穿模或卡在极限。
- `A` 暂停时姿态保持，恢复时没有明显跳变；`X` 能可靠返回 `STANDING`。
- 终端没有持续出现丢帧、超时、NaN、策略维度或模型资源错误。

配置中的 `policy_hz: 50` 和 `pd_hz: 200` 分别是策略与仿真 PD 更新频率。

### 7.5 仿真常见问题

| 现象 | 处理 |
|---|---|
| 一直显示等待 PICO | 检查 PICO 中填写的开发机 IP、同一局域网、防火墙和 `63901` 端口 |
| `Y` 后仍不进入 `MOCAP` | PICO 尚未提供有效身体/手部帧；先恢复跟踪，再观察终端是否收到首帧 |
| 窗口打不开 | 检查显卡驱动、OpenGL、`DISPLAY`/Wayland；SSH 环境需要正确的图形转发或本地桌面 |
| 找不到策略或模型 | 回到第 4 节重新检查开发机安装和资源下载，不要继续真机部署 |
| 左右手或关节方向不对 | 停留在仿真，记录具体手和自由度；不要继续后面的真机流程 |

## 8. 在开发机打包 G1 所需文件

仿真通过后，先在开发机补齐固定版本的 `unitree_sdk2` 源码，再制作 Teleopit 和
集成仓库压缩包。Teleopit 包包含已经合入的 E2 overlay、somehand、模型、策略
以及 G1 bridge 源码。
Teleopit 源码压缩包不包含 Conda 环境。

```bash
set -e
UNITREE_SDK_DIR="$HOME/Teleopit/third_party/g1_bridge_sdk/thirdparty/unitree_sdk2"
if [ ! -d "$UNITREE_SDK_DIR/.git" ]; then
  mkdir -p "$(dirname "$UNITREE_SDK_DIR")"
  git clone https://github.com/unitreerobotics/unitree_sdk2.git "$UNITREE_SDK_DIR"
fi
git -C "$UNITREE_SDK_DIR" fetch origin c753829882fba461ed07ba25aaabee0a25d83663
git -C "$UNITREE_SDK_DIR" checkout --detach c753829882fba461ed07ba25aaabee0a25d83663

cd ~/teleopit-rh56e2-repro
git archive --format=tar.gz \
  --prefix=teleopit-rh56e2-repro/ \
  --output=../teleopit-rh56e2-repro-latest.tar.gz \
  HEAD

cd ~
tar --exclude='*/.git' \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  --exclude='*/.venv' \
  --exclude='*/build' \
  --exclude='*/dist' \
  --exclude='Teleopit/data/datasets' \
  --exclude='Teleopit/outputs' \
  --exclude='Teleopit/recordings' \
  -czf Teleopit-latest.tar.gz Teleopit

curl -fL \
  https://github.com/conda-forge/miniforge/releases/download/26.7.2-0/Miniforge3-26.7.2-0-Linux-aarch64.sh \
  -o Miniforge3-26.7.2-0-Linux-aarch64.sh
curl -fL \
  https://github.com/BotRunner64/pico-bridge/releases/download/v0.2.1/pico_bridge-0.2.1-py3-none-any.whl \
  -o pico_bridge-0.2.1-py3-none-any.whl
echo '89b786c8d2c8b0fda7553914c1314ae4ddaa094503802f279377b19ac4463cb2  Miniforge3-26.7.2-0-Linux-aarch64.sh' | sha256sum --check
echo '7cf0fee07c76541fd06e2ee6bdeec3d11fec578cd4ef6b45179dec4af31b369f  pico_bridge-0.2.1-py3-none-any.whl' | sha256sum --check
```

Miniforge 安装包必须是 `Linux-aarch64`，因为 G1 是 ARM64。不要把开发机的 Conda
目录直接打包复制到 G1。

## 9. 通过 SSH 传输并配置 G1

`scp` 使用的就是 SSH 传输通道。下面四项从开发机一次传到 G1；如果 G1 已有可用
Conda，Miniforge 安装包只作为备用，不会重复安装。

```bash
set -e
scp ~/Teleopit-latest.tar.gz \
  ~/teleopit-rh56e2-repro-latest.tar.gz \
  ~/Miniforge3-26.7.2-0-Linux-aarch64.sh \
  ~/pico_bridge-0.2.1-py3-none-any.whl \
  unitree@192.168.50.62:/home/unitree/

ssh unitree@192.168.50.62
```

以下命令在 SSH 登录后的 G1 终端执行。先寻找常见位置中的 Conda；确实没有时，
才使用刚传入的 ARM64 Miniforge 安装包。随后创建 G1 自己的 `teleopit` 环境：

```bash
set -e
if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
else
  for conda_root in "$HOME/miniforge3" "$HOME/miniconda3" "$HOME/anaconda3"; do
    if [ -x "$conda_root/bin/conda" ]; then
      eval "$("$conda_root/bin/conda" shell.bash hook)"
      break
    fi
  done
fi

if ! command -v conda >/dev/null 2>&1; then
  if [ "$(uname -m)" != "aarch64" ]; then
    echo "错误：G1 应为 aarch64，当前为 $(uname -m)" >&2
    exit 1
  fi
  cd "$HOME"
  echo '89b786c8d2c8b0fda7553914c1314ae4ddaa094503802f279377b19ac4463cb2  Miniforge3-26.7.2-0-Linux-aarch64.sh' | sha256sum --check
  bash "$HOME/Miniforge3-26.7.2-0-Linux-aarch64.sh" -b -p "$HOME/miniforge3"
  eval "$("$HOME/miniforge3/bin/conda" shell.bash hook)"
fi

if ! conda env list | awk '{print $1}' | grep -qx teleopit; then
  conda create -n teleopit python=3.11 -y
fi
conda activate teleopit
python --version
```

首次创建环境和安装 Python 依赖仍需要 G1 能访问配置好的 Conda/PyPI镜像；Teleopit、somehand 和 E2 集成源码本身不需要在 G1 上从 GitHub 克隆。

G1 初始没有 Teleopit 时，必须先恢复完整目录，再复制 E2 overlay。下面的命令也
适用于重新部署：备份旧目录、解压并安装；备份只改名，不直接删除。

```bash
set -e
cd /home/unitree
stamp="$(date +%Y%m%d-%H%M%S)"
if [ -d teleopit-rh56e2-repro ]; then
  mv teleopit-rh56e2-repro "teleopit-rh56e2-repro-backup-$stamp"
fi
if [ -d Teleopit ]; then
  mv Teleopit "Teleopit-backup-$stamp"
fi
tar -xzf Teleopit-latest.tar.gz -C /home/unitree
tar -xzf teleopit-rh56e2-repro-latest.tar.gz -C /home/unitree
test -d /home/unitree/Teleopit/teleopit
test -f /home/unitree/Teleopit/third_party/g1_bridge_sdk/thirdparty/unitree_sdk2/CMakeLists.txt

cd /home/unitree/teleopit-rh56e2-repro
cp -a overlay/teleopit/. /home/unitree/Teleopit/teleopit/
cp -a overlay/scripts/. /home/unitree/Teleopit/scripts/
cp -a overlay/assets/. /home/unitree/Teleopit/assets/
mkdir -p /home/unitree/Teleopit/third_party/somehand
cp -a overlay/third_party/somehand/. \
  /home/unitree/Teleopit/third_party/somehand/

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e "/home/unitree/Teleopit[sim2real]"
python -m pip install /home/unitree/pico_bridge-0.2.1-py3-none-any.whl
python -m pip install -e /home/unitree/Teleopit/third_party/somehand
python -m pip install --no-build-isolation -e . --no-deps
cd /home/unitree/Teleopit
bash scripts/setup/setup_g1_bridge.sh
```

以后每次 SSH 登录 G1 后先让 Conda 命令进入当前 shell，再激活环境：

```bash
if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
else
  for conda_root in "$HOME/miniforge3" "$HOME/miniconda3" "$HOME/anaconda3"; do
    if [ -x "$conda_root/bin/conda" ]; then
      eval "$("$conda_root/bin/conda" shell.bash hook)"
      break
    fi
  done
fi
command -v conda >/dev/null 2>&1 || { echo "找不到 Conda" >&2; exit 1; }
conda activate teleopit
```

后续只更新 E2 集成时，可以只重新传输集成仓库包并重复 overlay 复制与 SDK 安装，
不要用旧 Teleopit 包覆盖已经验证可用的目录。

## 10. 确认传入的真机组件

确认第 9 节创建的 G1 Conda 环境、传入的 Teleopit 目录和本仓库 SDK 都可用：

```bash
conda activate teleopit
cd /home/unitree/teleopit-rh56e2-repro
python -c 'import g1_bridge_sdk, teleopit; from teleopit_rh56e2.sdk import RH56E2Hand; print("runtime imports OK")'
python scripts/dev/check_rh56e2.py \
  --teleopit-dir /home/unitree/Teleopit --profile real
```

缺少 `g1_bridge_sdk` 表示第 9 节的本地编译没有完成，或传入的 Teleopit 包不完整；
应检查包内的 `third_party/g1_bridge_sdk/thirdparty/unitree_sdk2` 后重新执行安装，
而不是在机器人上克隆 Teleopit。

## 11. 配置 RH56E2 电源与网络

### 当时如何确定 E2 的地址和端口

端口 `6000` 不是根据 G1 地址猜出来的，也不是随机试出的。我们先确认 G1 侧
网卡和子网，再从邻居表核对已上电的手；RH56E2 的 Modbus TCP 协议配置给出
TCP 端口 `6000`，随后用 TCP 连接测试和只读 Modbus FC03 请求确认端点确实是
E2 控制器：

```bash
ip -4 address show eth1
ip route
ip neigh show dev eth1

nc -vz -w 2 192.168.123.210 6000
nc -vz -w 2 192.168.123.211 6000

cd /home/unitree/teleopit-rh56e2-repro
bash scripts/dev/check_unitree_g1_rh56e2.sh
```

当时确认 `eth1` 为 `192.168.123.164/24`，左右 E2 分别为
`192.168.123.210` 和 `192.168.123.211`，两者的 TCP `6000` 都可连接。
仅仅看到端口开放还不能证明设备就是 E2；最后一条命令会用只读 Modbus FC03
读取六路遥测，必须返回合理数据且没有故障。不要通过随机写寄存器识别设备。
如果系统没有 `nc`，可直接执行只读检查脚本。

### 通用地址配置

一次只给一只手上电并配置。很多设备可能具有相同出厂地址 `192.168.11.210`；双手同网段前必须把其中一只改成唯一地址，例如左手 `.210`、右手 `.211`。

主机有线网卡设置为同一子网的静态地址，例如 `192.168.11.100/24`，端口默认 `6000`，Unit ID 默认 `0xFF`。先检查：

```bash
ping -c 3 192.168.11.210
ping -c 3 192.168.11.211
```

两只手不能使用相同的 IP/端口组合。接线、极性、保险、接地和电源容量必须由现场人员核对。

## 12. 单手只读预检

先断开 G1，只连接一只空载手：

```bash
cd ~/teleopit-rh56e2-repro
python scripts/dev/check_rh56e2.py \
  --teleopit-dir ~/Teleopit --profile sim --hardware \
  --left-host 192.168.11.210
```

确认六路角度可读、故障字节全为 0、温度合理。该命令只读。若固件明确要求其它 Unit ID，再加例如 `--unit-id 1`；不要靠随机尝试写寄存器排障。

## 13. 单手低速工作台测试

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

## 14. 双手只读预检

双手地址确认唯一后再同时接入：

```bash
python scripts/dev/check_rh56e2.py \
  --teleopit-dir ~/Teleopit --profile real --hardware \
  --left-host 192.168.11.210 --right-host 192.168.11.211
```

任何一侧连接、故障或温度检查失败都应停止，不要进入完整控制。

## 15. G1 dry-run 与站立测试

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

## 16. 完整 G1 + RH56E2 真机测试

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
conda activate teleopit
cd ~/teleopit-rh56e2-repro
bash scripts/dev/check_unitree_g1_rh56e2.sh

ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES \
  bash scripts/run/run_unitree_g1_rh56e2.sh
```

脚本参数仍可通过同名环境变量覆盖，因此不会把仓库限制为这一套网络。例如改过
手地址时，可在命令前设置 `LEFT_HAND_IP`、`RIGHT_HAND_IP`；改过 PICO 所在
Wi-Fi 时可设置 `PICO_ADVERTISE_IP`。

### 通用直接命令

先启动 PICO 应用并确认跟踪稳定。在 Unitree 主机上激活第 9 节创建的 `teleopit`
Conda 环境并进入 Teleopit 目录。不带灵巧手的全身遥操仍使用原 Teleopit 命令：

```bash
conda activate teleopit
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
conda activate teleopit
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
第 12-15 节检查，并保持机器人无负载、限制动作范围、硬件急停随时可用。

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

## 17. 状态切换与停止

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

## 18. 运行后检查

停止控制后再次执行第 14 节的双手只读预检，记录角度、故障和温度；检查电源、电缆和机械固定。代码当前采用 `open_on_failure=false`、`open_on_shutdown=false`，异常时不会主动张手；跟踪超时使用 `-1` 保持当前目标。是否安全仍取决于负载和现场风险评估。

## 19. 故障排查

| 现象 | 检查 |
|---|---|
| 缺少模型、策略或配置 | 检查 `/home/unitree/Teleopit` 是否为完整离线包；必要时从开发机重新传输 `Teleopit-latest.tar.gz`，再重新合入 overlay |
| `ModuleNotFoundError` | 确认 `CONDA_DEFAULT_ENV=teleopit`，且 `which python` 位于当前 Conda 环境；SDK 缺失时按第 9 节重新安装并构建 G1 bridge |
| RH56E2 超时 | 检查电源、静态 IP、子网、6000 端口、防火墙和 Unit ID |
| 按 `.11.210/.11.211` 超时 | `.11.x` 只是通用示例；当前已验证部署使用 `.123.210/.123.211`，先运行 `check_unitree_g1_rh56e2.sh` |
| 双手只能连一只 | 分别上电核对地址；消除重复 IP 后再同时接入 |
| 故障字节非零/温度过高 | 停止写入和上电排查，按厂商手册处理，不要软件清故障后强行运行 |
| 收不到 G1 LowState | 检查网卡名、G1 模式、物理链路和 `g1_bridge_sdk` |
| PICO 姿态跳变/丢失 | 检查同网段、无线质量、PICO 应用地址和跟踪环境，保持写入关闭 |
| `Ctrl+C` 没反应 | 先硬件止动并按 `X`、`Q`；再从第二个终端用 `pgrep` 确认目标后发送 `INT`/`TERM` |

## 20. 命令速查

```bash
# 开发机：仿真通过后制作传输文件（完整步骤见第 8 节）
set -e
cd ~
tar --exclude='*/.git' --exclude='*/__pycache__' --exclude='*.pyc' --exclude='*/.venv' --exclude='*/build' --exclude='*/dist' --exclude='Teleopit/data/datasets' --exclude='Teleopit/outputs' --exclude='Teleopit/recordings' -czf Teleopit-latest.tar.gz Teleopit
cd ~/teleopit-rh56e2-repro
git archive --format=tar.gz --prefix=teleopit-rh56e2-repro/ --output=../teleopit-rh56e2-repro-latest.tar.gz HEAD
curl -fL https://github.com/conda-forge/miniforge/releases/download/26.7.2-0/Miniforge3-26.7.2-0-Linux-aarch64.sh -o ~/Miniforge3-26.7.2-0-Linux-aarch64.sh
curl -fL https://github.com/BotRunner64/pico-bridge/releases/download/v0.2.1/pico_bridge-0.2.1-py3-none-any.whl -o ~/pico_bridge-0.2.1-py3-none-any.whl
scp ~/Teleopit-latest.tar.gz ~/teleopit-rh56e2-repro-latest.tar.gz ~/Miniforge3-26.7.2-0-Linux-aarch64.sh ~/pico_bridge-0.2.1-py3-none-any.whl unitree@192.168.50.62:/home/unitree/
# SSH 登录 G1；检测/安装 Conda、创建环境的完整命令见第 9 节
ssh unitree@192.168.50.62
conda create -n teleopit python=3.11 -y  # 仅在环境不存在时
conda activate teleopit
# G1 首次部署：先解压完整 Teleopit，再应用集成 overlay
tar -xzf /home/unitree/Teleopit-latest.tar.gz -C /home/unitree
tar -xzf /home/unitree/teleopit-rh56e2-repro-latest.tar.gz -C /home/unitree
# 离线验证
bash scripts/dev/validate.sh
# 单手只读检查
python scripts/dev/check_rh56e2.py --teleopit-dir "$HOME/Teleopit" --profile sim --hardware --left-host 192.168.11.210
# 完整真机入口（仅在分阶段验收全部通过后）
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES LEFT_HAND_IP=192.168.11.210 RIGHT_HAND_IP=192.168.11.211 NETWORK_INTERFACE=eth1 bash scripts/run/run_sim2real_rh56e2.sh
# 当前 Unitree 机载部署：只读检查 / 受保护启动
bash scripts/dev/check_unitree_g1_rh56e2.sh
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES bash scripts/run/run_unitree_g1_rh56e2.sh
```

协议、寄存器、模型映射和安全限制见 [RH56E2 参考](reference/rh56e2.md)。
