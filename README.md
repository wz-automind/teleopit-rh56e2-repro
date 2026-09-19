# Teleopit + RH56E2 双手仿真复现项目

这个仓库保存一套可复现的实验覆盖层，用于在 Teleopit 的 Unitree G1 MuJoCo 仿真中加入左右两只 Inspire RH56E2 手。

控制链路：

```text
PICO 4 身体跟踪  -> Teleopit -> G1 29DoF policy
PICO 4 双手跟踪  -> somehand -> RH56E2 左右手 actuator
```

原版 Teleopit 入口不会被修改。安装脚本只向上游工作树增加 RH56E2 专用文件，因此可以同时运行原版和本项目版本。

## 固定版本

- Teleopit：`BotRunner64/Teleopit`，commit `f926386`
- somehand：`BotRunner64/somehand`，commit `f0a6b42e151ca10a6eec3e24c24c10cd13c40314`
- 本项目基于 Teleopit 官方仓库、项目文档和本地 RH56E2 改动整理而成。

上游项目：[Teleopit](https://github.com/BotRunner64/Teleopit)

## 安装

```bash
cd ~/teleopit-rh56e2-repro
TELEOPIT_DIR=~/Teleopit \
SOMEHAND_DIR=~/Teleopit/third_party/somehand \
bash scripts/install.sh
```

如果两个上游目录不存在，脚本会从 GitHub 克隆并切换到固定 commit。安装不会覆盖原版 `run_sim.py`、`mujoco_robot.py`、`session.py` 或 `pico4_sim.yaml`。

## 验证

```bash
cd ~/teleopit-rh56e2-repro
TELEOPIT_DIR=~/Teleopit \
SOMEHAND_DIR=~/Teleopit/third_party/somehand \
bash scripts/validate.sh
```

验证包括：RH56E2 配置加载、合并模型的 `nq/nv/nu`、41 个 actuator、首步无手部碰撞，以及 1000 步无 MuJoCo 数值警告。

## 运行双手仿真

```bash
cd ~/Teleopit
PYTHONPATH=third_party/somehand/src:$PYTHONPATH \
python scripts/run/run_sim_rh56e2.py \
  controller.policy_path=ckpt/track_g1.onnx
```

原版仍使用原命令：

```bash
python scripts/run/run_sim.py \
  --config-name pico4_sim \
  controller.policy_path=ckpt/track_g1.onnx
```

## 目录说明

`overlay/` 是复制到 Teleopit 和 somehand 工作树中的新增文件；`scripts/merge_g1_rh56e2.py` 的碰撞和阻尼修复已经反映在随附的合并 XML 中。RH56E2 手部碰撞被关闭，仅保留可视化和关节控制，避免手部碰撞体与 G1 原橡胶手发生重叠导致身体仿真失稳。

