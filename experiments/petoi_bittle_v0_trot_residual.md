# Petoi Bittle v0 Trot Residual Baseline

Date: 2026-05-10

## Goal

Start from the stable Petoi stand policy and train a residual PPO policy on top
of a phase-based trot reference. The action no longer commands an absolute joint
target directly; it commands a bounded correction around the open-loop reference.

## Control Setup

- Model: `build/petoi_bittle/petoi_bittle_v0.xml`
- Config: `training/configs/ppo_petoi_bittle_v0_trot_residual.yaml`
- Control mode: `residual_trot`
- Stand pose: `[0.2, 1.4, 0.2, 1.4, 0.2, 1.4, 0.2, 1.4]`
- Reference gait:
  - `period_steps: 120`
  - `shoulder_amplitude: 0.08`
  - `knee_amplitude: 0.12`
- Residual action scale: `0.10 rad` per controlled joint
- Warm start: `training/checkpoints/ppo_petoi_bittle_v0_stand/final_model.zip`

## Training

Command:

```bash
.venv/bin/python training/scripts/train_ppo.py --config training/configs/ppo_petoi_bittle_v0_trot_residual.yaml
```

Result:

- Requested timesteps: `30000`
- Actual timesteps: `30208`
- Training FPS: about `114`
- Wall time: about `262 s`
- Episode length mean: `1000`
- Rollout reward mean increased from about `364` to `366`

## Evaluation

Command:

```bash
MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python training/scripts/evaluate_policy.py --config training/configs/ppo_petoi_bittle_v0_trot_residual.yaml
```

Report: `experiments/reports/petoi_bittle_v0_trot_residual_eval.json`

Summary:

- `reward_mean`: `373.5209`
- `steps_mean`: `1000.0`
- `fall_rate`: `0.0`
- `distance_x_mean`: `-0.0968 m`
- `final_torso_height_mean`: `0.0490 m`
- `final_roll_abs_mean`: `0.0250 rad`
- `final_pitch_abs_mean`: `0.0039 rad`
- Terminations: `timeout: 10`

## Conclusion

The residual trot pipeline is functional and stable: the policy loads from the
stand checkpoint, follows the Petoi MJCF actuator interface, runs full-length
episodes, and remains upright during evaluation.

The first residual reward is still too conservative for locomotion. The policy
learned a stable slight backward motion rather than improving forward progress.
This is consistent with the current reward balance: survival, height, posture,
and action smoothness dominate the relatively weak forward velocity term.

## Next Iteration

- Increase the forward locomotion objective and reduce stabilization terms that
  can be satisfied while standing or drifting backward.
- Add an explicit progress reward based on per-step `x_position` delta instead
  of relying only on instantaneous `qvel[0]`.
- Split lateral drift from longitudinal progress so the policy is penalized for
  sideways motion without penalizing forward travel.
- Record this policy once as a diagnostic video only if needed; it is stable but
  not yet a good demo gait.
