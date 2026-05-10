# training

训练流程目录，用于保存算法配置、训练脚本、回调、checkpoint、日志和策略评估工具。

## PPO Baseline

当前最小训练入口：

```bash
source .venv/bin/activate
python training/scripts/train_ppo.py --config training/configs/ppo_simple_quadruped.yaml
```

快速 dry-run：

```bash
python training/scripts/train_ppo.py \
  --config training/configs/ppo_simple_quadruped.yaml \
  --total-timesteps 1024 \
  --check-env
```

统一 shell 入口：

```bash
bash scripts/train.sh
```

训练日志写入 `training/logs/`，checkpoint 和最终模型写入 `training/checkpoints/`。这些产物默认不纳入 Git。

Bittle-like v0 模型 sanity training：

```bash
bash scripts/train.sh training/configs/ppo_bittle_like_v0.yaml
```

Bittle-like v0 站立稳定任务：

```bash
bash scripts/train.sh training/configs/ppo_bittle_like_v0_stand.yaml
```

Bittle-like v0 慢速前进 curriculum：

```bash
bash scripts/train.sh training/configs/ppo_bittle_like_v0_slow_forward.yaml
```

该配置默认从 `training/checkpoints/ppo_bittle_like_v0_stand/final_model.zip` warm-start，因此新服务器上需要先完成 stand 训练。

## TensorBoard

服务器上启动 TensorBoard：

```bash
bash scripts/tensorboard.sh
```

推荐使用 SSH 端口转发在本地浏览器访问。先在本地电脑运行：

```bash
ssh -L 6006:127.0.0.1:6006 ubuntu@<server-ip>
```

然后打开：

```text
http://127.0.0.1:6006
```

默认监听 `127.0.0.1:6006`，如需临时调整：

```bash
TENSORBOARD_PORT=6007 bash scripts/tensorboard.sh
```

## Evaluation

评估当前 final model：

```bash
python training/scripts/evaluate_policy.py \
  --config training/configs/ppo_simple_quadruped.yaml
```

统一 shell 入口：

```bash
bash scripts/evaluate.sh
```

评估报告默认写入 `experiments/reports/simple_quadruped_eval.json`，包含 episode reward、长度、前进距离、摔倒率、最终姿态和终止原因统计等指标。

## Export

导出确定性 actor 到 ONNX，并使用 ONNXRuntime 做一致性验证：

```bash
bash scripts/export_policy.sh training/configs/ppo_simple_quadruped.yaml
```

默认导出路径为 `models/onnx/simple_quadruped_actor.onnx`，验证报告写入 `models/reports/simple_quadruped_actor_onnx.json`。这些生成产物默认不纳入 Git。
