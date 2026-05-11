# Petoi Bittle v0 Demo Milestone

Date: 2026-05-11

## Summary

This milestone captures the first strong Petoi simulated locomotion demo:

- Official Petoi-derived MJCF model
- Phase-corrected residual trot reference
- PPO residual policy trained from the stand policy
- Deterministic 20-episode evaluation with no falls
- ONNX export with parity verification
- MP4 rollout videos for the open-loop and learned policies

## Best Policy

Current best checkpoint:

```text
training/checkpoints/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue_90000_steps.zip
```

Config:

```text
training/configs/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue.yaml
```

Why this checkpoint:

- 90k checkpoint, 20 episodes:
  - `distance_x_mean`: `1.3085 m`
  - `distance_x_std`: `0.0146 m`
  - `fall_rate`: `0.0`
  - `termination_reason_counts`: `timeout: 20`
- 95k checkpoint had a slightly higher 10-episode mean, but the 20-episode
  validation had much higher variance.
- The final model was good, but not the best checkpoint.

## Baseline Comparison

| Policy | Evaluation | Fall rate | Mean distance x | Distance std |
| --- | ---: | ---: | ---: | ---: |
| Zero-action residual trot | 10 episodes | 0.0 | `0.4288 m` | `0.1738 m` |
| v3 phase-fixed PPO, 30k | 10 episodes | 0.0 | `0.5029 m` | `0.2510 m` |
| v3 100k continue, final | 10 episodes | 0.0 | `1.2350 m` | `0.2418 m` |
| v3 100k continue, 90k checkpoint | 20 episodes | 0.0 | `1.3085 m` | `0.0146 m` |

## Demo Videos

Videos are generated artifacts and are not tracked by Git.

Open-loop / zero-action corrected reference:

```text
assets/videos/petoi_bittle_v0_zero_action_residual_trot.mp4
```

Best learned policy:

```text
assets/videos/petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue_best_90000.mp4
```

Recreate the best-policy video:

```bash
bash scripts/record_eval.sh training/configs/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue.yaml \
  --model training/checkpoints/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue_90000_steps.zip \
  --max-steps 500 \
  --fps 50 \
  --output assets/videos/petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue_best_90000.mp4
```

Recorded rollout result:

- `steps=500`
- `reward=287.064`
- `termination_reason=healthy`

## ONNX Export

Command:

```bash
bash scripts/export_policy.sh training/configs/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue.yaml \
  --model training/checkpoints/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue_90000_steps.zip \
  --output models/onnx/petoi_bittle_v0_trot_residual_v3_best_actor.onnx \
  --report models/reports/petoi_bittle_v0_trot_residual_v3_best_actor_onnx.json \
  --samples 64
```

Generated artifacts:

```text
models/onnx/petoi_bittle_v0_trot_residual_v3_best_actor.onnx
models/reports/petoi_bittle_v0_trot_residual_v3_best_actor_onnx.json
```

Parity:

- `observation_dim`: `29`
- `action_dim`: `8`
- `torch_vs_onnx_max_abs_diff`: `8.940696716308594e-08`
- `torch_vs_onnx_mean_abs_diff`: `1.6974809113889933e-08`
- `sb3_vs_onnx_max_abs_diff`: `1.1920928955078125e-07`
- `sb3_vs_onnx_mean_abs_diff`: `2.4851260604918934e-08`
- `action_min`: `-0.4286508858203888`
- `action_max`: `0.5392369031906128`

## Engineering Notes

- The key bug fix was phase timing: residual trot phase must advance by
  `frame_skip / gait_period_steps`, because `gait.period_steps` is measured in
  MuJoCo physics steps.
- Final checkpoints are not necessarily best. The 90k checkpoint was selected
  through deterministic checkpoint evaluation, not by assuming the final model
  was optimal.
- Checkpoint selection is now scriptable:

```bash
bash scripts/select_checkpoint.sh \
  'experiments/reports/petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue_*eval*.json' \
  --min-episodes 20 \
  --output-json experiments/reports/petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_checkpoint_ranking_20ep.json
```

  With the 20-episode validation threshold, the helper selects the 90k
  checkpoint as rank 1.
- The ONNX actor exports the deterministic normalized residual action. Runtime
  deployment still needs the same observation construction and residual target
  reconstruction used by the Gym environment.

## Next Steps

- Run a lower-learning-rate fine-tune from the 90k best checkpoint.
- Start defining the embedded inference interface: observation vector layout,
  action scaling, residual reference generation, and timing budget for STM32.
