# Petoi Bittle × 强化学习步态 × STM32H747

## 项目概述

面向 **Petoi Bittle X V2** 四足机器人：在仿真中用强化学习学得稳定步态，将策略 **轻量化与量化** 后部署到 **STM32H747I-DISCO**，由 MCU **独立做推理并联机下发运动指令**，形成 **仿真训练 → 嵌入式推理 → 真机执行** 闭环。本项目用于衔接「嵌入式」与「强化学习」两条技术线。

- 真机：Bittle X V2（机载 ESP32 / BiBoard，生态见 [Bittle X V2 说明](https://guide.petoi.com/product/bittle-x-v2)）。
- 边缘推理板：STM32H747（[STM32H747I-DISCO](https://www.st.com/en/evaluation-tools/stm32h747i-disco.html)），策略以 **MCU 常驻推理** 为叙事核心。
- 运动控制开源背景：Petoi **OpenCat** 相关栈（固件与协议在具体联调阶段再对齐）。

## Current Status

当前仓库已推进到 **gait_quality_v2 30k 策略候选 + STM32H747 M7 smoke ELF** 阶段。实物 Bittle X V2 到手前，当前重点是准备硬件联调链路与安全边界；真机部署仍应从站立、零动作、低幅度动作开始逐步推进。

- 当前推荐训练配置：`training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2.yaml`
- 当前推荐 checkpoint：`training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_steps.zip`
- 不推荐使用：`training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2/final_model.zip`，该 v2 final 在 30k 后明显退化；旧 100k continuation final 也不推荐使用。
- 当前 30 episode deterministic 评估：`reward_mean=666.5192`，`distance_x_mean=1.4234m`，`fall_rate=0.0`。
- 当前 ONNX：`models/onnx/petoi_bittle_v0_gait_quality_v2_30k_actor.onnx`
- 当前策略向量：`firmware/stm32h747_disco/test_vectors/gait_quality_v2_30k_policy_vector.json`
- 当前 STM32 ELF：`build/stm32h747_m7_inference_smoke/m7_inference_smoke.elf`
- 当前 rollout 视频：`assets/videos/petoi_bittle_v0_gait_quality_v2_30k_rollout_track_matte.mp4`
- 旧 10k deployable 策略保留为回退基线：`training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue_10000_steps.zip`
- 已完成 gait_quality_v1/v2 诊断实验：v1 改善后腿滑移但牺牲前进距离；v2 30k 在仿真距离、接触滑移比例和视觉观感上是当前更好的折中。详见 `experiments/petoi_bittle_v0_gait_diagnosis.md`。
- 状态详情见：`docs/training_status.md`
- Gait 诊断见：`experiments/petoi_bittle_v0_gait_diagnosis.md`
- Hand gait / RL 对照实验见：`experiments/gait_baseline_comparison.md`
- 硬件到手前 checklist：`docs/hardware_bringup_checklist.md`
- 里程碑备份见：`docs/artifact_backup.md` 和 `scripts/pack_artifacts.sh`

常用检查命令：

```bash
bash scripts/select_checkpoint.sh 'experiments/reports/checkpoint_eval/*.json' --min-episodes 5
bash scripts/record_eval.sh training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue.yaml \
  --model training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue_10000_steps.zip \
  --output assets/videos/petoi_bittle_v0_deployable_v0_10k_rollout.mp4
bash scripts/evaluate.sh training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2.yaml \
  --model training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_steps.zip \
  --episodes 30 \
  --output experiments/reports/petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_eval_30ep.json
bash scripts/record_eval.sh training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2.yaml \
  --model training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_steps.zip \
  --output assets/videos/petoi_bittle_v0_gait_quality_v2_30k_rollout_track_matte.mp4
bash scripts/export_policy.sh training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2.yaml \
  --model training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_steps.zip \
  --output models/onnx/petoi_bittle_v0_gait_quality_v2_30k_actor.onnx \
  --report models/reports/petoi_bittle_v0_gait_quality_v2_30k_actor_onnx.json \
  --vector-output firmware/stm32h747_disco/test_vectors/gait_quality_v2_30k_policy_vector.json
bash scripts/generate_bittle_bringup_vectors.sh
bash scripts/bittle_bringup_probe.sh --list
bash scripts/record_eval.sh training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue.yaml \
  --zero-action --output assets/videos/gait_compare_A_hand_gait_prior_track.mp4
bash scripts/analyze_policy_actions.sh training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue.yaml
bash scripts/analyze_gait_contacts.sh training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue.yaml \
  --episodes 5 --prefix petoi_bittle_v0_deployable_v0_10k_5seed
bash scripts/pack_artifacts.sh
```

## 仿真与模型

- **仿真**：**MuJoCo**（配套 Gymnasium 等），不强制初版即几何 1:1 Bittle。
- **机器人模型**：优先使用社区 **URDF/MJCF 四足模型**，按杆长、关节限位与惯量 **向真机近似**；辅以域随机化与噪声改善 sim2real。
- **训练**：在 GPU（如 Tesla T4）上迭代；环境与算法可选 SB3 / CleanRL 等，以并行采样与可调超参缩短迭代周期。

## 观测空间（当前约定）

- 机身 **滚转 / 俯仰**（宜用 sin/cos 等平滑表示）、**角速度**。
- **各关节角与角速度**。
- 固定节律 **步态相位** φ ∈ [0, 1)。
- 仿真阶段若易得：**足底接触** 作为辅助观测以加快学习；真机无量测时可弱化或改为估计。

## 动作空间（当前约定）

- 策略输出 **归一化关节目标增量 Δq**；经 **限幅与速度约束** 后得到本控制周期 **舵机目标角**（贴合位置伺服与 MCU 侧安全逻辑）。

## 硬件与通信

- **控制架构**：**仅在 STM32 上完成推理并发指令**（简历与演示主线）。
- DISCO 板 **无原生蓝牙**；真机链路可能为 **扩展无线模块、桥接或经 Bittle 侧连接**。
- **与真机对话方式**（官方 App / 串口 / WiFi UDP 等）：**不阻塞仿真训练**，在部署与联调阶段确定即可。

## 部署

- 导出格式按需选择（如 TFLite Micro、X-CUBE-AI 等），以 **INT8 量化、小内存** 为约束，使网络可常驻 H7。

## 阶段目标（可后续细化指标）

1. 仿真中稳定节律行走（平地为主）。
2. 真机短时行走 / 抗轻扰。
3. DISCO **实时推理 + 下发指令** 与真机联调。

## 工程化目录结构规划

本仓库按 **训练侧、部署侧、通信侧、真机适配侧、文档演示侧** 分层组织。目标是同时支撑：

- **可演示作品**：每个阶段都有可录屏、可拍摄、可复现的结果。
- **工程项目深挖**：关键模块有清晰接口、指标记录、资源约束与测试依据。

建议目录结构如下：

```text
rl_petoi/
├── README.md
├── install_codex.sh
├── docs/
│   ├── roadmap.md
│   ├── hardware.md
│   ├── protocol.md
│   ├── sim2real.md
│   ├── deployment.md
│   └── demo_plan.md
├── assets/
│   ├── images/
│   └── videos/
├── requirements.txt
├── sim/
│   ├── envs/
│   ├── robots/
│   ├── tasks/
│   ├── rewards/
│   ├── wrappers/
│   └── tests/
├── training/
│   ├── configs/
│   ├── scripts/
│   ├── callbacks/
│   ├── checkpoints/
│   ├── logs/
│   └── eval/
├── models/
│   ├── exported/
│   ├── quantized/
│   └── reports/
├── tools/
│   ├── export_model/
│   ├── quantization/
│   ├── telemetry/
│   └── calibration/
├── firmware/
│   ├── stm32h747_disco/
│   │   ├── Core/
│   │   ├── Drivers/
│   │   ├── Middlewares/
│   │   ├── App/
│   │   │   ├── inference/
│   │   │   ├── control/
│   │   │   ├── comm/
│   │   │   ├── safety/
│   │   │   └── telemetry/
│   │   └── README.md
│   └── petoi_opencat/
│       ├── protocol_adapter/
│       ├── joint_command_mode/
│       └── README.md
├── protocol/
│   ├── messages.md
│   ├── schemas/
│   └── test_vectors/
├── experiments/
│   ├── runs/
│   ├── notebooks/
│   └── reports/
└── scripts/
    ├── setup_env.sh
    ├── check_env.sh
    ├── setup_stedgeai.sh
    ├── train.sh
    ├── evaluate.sh
    ├── export_policy.sh
    └── flash_stm32.sh
```

### 目录职责

- `docs/`：保存项目路线图、硬件连接、通信协议、sim2real、模型部署和演示计划。面试时可直接作为工程说明材料。
- `assets/`：保存图片、架构图、演示视频素材和最终 demo 截图。
- `sim/`：MuJoCo / Gymnasium 仿真环境主体，包括机器人模型、任务定义、奖励函数、环境包装器和仿真测试。
- `training/`：训练入口、算法配置、回调、checkpoint、日志和评估脚本。训练产物不应只散落在本地机器。
- `models/`：保存导出的策略网络、量化后的 MCU 版本和量化误差 / 推理延迟 / 内存占用报告。
- `tools/`：放置模型导出、量化、遥测解析、舵机标定等跨平台工具。
- `firmware/stm32h747_disco/`：STM32H747I-DISCO 固件工程，突出 **MCU 本地推理、运动指令生成、无线通信、安全限幅、遥测输出**。
- `firmware/petoi_opencat/`：Petoi / OpenCat 侧适配代码。允许修改真机固件后，可实现更直接的关节命令模式或协议适配层。
- `protocol/`：定义 STM32 与 Bittle 之间的消息格式、测试向量和版本化协议，避免通信逻辑散落在两端代码中。
- `experiments/`：保存实验记录、训练曲线分析、参数对比和阶段性报告，支撑简历中的量化描述。
- `scripts/`：统一常用命令入口，让环境重建、训练、评估、导出和烧录尽量脚本化。

### 初期落地顺序

1. 先建立 `docs/`、`sim/`、`training/`、`models/`、`scripts/`，支撑无真机阶段的仿真训练闭环。
2. 在 STM32H747I-DISCO 上先完成 `firmware/stm32h747_disco/App/inference/` 的空模型或假模型推理框架，提前验证实时任务、内存布局和日志输出。
3. 等 Bittle 到手后补齐 `protocol/` 与 `firmware/petoi_opencat/`，优先实现无线链路下的关节目标下发与安全回退。
4. 每个阶段都在 `experiments/reports/` 和 `assets/videos/` 中保存可展示证据，避免最后才补材料。

## 一键环境重建

当前服务器租期只有 7 天，因此本项目把 **可重复搭建环境** 作为基础工程能力。新服务器初始化建议流程：

```bash
git clone git@github.com:icuic/rl_petoi_stm32.git
cd rl_petoi_stm32
bash install_codex.sh
bash scripts/setup_env.sh
bash scripts/setup_stedgeai.sh
source .venv/bin/activate
bash scripts/check_env.sh
```

如果新云服务器需要立即重新连回接着 Bittle 的本地 Ubuntu，以本地 Ubuntu
现有 `/usr/local/frp/frpc.toml` 中的 `auth.token` 为准。先从本地记录或
本地配置文件复制这个 token，然后在新云服务器上启动 FRP 反向 SSH relay：

```bash
FRP_TOKEN="本地frpc.toml中的auth.token" \
bash scripts/setup_reverse_ssh_frp.sh server --print-client --start
```

然后在本地 Ubuntu 的 `/usr/local/frp/frpc.toml` 中把 `serverAddr` 改成新
云服务器公网 IP，并重启 `frpc`：

```bash
sudo systemctl restart frpc
```

不要把 FRP token 提交到 Git。详见 `docs/reverse_ssh_recovery.md`。

其中：

- `install_codex.sh`：安装 Codex CLI 并开启远程连接。
- `scripts/setup_env.sh`：创建项目目录、安装 Ubuntu 系统依赖、创建 `.venv`、安装 MuJoCo / Gymnasium / Stable-Baselines3 等 Python 依赖。
- `scripts/setup_stedgeai.sh`：接入本地 ST Edge AI Core / `stedgeai` CLI，不使用 Web 工具链。
- `scripts/check_env.sh`：一键检查 CPU、内存、磁盘、GPU、Python、MuJoCo、Stable-Baselines3、PyTorch CUDA 和 ST Edge AI CLI 状态。
- `requirements.txt`：记录训练侧基础依赖，后续新增库时必须同步更新。
- `docs/environment.md`：记录环境重建流程、依赖策略和后续增强项。

当前仿真侧已有两套模型配置：

- `training/configs/ppo_simple_quadruped.yaml`：最小四足稳定 gait 基线。
- `training/configs/ppo_bittle_like_v0.yaml`：面向 Petoi Bittle 形态迁移的 v0 近似模型，用于后续站立稳定与步态迁移实验。
- `training/configs/ppo_bittle_like_v0_stand.yaml`：Bittle-like v0 的站立稳定任务，用于先解决窄站姿 roll 翻倒，再进入前进步态。
- `training/configs/ppo_bittle_like_v0_slow_forward.yaml`：从 stand policy warm-start 的慢速前进 curriculum。
- `training/configs/ppo_bittle_like_v1_visual_stand.yaml`：更接近 Bittle 外观的 v1 visual 模型站立 smoke test。

后续训练产生的 checkpoint、TensorBoard 日志、导出模型和演示视频不宜只保存在租用服务器本地，应定期同步到远程仓库、网盘、对象存储或 Git LFS。

## 环境与协作说明

- 开发机可能为短周期租用；建议 **代码与依赖可脚本化重建**（Docker / conda export / requirements），**检查点与日志定期备份** 到网盘或私有仓库。

---

*本文档由项目初期讨论整理，随实现进展可继续修订。*
