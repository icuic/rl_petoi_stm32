# Petoi Bittle v0 Trot Residual v2

Date: 2026-05-10

## Goal

Adjust the residual trot reward so that locomotion is driven by explicit
per-step forward progress instead of mainly by posture and survival rewards.

## Reward Changes

- Added `progress`, a reward term based on per-step `x_position` delta.
- Changed `drift_penalty` to penalize lateral `y` drift only, so forward travel
  is no longer punished by the drift term.
- Added `lateral_velocity_penalty` for sideways velocity.
- Reduced survival, upright, posture, and action penalties compared with the
  first residual trot baseline.

## Training Setup

- Config: `training/configs/ppo_petoi_bittle_v0_trot_residual_v2.yaml`
- Warm start: `training/checkpoints/ppo_petoi_bittle_v0_stand/final_model.zip`
- Control mode: `residual_trot`
- Residual action scale: `0.12 rad`
- Reference gait:
  - `period_steps: 120`
  - `shoulder_amplitude: 0.08`
  - `knee_amplitude: 0.12`

Command:

```bash
.venv/bin/python training/scripts/train_ppo.py --config training/configs/ppo_petoi_bittle_v0_trot_residual_v2.yaml
```

Result:

- Requested timesteps: `30000`
- Actual timesteps: `30208`
- Training FPS: about `114`
- Wall time: about `264 s`
- Episode length mean: `1000`
- Rollout reward mean increased from about `88.8` to `94.8`

## Evaluation

Command:

```bash
MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python training/scripts/evaluate_policy.py --config training/configs/ppo_petoi_bittle_v0_trot_residual_v2.yaml
```

Report: `experiments/reports/petoi_bittle_v0_trot_residual_v2_eval.json`

Summary:

- `reward_mean`: `91.5625`
- `steps_mean`: `1000.0`
- `fall_rate`: `0.0`
- `distance_x_mean`: `-0.0869 m`
- `final_torso_height_mean`: `0.0492 m`
- `final_roll_abs_mean`: `0.0200 rad`
- `final_pitch_abs_mean`: `0.0030 rad`
- Terminations: `timeout: 10`

## Comparison

| Policy | Timesteps | Fall rate | Mean distance x |
| --- | ---: | ---: | ---: |
| Open-loop trot reference | 1000-step smoke | 0.0 | `0.0423 m` |
| Residual trot v1 | 30208 | 0.0 | `-0.0968 m` |
| Residual trot v2 | 30208 | 0.0 | `-0.0869 m` |

## Conclusion

The v2 reward change improved deterministic forward displacement by about
`0.0099 m` relative to v1, while preserving stability. It did not yet produce
net forward motion.

The most likely issue is that a 30k PPO run from the stand checkpoint is still
too short for the deterministic policy mean to overcome the backward residual
preference. The open-loop reference itself can move forward, so the next step
should preserve that prior more strongly and make the residual policy less able
to cancel it early in training.

## Next Iteration

- Train v2 for `100k` timesteps before changing the reward again.
- If deterministic evaluation still moves backward, reduce residual action scale
  to `0.06-0.08 rad` or initialize from a zero-residual policy rather than the
  stand policy.
- Add an evaluation mode for zero-action residual trot to track the open-loop
  reference under the exact Gym environment and report format.
