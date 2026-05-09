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
