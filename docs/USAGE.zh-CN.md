# Teleopit + RH56E2 使用手册（中文）

本文从一台干净的 Ubuntu/Linux 主机开始，依次完成 Python 虚拟环境、仿真、RH56E2 只读检查、单手低速测试、G1 站立测试和完整真机联调。命令对应仓库固定的 Teleopit v0.5.0、somehand 0.3.0 和 pico-bridge v0.2.1。

## 1. 范围与安全边界

- 仿真可以在没有机器人时完成；PICO 遥操作需要头显和同一局域网。
- `rh56e2_preflight.py` 与 bench 工具的默认模式只读，不会写 Modbus 寄存器。
- 单手动作必须额外给出 `--write --confirm MOVE_RH56E2`。
- 完整真机入口还要求 `ENABLE_G1_REAL=YES` 和 `ENABLE_RH56E2_WRITES=YES` 两道环境变量确认。
- 代码和静态测试通过不等于物理安全验收。首次动作必须空载、低速、有急停人员，并保证 G1 周围无人。

## 2. 系统与目录

安装完成后主要目录如下：

```text
teleopit-rh56e2-repro/       本仓库：安装、验证和安全入口
$HOME/Teleopit/              固定版本的 Teleopit 与覆盖层
$HOME/Teleopit/.venv/        Python 虚拟环境
$HOME/Teleopit/third_party/somehand/
$HOME/Teleopit/ckpt/track_g1.onnx
```

数据流为：PICO 身体/手部跟踪 → pico-bridge → Teleopit 状态机与策略 → G1；手部跟踪同时经 somehand 重定向 → RH56E2 Modbus TCP。配置中的 120/60/50/200 Hz 是各环节更新频率，不是端到端延迟；实际延迟需要在本机网络和真机上测量。

## 3. 前置条件

- Ubuntu 22.04/24.04 或兼容 Linux，x86_64，Python 3.10 或 3.11。
- `git`、可创建 venv 的 Python、编译工具和网络访问。
- 仿真建议使用带 OpenGL/Vulkan 驱动的独立显卡。
- 真机需要 Unitree G1、左右 RH56E2、PICO 4 Ultra、可用急停、隔离测试区和有线网卡。
- RH56E2 使用稳定的 24 V 电源；手册给出的单手最大抓取电流为 4.5 A。不要从容量未经确认的 G1 接口直接取电。

Ubuntu 基础依赖示例：

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-dev build-essential
```

## 4. 克隆仓库并配置路径

```bash
git clone https://github.com/wz-automind/teleopit-rh56e2-repro.git
cd teleopit-rh56e2-repro
export REPRO_DIR="$PWD"
export TELEOPIT_DIR="$HOME/Teleopit"
export SOMEHAND_DIR="$TELEOPIT_DIR/third_party/somehand"
```

如需其它位置，安装前修改 `TELEOPIT_DIR` 和 `SOMEHAND_DIR`。路径中不要放另一个已有修改但未提交的 Teleopit 工作区，安装器会拒绝覆盖不明修改。

## 5. 创建并使用 Python 虚拟环境

安装器会创建 `$TELEOPIT_DIR/.venv`，不需要手动 `pip install`：

```bash
cd "$REPRO_DIR"
bash scripts/setup/install.sh --profile sim --download-pico-apk
source "$TELEOPIT_DIR/.venv/bin/activate"
python -V
```

若默认 `python3` 不是 3.10/3.11，可显式指定：

```bash
bash scripts/setup/install.sh --profile sim --download-pico-apk --python python3.11
```

安装器会检出固定 commit、复制 overlay、安装可编辑包并下载机器人、GMR、策略和 BVH 资源。不要提交 `.venv`、下载资源、设备凭据或令牌。

## 6. 配置并安装 PICO 应用

APK 下载到 `downloads/PicoBridge_v0.2.1_20260522_release.apk`，脚本会校验 SHA-256。通过开发者模式/ADB 安装 APK，启动后让 PICO 与控制主机处在同一局域网。防火墙需允许 pico-bridge 所用连接；主机 IP变化后要在 PICO 应用中同步更新。

先确认主机能看到 PICO，再进入机器人测试。跟踪丢失、网络频繁抖动或坐标方向异常时不要启用真机输出。

## 7. 离线验证

```bash
cd "$REPRO_DIR"
TELEOPIT_DIR="$TELEOPIT_DIR" bash scripts/dev/validate.sh
"$TELEOPIT_DIR/.venv/bin/python" scripts/dev/check_rh56e2.py \
  --teleopit-dir "$TELEOPIT_DIR" --profile sim
```

必须看到验证通过、固定版本和关键资源存在。此阶段不连接机器人，不会发送 Modbus 写请求。

## 8. 运行仿真

### 8.1 仿真内容与边界

这里运行的是 **MuJoCo sim2sim**，不是 RH56E2 真机控制。场景使用 `teleopit/configs/pico4_sim_rh56e2.yaml`，包含 G1 29 自由度本体和左右 RH56E2 共 12 个手部执行器。PICO 身体数据进入 Teleopit 策略控制 G1，左右手跟踪经 somehand 重定向后只驱动仿真手。此命令不会连接 G1、不会打开 RH56E2 Modbus socket，也不会写真机寄存器。

默认配置需要 PICO 4 Ultra 提供实时身体和手部跟踪。没有 PICO 时仍可执行第 7 节的离线安装、模型加载与 1000 步稳定性验证，但本节的实时遥操作会等待 PICO 数据，不能当作无输入自动演示。默认监听 `0.0.0.0:63901`，等待第一帧的超时时间为 60 秒。

### 8.2 启动前检查

1. 在 PICO 上打开 pico-bridge，填写控制主机在同一局域网中的 IP。
2. 确认主机防火墙允许 UDP/TCP 端口 `63901`（协议以 pico-bridge 当前版本为准），并确保该端口未被其它进程占用。
3. 确认策略文件存在：

```bash
test -f "$TELEOPIT_DIR/ckpt/track_g1.onnx" && echo "policy OK"
```

4. 再次做无硬件写入的完整检查：

```bash
cd "$REPRO_DIR"
TELEOPIT_DIR="$TELEOPIT_DIR" bash scripts/dev/validate.sh
```

### 8.3 启动实时 PICO 仿真

```bash
cd "$TELEOPIT_DIR"
bash "$REPRO_DIR/scripts/run/run_sim_rh56e2.sh" \
  controller.policy_path=ckpt/track_g1.onnx
```

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

配置中的 `policy_hz: 50` 和 `pd_hz: 200` 分别是策略与仿真 PD 更新频率，不代表 PICO 到画面的端到端延迟。

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
cd "$REPRO_DIR"
bash scripts/setup/install.sh --profile real
source "$TELEOPIT_DIR/.venv/bin/activate"
```

不要用另一个 Python 环境运行真机脚本。验证：

```bash
"$TELEOPIT_DIR/.venv/bin/python" scripts/dev/check_rh56e2.py \
  --teleopit-dir "$TELEOPIT_DIR" --profile real
```

## 10. 配置 RH56E2 电源与网络

一次只给一只手上电并配置。很多设备可能具有相同出厂地址 `192.168.11.210`；双手同网段前必须把其中一只改成唯一地址，例如左手 `.210`、右手 `.211`。这是示例，不要未经核对照抄到现有网络。

主机有线网卡设置为同一子网的静态地址，例如 `192.168.11.100/24`，端口默认 `6000`，Unit ID 默认 `0xFF`。先检查：

```bash
ping -c 3 192.168.11.210
ping -c 3 192.168.11.211
```

两只手不能使用相同的 IP/端口组合。接线、极性、保险、接地和电源容量必须由现场人员核对。

## 11. 单手只读预检

先断开 G1，只连接一只空载手：

```bash
cd "$REPRO_DIR"
"$TELEOPIT_DIR/.venv/bin/python" scripts/dev/check_rh56e2.py \
  --teleopit-dir "$TELEOPIT_DIR" --profile sim --hardware \
  --left-host 192.168.11.210
```

确认六路角度可读、故障字节全为 0、温度合理。该命令只读。若固件明确要求其它 Unit ID，再加例如 `--unit-id 1`；不要靠随机尝试写寄存器排障。

## 12. 单手低速工作台测试

确保手固定牢固、无负载、手指行程内无物体。先用默认只读模式：

```bash
"$TELEOPIT_DIR/.venv/bin/python" scripts/dev/bench_rh56e2.py \
  --teleopit-dir "$TELEOPIT_DIR" --host 192.168.11.210 \
  --dof index --delta 50
```

确认读数无误后，现场人员准备断电/急停，再允许一次动作：

```bash
"$TELEOPIT_DIR/.venv/bin/python" scripts/dev/bench_rh56e2.py \
  --teleopit-dir "$TELEOPIT_DIR" --host 192.168.11.210 \
  --dof index --delta 50 --speed 50 \
  --write --confirm MOVE_RH56E2
```

工具只改一个自由度，另外五路写 `-1` 保持，增量限制为 ±100；随后把该自由度目标写回初始反馈值。任一故障字节非零或温度高于阈值都会拒绝动作。依次对另一只手和必要自由度重复，不要第一次就做双手连续跟随。

## 13. 双手只读预检

双手地址确认唯一后再同时接入：

```bash
"$TELEOPIT_DIR/.venv/bin/python" scripts/dev/check_rh56e2.py \
  --teleopit-dir "$TELEOPIT_DIR" --profile real --hardware \
  --left-host 192.168.11.210 --right-host 192.168.11.211
```

任何一侧连接、故障或温度检查失败都应停止，不要进入完整控制。

## 14. G1 dry-run 与站立测试

先确定 G1 使用的有线接口名（如 `eth0`），机器人悬挂或处于厂家规定测试姿态：

```bash
cd "$TELEOPIT_DIR"
.venv/bin/python scripts/run/standalone_standing.py \
  --policy ckpt/track_g1.onnx \
  --network-interface eth0 \
  --dry-run
```

dry-run 正常后，在厂家流程、急停和现场监护到位时去掉 `--dry-run`：

```bash
.venv/bin/python scripts/run/standalone_standing.py \
  --policy ckpt/track_g1.onnx \
  --network-interface eth0
```

只有 G1 能稳定进入和退出站立状态，才继续全链路遥操作。

## 15. 完整 G1 + RH56E2 真机测试

先启动 PICO 应用并确认跟踪稳定。在本仓库执行：

```bash
cd "$REPRO_DIR"
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES \
LEFT_HAND_IP=192.168.11.210 RIGHT_HAND_IP=192.168.11.211 \
NETWORK_INTERFACE=eth0 \
bash scripts/run/run_sim2real_rh56e2.sh
```

入口会再次运行真机预检，缺少任一确认、地址重复或遥测异常时停止。首次运行保持机器人无负载并限制动作范围。

## 16. 状态切换与停止

- `Start`：进入 `STANDING`。
- `Y`：从站立进入 `MOCAP` 遥操作。
- `X`：返回 `STANDING`。
- `B` 或 PICO `A`：暂停/恢复。
- `L1 + R1`：进入 `DAMPING` 紧急停止状态。

先验证暂停和退出，再扩大动作。出现跟踪丢失、异常振动、关节方向错误、网络延迟突增、过温或故障码时立即停止；需要时使用硬件急停/断电，不能只依赖软件按键。

## 17. 运行后检查

停止控制后再次执行第 13 节的双手只读预检，记录角度、故障和温度；检查电源、电缆和机械固定。代码当前采用 `open_on_failure=false`、`open_on_shutdown=false`，异常时不会主动张手；跟踪超时使用 `-1` 保持当前目标。是否安全仍取决于负载和现场风险评估。

## 18. 故障排查

| 现象 | 检查 |
|---|---|
| 缺少模型、策略或配置 | 重跑 `scripts/setup/install.sh`（不要加 `--skip-assets`），再运行 `scripts/dev/validate.sh` |
| `ModuleNotFoundError` | 确认使用 `$TELEOPIT_DIR/.venv/bin/python`，必要时重跑相应 profile 安装 |
| RH56E2 超时 | 检查电源、静态 IP、子网、6000 端口、防火墙和 Unit ID |
| 双手只能连一只 | 分别上电核对地址；消除重复 IP 后再同时接入 |
| 故障字节非零/温度过高 | 停止写入和上电排查，按厂商手册处理，不要软件清故障后强行运行 |
| 收不到 G1 LowState | 检查网卡名、G1 模式、物理链路和 `g1_bridge_sdk` |
| PICO 姿态跳变/丢失 | 检查同网段、无线质量、PICO 应用地址和跟踪环境，保持写入关闭 |

## 19. 命令速查

```bash
# 安装仿真环境
bash scripts/setup/install.sh --profile sim --download-pico-apk
# 离线验证
TELEOPIT_DIR="$HOME/Teleopit" bash scripts/dev/validate.sh
# 安装真机组件
bash scripts/setup/install.sh --profile real
# 单手只读检查
$HOME/Teleopit/.venv/bin/python scripts/dev/check_rh56e2.py --teleopit-dir "$HOME/Teleopit" --profile sim --hardware --left-host 192.168.11.210
# 完整真机入口（仅在分阶段验收全部通过后）
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES LEFT_HAND_IP=192.168.11.210 RIGHT_HAND_IP=192.168.11.211 NETWORK_INTERFACE=eth0 bash scripts/run/run_sim2real_rh56e2.sh
```

协议、寄存器、模型映射和仍待完成的物理验收见 [真机控制检查](真机控制检查.md)。
