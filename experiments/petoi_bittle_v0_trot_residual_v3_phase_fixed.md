# Petoi Bittle v0 Trot Residual v3 Phase Fixed

Date: 2026-05-10

## Goal

Train a residual trot PPO policy after fixing the Gym phase timing bug found by
zero-action evaluation. This run uses the corrected interpretation that
`gait.period_steps` is measured in MuJoCo physics steps, not Gym environment
steps.

## Setup

- Config: `training/configs/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed.yaml`
- Model: `build/petoi_bittle/petoi_bittle_v0.xml`
- Warm start: `training/checkpoints/ppo_petoi_bittle_v0_stand/final_model.zip`
- Control mode: `residual_trot`
- Residual action scale: `0.06 rad`
- Reference gait:
  - `period_steps: 120`
  - `shoulder_amplitude: 0.08`
  - `knee_amplitude: 0.12`

## Training

Command:

```bash
.venv/bin/python training/scripts/train_ppo.py --config training/configs/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed.yaml
```

Result:

- Requested timesteps: `30000`
- Actual timesteps: `30208`
- Training FPS: about `114`
- Wall time: about `263 s`
- Episode length mean: `1000`
- Rollout reward started near the zero-action reference level, dropped during
  exploration, and recovered to about `41.8` by the final rollout.

## Evaluation

Command:

```bash
MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python training/scripts/evaluate_policy.py --config training/configs/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed.yaml
```

Report: `experiments/reports/petoi_bittle_v0_trot_residual_v3_phase_fixed_eval.json`

Summary:

- `reward_mean`: `177.4095`
- `steps_mean`: `1000.0`
- `fall_rate`: `0.0`
- `distance_x_mean`: `0.5029 m`
- `distance_x_std`: `0.2510 m`
- `final_torso_height_mean`: `0.0499 m`
- `final_roll_abs_mean`: `0.0261 rad`
- `final_pitch_abs_mean`: `0.0564 rad`
- Terminations: `timeout: 10`

## Comparison

| Policy | Phase timing | Fall rate | Mean distance x |
| --- | --- | ---: | ---: |
| Residual trot v2 PPO | too slow | 0.0 | `-0.0869 m` |
| Zero-action residual trot | fixed | 0.0 | `0.4288 m` |
| Residual trot v3 PPO | fixed | 0.0 | `0.5029 m` |

## Videos

Two 500-step diagnostic videos were recorded with the same renderer and config:

```bash
bash scripts/record_eval.sh training/configs/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed.yaml \
  --zero-action \
  --max-steps 500 \
  --fps 50 \
  --output assets/videos/petoi_bittle_v0_zero_action_residual_trot.mp4

bash scripts/record_eval.sh training/configs/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed.yaml \
  --max-steps 500 \
  --fps 50 \
  --output assets/videos/petoi_bittle_v0_trot_residual_v3_phase_fixed.mp4
```

Results:

- `assets/videos/petoi_bittle_v0_zero_action_residual_trot.mp4`
  - `steps=500`
  - `reward=117.638`
  - `termination_reason=healthy`
- `assets/videos/petoi_bittle_v0_trot_residual_v3_phase_fixed.mp4`
  - `steps=500`
  - `reward=132.452`
  - `termination_reason=healthy`

## Conclusion

The corrected phase timing turns the residual trot setup into a valid forward
locomotion task. The zero-action gait is already a strong demonstration
baseline, and v3 PPO improves mean forward distance while preserving full
episode stability.

The variance is still high, so the next useful step is not deployment yet. The
next step should run a longer v3 training pass or a lower-variance seed sweep to
confirm the improvement.
