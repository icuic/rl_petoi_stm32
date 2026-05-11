# Petoi Bittle v0 Trot Residual v3 Phase Fixed 100k Continue

Date: 2026-05-10

## Goal

Continue training the phase-fixed v3 residual trot policy for a longer run and
check whether more PPO updates improve deterministic forward locomotion.

## Setup

- Config: `training/configs/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue.yaml`
- Initial model: `training/checkpoints/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed/final_model.zip`
- Output model: `training/checkpoints/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue/final_model.zip`
- Control mode: `residual_trot`
- Residual action scale: `0.06 rad`
- Reference gait:
  - `period_steps: 120`
  - `shoulder_amplitude: 0.08`
  - `knee_amplitude: 0.12`

## Training

Command:

```bash
.venv/bin/python training/scripts/train_ppo.py --config training/configs/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue.yaml
```

Result:

- Requested timesteps: `100000`
- Actual timesteps: `100352`
- Training FPS: about `114-115`
- Wall time: about `872 s`
- Episode length mean: `1000`
- Rollout reward initially dropped from about `220` into negative values, then
  recovered steadily during the second half of training and ended around `159`.

## Evaluation

Command:

```bash
MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python training/scripts/evaluate_policy.py --config training/configs/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue.yaml
```

Report: `experiments/reports/petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue_eval.json`

Summary:

- `reward_mean`: `318.1431`
- `steps_mean`: `1000.0`
- `fall_rate`: `0.0`
- `distance_x_mean`: `1.2350 m`
- `distance_x_std`: `0.2418 m`
- `final_torso_height_mean`: `0.0499 m`
- `final_roll_abs_mean`: `0.0239 rad`
- `final_pitch_abs_mean`: `0.0484 rad`
- Terminations: `timeout: 10`

## Video

Command:

```bash
bash scripts/record_eval.sh training/configs/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue.yaml \
  --max-steps 500 \
  --fps 50 \
  --output assets/videos/petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue.mp4
```

Result:

- `assets/videos/petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue.mp4`
- `steps=500`
- `reward=283.605`
- `termination_reason=healthy`

Best-checkpoint demo command:

```bash
bash scripts/record_eval.sh training/configs/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue.yaml \
  --model training/checkpoints/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue_90000_steps.zip \
  --max-steps 500 \
  --fps 50 \
  --output assets/videos/petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue_best_90000.mp4
```

Result:

- `assets/videos/petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue_best_90000.mp4`
- `steps=500`
- `reward=287.064`
- `termination_reason=healthy`

## Comparison

| Policy | Training | Fall rate | Mean distance x |
| --- | ---: | ---: | ---: |
| Zero-action residual trot | none | 0.0 | `0.4288 m` |
| Residual trot v3 phase fixed | 30208 | 0.0 | `0.5029 m` |
| Residual trot v3 100k continue | 100352 more | 0.0 | `1.2350 m` |

## Checkpoint Sweep

Several late checkpoints were evaluated with the same deterministic protocol to
check whether the final model was the best candidate:

| Checkpoint | Episodes | Fall rate | Mean distance x | Distance std | Reward mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| 60000 | 10 | 0.0 | `0.9619 m` | `0.0178 m` | `329.8345` |
| 70000 | 10 | 0.0 | `1.0569 m` | `0.1700 m` | `321.6217` |
| 80000 | 10 | 0.0 | `1.1917 m` | `0.0155 m` | `393.1036` |
| 90000 | 10 | 0.0 | `1.3029 m` | `0.0163 m` | `440.0439` |
| 95000 | 10 | 0.0 | `1.3202 m` | `0.0195 m` | `419.3481` |
| final | 10 | 0.0 | `1.2350 m` | `0.2418 m` | `318.1431` |

The 95000-step checkpoint had the best 10-episode mean distance, but a larger
20-episode validation showed that it was less robust:

| Checkpoint | Episodes | Fall rate | Mean distance x | Distance std | Reward mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| 90000 | 20 | 0.0 | `1.3085 m` | `0.0146 m` | `437.2846` |
| 95000 | 20 | 0.0 | `1.2491 m` | `0.3212 m` | `370.8003` |

Current best checkpoint:

```text
training/checkpoints/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue/ppo_petoi_bittle_v0_trot_residual_v3_phase_fixed_100k_continue_90000_steps.zip
```

## Conclusion

Longer training substantially improved deterministic forward progress while
preserving full-episode stability. The training curve was not monotonic: PPO
temporarily degraded the gait during early continuation, then recovered and
improved it late in the run.

This is the strongest Petoi simulated locomotion baseline so far. The 90000-step
checkpoint is the best current candidate because it combines strong forward
distance with very low evaluation variance. The final model is still good, but
it is not the best checkpoint.

The next step should record a clean demo video from the 90000-step checkpoint
and add a simple checkpoint-selection workflow so future long runs do not rely
only on the final model.
