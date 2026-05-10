# Petoi Bittle v0 Zero-Action Residual Trot

Date: 2026-05-10

## Goal

Evaluate the residual trot reference inside the Gym environment with zero
actions. This verifies whether the open-loop reference itself moves forward
under the same environment, reward, reset, frame skip, and report format used
by PPO evaluation.

## Tooling

- Added `--zero-action` to `training/scripts/evaluate_policy.py`.
- Added `scripts/evaluate_zero_action.sh` as a convenience wrapper.

Command:

```bash
bash scripts/evaluate_zero_action.sh training/configs/ppo_petoi_bittle_v0_trot_residual_v2.yaml \
  --episodes 10 \
  --output experiments/reports/petoi_bittle_v0_trot_residual_v2_zero_action_eval.json
```

## Finding

The first zero-action Gym evaluation moved backward:

- `distance_x_mean`: `-0.1008 m`
- `fall_rate`: `0.0`

This disagreed with the lower-level open-loop smoke test, which moved forward.
The mismatch came from phase timing. The Gym environment uses `frame_skip=10`,
but residual phase was advancing once per environment step as if each step were
one MuJoCo physics step. As a result, `period_steps=120` became effectively
`1200` physics steps in Gym evaluation.

## Fix

For `residual_trot`, phase now advances by:

```text
frame_skip / gait_period_steps
```

This keeps `gait.period_steps` expressed in MuJoCo physics steps, matching the
open-loop smoke script.

## Corrected Result

After the phase fix, the same zero-action residual trot evaluation produced:

- `reward_mean`: `146.1779`
- `steps_mean`: `1000.0`
- `fall_rate`: `0.0`
- `distance_x_mean`: `0.4288 m`
- `distance_x_std`: `0.1738 m`
- `final_torso_height_mean`: `0.0501 m`
- `final_roll_abs_mean`: `0.0236 rad`
- `final_pitch_abs_mean`: `0.0593 rad`
- Terminations: `timeout: 10`

## Conclusion

The phase-corrected open-loop reference is a valid forward locomotion prior in
the Gym environment. Previous PPO residual results were trained with a too-slow
reference phase and should be treated as diagnostic baselines rather than final
locomotion results.

The next PPO run should train with the corrected phase timing. A smaller
residual action scale may help preserve the forward prior while the policy
learns stabilizing corrections.
