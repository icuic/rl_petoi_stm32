# Bittle-like v0 Stand Stabilization

This note records the first successful stand-still stabilization task for `sim/robots/bittle_like_v0.xml`.

## Goal

Before training forward locomotion on the narrower Bittle-like geometry, prove that the robot can maintain a stable standing posture for a full 1000-step episode.

## Key Finding

The Bittle-like model can stand in the simulator, but PPO's default exploration noise is too large for this narrow stance. With the default policy standard deviation, training repeatedly fell after roughly 20-30 steps. Lowering the initial policy log standard deviation was the decisive change:

```yaml
ppo:
  policy_kwargs:
    log_std_init: -2.0
```

This starts stochastic exploration around a much smaller action scale, which is more appropriate for a stand-still task.

## Static Pose Diagnostic

Before the successful run, a zero-action diagnostic showed that the neutral pose can remain healthy for 300 steps when initialized near the settled body height. The torso naturally settles around `0.114 m`, so the stand reward target was changed from an unrealistic `0.18 m` to `0.115 m`.

## Configuration

Config:

```bash
training/configs/ppo_bittle_like_v0_stand.yaml
```

Important settings:

```yaml
env:
  reset:
    torso_height: 0.16
    joint_noise: 0.01
    velocity_noise: 0.005
  reward:
    forward: 0.0
    target_height: 0.115
    roll: 0.3
    pitch: 0.3
    xy_velocity: 0.08
    vertical_velocity: 0.08
    joint_position: 0.1
    action: 0.02
    action_delta: 0.01
    drift: 0.1
    fall: 1.0
ppo:
  policy_kwargs:
    log_std_init: -2.0
```

## Commands

Training:

```bash
bash scripts/train.sh training/configs/ppo_bittle_like_v0_stand.yaml --check-env
```

Evaluation:

```bash
bash scripts/evaluate.sh training/configs/ppo_bittle_like_v0_stand.yaml --episodes 10 --output experiments/reports/bittle_like_v0_stand_eval.json
```

Recording:

```bash
bash scripts/record_eval.sh training/configs/ppo_bittle_like_v0_stand.yaml --max-steps 200 --output assets/videos/bittle_like_v0_stand.mp4
```

ONNX export:

```bash
bash scripts/export_policy.sh training/configs/ppo_bittle_like_v0_stand.yaml --samples 16 --output models/onnx/bittle_like_v0_stand_actor.onnx --report models/reports/bittle_like_v0_stand_actor_onnx.json
```

## Results

Training completed successfully on CUDA at about `462 fps`.

Evaluation summary:

| Metric | Value |
| --- | ---: |
| reward_mean | 368.21 |
| reward_std | 0.05 |
| steps_mean | 1000.0 |
| distance_x_mean | -0.074 |
| fall_rate | 0.0 |
| final_torso_height_mean | 0.108 |
| final_roll_abs_mean | 0.0055 |
| final_pitch_abs_mean | 0.443 |

Termination reasons:

```json
{"timeout": 10}
```

ONNX parity:

| Check | Max Abs Diff | Mean Abs Diff |
| --- | ---: | ---: |
| PyTorch actor vs ONNXRuntime | 4.47e-8 | 9.77e-9 |
| SB3 deterministic predict vs ONNXRuntime | 8.20e-8 | 1.29e-8 |

## Interpretation

This is the first stable Bittle-like milestone. The policy is not a walking controller; it is a controlled stand-still baseline. That is still valuable because it separates two problems:

- The Bittle-like MJCF can be stabilized.
- Forward locomotion should now be introduced as a curriculum after stable standing, not as the first objective.

## Next Experiments

- Add a slow-forward curriculum with a small positive forward reward.
- Keep low exploration noise for early locomotion.
- Gradually relax action and drift penalties.
- Compare warm-starting locomotion from the stand policy versus training locomotion from scratch.

Follow-up: `bittle_like_v0_slow_forward.md` keeps the robot stable for 1000 steps, but the first small forward reward is not enough to produce positive forward displacement.
