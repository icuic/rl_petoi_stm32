# Milestone 01: Minimal Stable Gait

This milestone captures the first end-to-end RL baseline for the project: train a minimal MuJoCo quadruped with PPO, evaluate deterministic rollouts, and record demo video material on a rented GPU server.

## Outcome

The project now has a reproducible training, evaluation, and recording loop:

```text
MuJoCo SimpleQuadrupedEnv -> SB3 PPO -> deterministic evaluation -> MP4 rollout recording
```

The stability-v2 reward is the first policy that reaches the 1000-step episode limit consistently in deterministic evaluation.

## Environment

- Robot model: `sim/robots/simple_quadruped.xml`
- Gym environment: `sim/envs/simple_quadruped_env.py`
- Observation shape: `29`
- Action shape: `8`
- Action semantics: normalized joint target command in `[-1, 1]`
- Control target mapping: `neutral_pose + action * action_scale`
- Episode limit: `1000` environment steps

## Training

- Algorithm: PPO
- Implementation: Stable-Baselines3
- Policy: MLP actor-critic, hidden layers `[64, 64]`
- Training budget: `100000` timesteps
- Hardware: Tesla T4
- Observed training time: about `207s`

Reproduction command:

```bash
bash scripts/train.sh training/configs/ppo_simple_quadruped.yaml --total-timesteps 100000
```

## Evaluation

Command:

```bash
bash scripts/evaluate.sh training/configs/ppo_simple_quadruped.yaml --episodes 10 --output experiments/reports/simple_quadruped_eval_stability_v2.json
```

Summary:

| Metric | Value |
| --- | ---: |
| reward_mean | 423.55 |
| reward_std | 40.21 |
| steps_mean | 1000.0 |
| distance_x_mean | 5.75 |
| distance_x_std | 0.66 |
| fall_rate | 0.0 |
| final_roll_abs_mean | 0.068 |
| final_pitch_abs_mean | 0.342 |

Termination reasons:

```json
{"timeout": 10}
```

## Demo Recording

Command:

```bash
bash scripts/record_eval.sh training/configs/ppo_simple_quadruped.yaml --output assets/videos/simple_quadruped_stability_v2.mp4
```

On the current server, short rollout smoke recording succeeded. EGL may print a `/dev/dri/renderD128` permission warning, but MP4 generation still works.

## Engineering Significance

This milestone is intentionally small, but it is already useful as an interview project anchor:

- Reproducible setup for short-lived rented servers.
- RL training loop with explicit config and hardware/runtime notes.
- Deterministic evaluation with termination-reason diagnostics.
- Reward-shaping iteration history with a failed attempt and a successful baseline.
- Demo video generation path.

## ONNX Export

Command:

```bash
bash scripts/export_policy.sh training/configs/ppo_simple_quadruped.yaml --samples 64
```

Exported actor interface:

| Field | Value |
| --- | --- |
| input | `observation`, shape `[batch, 29]`, `float32` |
| output | `action`, shape `[batch, 8]`, `float32` |
| action range | clamped to `[-1, 1]` |
| ONNX opset | `17` |

Parity check:

| Check | Max Abs Diff | Mean Abs Diff |
| --- | ---: | ---: |
| PyTorch actor vs ONNXRuntime | 2.98e-7 | 3.53e-8 |
| SB3 deterministic predict vs ONNXRuntime | 4.77e-7 | 5.21e-8 |

This is close enough to treat the ONNX actor as behaviorally equivalent for the current minimal policy.

## Next Step

Define the embedded control interface v0: observation layout, action layout, timing, units, normalization, and how normalized actions map to Petoi servo targets.
