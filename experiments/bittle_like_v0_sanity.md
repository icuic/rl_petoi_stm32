# Bittle-like v0 Sanity Check

This note records the first bring-up run for `sim/robots/bittle_like_v0.xml`.

## Goal

Move beyond the toy `simple_quadruped.xml` model toward a Petoi Bittle-shaped simulator while preserving the current policy interface:

- Observation dimension: `29`
- Action dimension: `8`
- Joint order: `front_left`, `front_right`, `rear_left`, `rear_right`, each with `hip`, `knee`
- Action semantics: normalized joint targets in `[-1, 1]`

The goal of this run was only to verify that the model can train, evaluate, record, and export. It was not expected to produce a stable gait immediately.

## Model Changes

Compared with `simple_quadruped.xml`, `bittle_like_v0.xml` changes:

- Shorter body and leg dimensions.
- Narrower stance.
- More Bittle-like shell proportions and visual materials.
- Slightly different link masses, joint damping, and actuator limits.
- Same joint names and actuator order, so the v0 control interface remains compatible.

## Commands

Training:

```bash
bash scripts/train.sh training/configs/ppo_bittle_like_v0.yaml --total-timesteps 10000 --check-env
```

Evaluation:

```bash
bash scripts/evaluate.sh training/configs/ppo_bittle_like_v0.yaml --episodes 5 --output experiments/reports/bittle_like_v0_sanity_eval.json
```

Recording:

```bash
bash scripts/record_eval.sh training/configs/ppo_bittle_like_v0.yaml --max-steps 80 --output assets/videos/bittle_like_v0_sanity.mp4
```

ONNX export:

```bash
bash scripts/export_policy.sh training/configs/ppo_bittle_like_v0.yaml --samples 16 --output models/onnx/bittle_like_v0_actor.onnx --report models/reports/bittle_like_v0_actor_onnx.json
```

## Results

Training completed successfully on CUDA at about `475 fps`.

Evaluation summary:

| Metric | Value |
| --- | ---: |
| reward_mean | -2.39 |
| reward_std | 0.90 |
| steps_mean | 23.2 |
| distance_x_mean | -0.068 |
| fall_rate | 1.0 |
| final_torso_height_mean | 0.106 |
| final_roll_abs_mean | 1.266 |
| final_pitch_abs_mean | 0.489 |

Termination reasons:

```json
{"roll_too_large": 5}
```

ONNX parity:

| Check | Max Abs Diff | Mean Abs Diff |
| --- | ---: | ---: |
| PyTorch actor vs ONNXRuntime | 5.96e-8 | 1.78e-8 |
| SB3 deterministic predict vs ONNXRuntime | 1.19e-7 | 2.49e-8 |

## Interpretation

The Bittle-like v0 model is integrated correctly at the software level: Gym reset/step, PPO training, deterministic evaluation, MP4 recording, and ONNX export all work.

The policy does not yet walk. It falls by roll after roughly 20-30 steps. This is a useful result: the reward and/or initial posture that worked on the wider toy model does not transfer directly to the narrower Bittle-like geometry.

## Next Experiments

- Revisit the initial standing pose and torso height for the Bittle-like model.
- Add a short stand-still stabilization task before forward locomotion.
- Consider lowering early forward reward pressure and adding a stronger lateral stability curriculum.
- Inspect whether the narrower stance needs different `neutral_pose` or action scale before training.

Follow-up: `bittle_like_v0_stand.md` shows that stand-still stabilization succeeds after lowering PPO's initial exploration noise with `log_std_init: -2.0`.
