# Teleopit + RH56E2 复现

这个仓库把 [Teleopit](https://github.com/BotRunner64/Teleopit)、[somehand](https://github.com/BotRunner64/somehand) 和 [pico-bridge](https://github.com/BotRunner64/pico-bridge/blob/main/docs/zh/README.md) 固定到可复现版本，并加入 Inspire RH56E2 双手模型、PICO 手部重定向和受保护的 Modbus TCP 真机驱动。

结论先说清楚：**只执行 `git clone` 还不能直接运行**，因为 Teleopit 本体、Python 环境、策略权重和 PICO 应用不在这个仓库里。执行安装脚本后，仿真链路可以按固定版本复现；真机链路还必须完成网络、电气和空载验收，默认不会向手发送任何运动指令。

完整使用文档：[中文使用手册](docs/USAGE.zh-CN.md) | [English Usage Guide](docs/USAGE.en.md)

## 能力边界

| 能力 | 状态 | 说明 |
|---|---|---|
| G1 + RH56E2 MuJoCo 双手仿真 | 已实现 | PICO 身体跟踪驱动 G1，PICO 手跟踪经 somehand 驱动 12 个手部执行器 |
| RH56E2 Modbus TCP 只读预检 | 已实现 | 读取角度、力、电流、故障、状态和温度，不写寄存器 |
| RH56E2 实时控制 | 代码已实现，待真机验收 | 必须显式设置 `write_enabled=true`；故障、过温或跟踪超时会阻止/停止跟随 |
| G1 全身真机控制 | 复用 Teleopit 官方路径，待真机验收 | 使用 `g1_bridge_sdk`、Teleopit 状态机和安全检查 |

## 快速开始：仿真

推荐 Ubuntu/Linux，Python 3.10 或 3.11：

```bash
git clone https://github.com/wz-automind/teleopit-rh56e2-repro.git
cd teleopit-rh56e2-repro
bash scripts/install.sh --profile sim --download-pico-apk
TELEOPIT_DIR="$HOME/Teleopit" bash scripts/validate.sh
```

安装脚本会创建 `$HOME/Teleopit/.venv`、检出固定 commit、安装 pico-bridge 和 somehand，并下载 `track_g1.onnx` 等官方资源。安装 PICO APK、按 pico-bridge 文档配置同一局域网后运行：

```bash
cd "$HOME/Teleopit"
.venv/bin/python scripts/run/run_sim_rh56e2.py \
  controller.policy_path=ckpt/track_g1.onnx
```

这是 MuJoCo 仿真，不会连接或写入 G1/RH56E2 真机。程序默认等待 PICO 身体和双手跟踪数据（端口 `63901`），启动后处于 `STANDING`：按 `Y` 进入全身跟随，`B` 切换仅手臂模式，`A` 暂停/恢复，`X` 返回站立，`Q` 退出。没有 PICO 时可以完成 `validate.sh` 的模型加载和 1000 步稳定性检查，但实时遥操作仿真不会自动生成输入。完整的启动检查、验收标准和排障见[中文使用手册第 8 节](docs/USAGE.zh-CN.md#8-运行仿真)。

## 真机接入

先安装真实 G1 桥接层：

```bash
bash scripts/install.sh --profile real
```

先做只读检查；该命令不会发送 Modbus 写请求：

```bash
$HOME/Teleopit/.venv/bin/python scripts/rh56e2_preflight.py \
  --teleopit-dir "$HOME/Teleopit" --profile real --hardware \
  --left-host 192.168.11.210 --right-host 192.168.11.211
```

只有完成 [真机控制检查](docs/真机控制检查.md) 的分阶段验收后，才可显式启动：

```bash
ENABLE_G1_REAL=YES ENABLE_RH56E2_WRITES=YES \
LEFT_HAND_IP=192.168.11.210 RIGHT_HAND_IP=192.168.11.211 \
NETWORK_INTERFACE=eth0 \
bash scripts/run_real.sh
```

## 关键目录

```text
overlay/teleopit/sim/                 RH56E2 MuJoCo 双手仿真
overlay/teleopit/sim2real/hands/      Modbus TCP 驱动与 Teleopit hand worker 注册
overlay/third_party/somehand/          RH56E2 左右手模型和重定向配置
scripts/install.sh                     固定版本、环境、资源和可选 G1 bridge 安装
scripts/rh56e2_preflight.py            默认只读的环境/真机预检
scripts/rh56e2_bench_test.py           双重确认、单自由度的低速工作台测试
scripts/run_real.sh                    需要双重确认的真机入口
tests/test_rh56e2.py                   协议和映射测试
```

快速安装说明见 [安装与运行](docs/安装与运行.md)，从虚拟环境到真机验收的完整流程见上方中英文手册。版本和资源哈希见 [manifest.json](manifest.json)。

## 重要限制

- 本仓库没有在你的具体 G1、左右 RH56E2、电源和网络上完成物理验收，因此不能仅凭代码审查宣称“已可安全上真机”。
- 两只手出厂默认 IP 都可能是 `192.168.11.210`；同一网段使用时必须先离线修改其中一只，不能把两个设备同时接入同一 IP。
- RH56E2 需要稳定 24 V 供电；手册给出的单手最大抓取电流为 4.5 A。不得从未经确认容量的 G1 接口直接取电。
- 真机默认 `open_on_failure=false`、`open_on_shutdown=false`，避免异常时突然松手；跟踪超时发送 `-1` 保持当前关节目标。

