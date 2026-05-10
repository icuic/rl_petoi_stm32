# Bittle-like v0 Slow-Forward Curriculum

This note records the first slow-forward curriculum run for `sim/robots/bittle_like_v0.xml`.

## Goal

Start from the stable stand policy and introduce a small forward reward while preserving the stand task's low exploration noise and stability constraints.

## Configuration

Config:

```bash
training/configs/ppo_bittle_like_v0_slow_forward.yaml
```

Important settings:

```yaml
paths:
  init_model: training/checkpoints/ppo_bittle_like_v0_stand/final_model.zip
env:
  reward:
    forward: 0.2
    target_height: 0.115
    roll: 0.3
    pitch: 0.3
    vertical_velocity: 0.08
    joint_position: 0.08
    action: 0.015
    action_delta: 0.008
    fall: 1.0
ppo:
  policy_kwargs:
    log_std_init: -2.0
```

The run warm-starts from the stand checkpoint. On a fresh server, run the stand task first:

```bash
bash scripts/train.sh training/configs/ppo_bittle_like_v0_stand.yaml --check-env
```

## Commands

Training:

```bash
bash scripts/train.sh training/configs/ppo_bittle_like_v0_slow_forward.yaml --check-env
```

Evaluation:

```bash
bash scripts/evaluate.sh training/configs/ppo_bittle_like_v0_slow_forward.yaml --episodes 10 --output experiments/reports/bittle_like_v0_slow_forward_eval.json
```

Recording:

```bash
bash scripts/record_eval.sh training/configs/ppo_bittle_like_v0_slow_forward.yaml --max-steps 300 --output assets/videos/bittle_like_v0_slow_forward.mp4
```

ONNX export:

```bash
bash scripts/export_policy.sh training/configs/ppo_bittle_like_v0_slow_forward.yaml --samples 16 --output models/onnx/bittle_like_v0_slow_forward_actor.onnx --report models/reports/bittle_like_v0_slow_forward_actor_onnx.json
```

## Results

Training completed successfully on CUDA at about `449 fps`. The policy remained stable throughout training: `ep_len_mean` stayed at `1000`.

Evaluation summary:

| Metric | Value |
| --- | ---: |
| reward_mean | 376.32 |
| reward_std | 0.10 |
| steps_mean | 1000.0 |
| distance_x_mean | -0.077 |
| distance_x_std | 0.001 |
| fall_rate | 0.0 |
| final_torso_height_mean | 0.106 |
| final_roll_abs_mean | 0.0026 |
| final_pitch_abs_mean | 0.392 |

Termination reasons:

```json
{"timeout": 10}
```

ONNX parity:

| Check | Max Abs Diff | Mean Abs Diff |
| --- | ---: | ---: |
| PyTorch actor vs ONNXRuntime | 8.94e-8 | 1.36e-8 |
| SB3 deterministic predict vs ONNXRuntime | 8.94e-8 | 1.62e-8 |

## Interpretation

This is a successful curriculum plumbing test, but not yet a walking policy.

The policy keeps the Bittle-like model upright for the full episode, which preserves the stand milestone. However, the small forward reward is not strong enough to overcome the stabilizing penalties. The resulting behavior is still effectively standing, with a tiny negative x displacement.

## Next Experiments

- Increase `forward` reward and reduce `joint_position`/`action` penalties in small steps.
- Replace generic joint-position penalty with a gait-phase-friendly regularizer.
- Add a target velocity reward instead of raw forward velocity.
- Consider a scripted trot prior or imitation warm-start before PPO.
