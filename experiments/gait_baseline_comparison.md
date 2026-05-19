# Gait Baseline Comparison

Date: 2026-05-19

## Purpose

This experiment checks whether the learned residual policies actually improve
over the current hand-written residual trot reference. The hand gait here is
only the current sinusoidal bring-up gait prior; it is not Petoi/OpenCat's
official tuned gait.

## Compared Variants

```text
A. Hand gait prior
   config: training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue.yaml
   policy_mode: zero_action

B. Deployable RL best
   config: training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue.yaml
   checkpoint: training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue_10000_steps.zip

C. Gait quality v2 30k
   config: training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2.yaml
   checkpoint: training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_steps.zip
```

## Artifacts

Evaluation reports:

```text
experiments/reports/gait_baseline_comparison/A_hand_gait_prior_eval_5ep.json
experiments/reports/gait_baseline_comparison/B_deployable_10k_eval_5ep.json
experiments/reports/gait_baseline_comparison/C_gait_quality_v2_30k_eval_5ep.json
```

Contact/action reports:

```text
experiments/reports/gait_baseline_comparison/A_hand_gait_prior_contact_summary.json
experiments/reports/gait_baseline_comparison/B_deployable_10k_contact_summary.json
experiments/reports/gait_baseline_comparison/C_gait_quality_v2_30k_contact_summary.json
experiments/reports/gait_baseline_comparison/A_hand_gait_prior_action_summary.json
experiments/reports/gait_baseline_comparison/B_deployable_10k_action_summary.json
experiments/reports/gait_baseline_comparison/C_gait_quality_v2_30k_action_summary.json
```

Tracking-camera videos:

```text
assets/videos/gait_compare_A_hand_gait_prior_track.mp4
assets/videos/gait_compare_B_deployable_10k_track.mp4
assets/videos/gait_compare_C_gait_quality_v2_30k_track.mp4
```

All three videos are 20 seconds, 50 fps, and 640x480.

## Summary Table

| Metric | A: hand gait prior | B: deployable 10k | C: gait_quality_v2 30k |
| --- | ---: | ---: | ---: |
| reward_mean | 137.4274 | 562.0475 | 671.9641 |
| distance_x_mean_m | 0.4250 | 1.2671 | 1.4290 |
| distance_x_std_m | 0.2122 | 0.0094 | 0.0102 |
| fall_rate | 0.0 | 0.0 | 0.0 |
| final_roll_abs_mean_rad | 0.0227 | 0.0251 | 0.0270 |
| final_pitch_abs_mean_rad | 0.0612 | 0.0510 | 0.0498 |
| contact_slip_speed_mean_m_s | 0.0960 | 0.1055 | 0.1044 |
| front_contact_duty_factor_mean | 0.6405 | 0.5932 | 0.6095 |
| rear_contact_duty_factor_mean | 0.2527 | 0.2223 | 0.2229 |
| rear_to_front_contact_slip_ratio | 2.4874 | 1.8137 | 1.6867 |
| knee_to_shoulder_action_abs_ratio | n/a | 1.0414 | 0.9927 |
| shoulder_or_hip_target_ptp_rad | 0.1600 | 0.1545 | 0.1683 |
| knee_or_lower_leg_target_ptp_rad | 0.2400 | 0.2701 | 0.2541 |

## Interpretation

The current hand gait prior is a useful scaffold, but it is not competitive as
a controller by itself in this simulation setup. It completes all episodes
without falling, but it travels only `0.425 m` on average and has high
rear/front slip imbalance (`2.49x`).

Both learned residual policies substantially improve forward progress over the
hand gait prior. The deployable 10k policy travels `1.267 m`, while v2_30k
travels `1.429 m`.

The contact picture is more nuanced. The hand gait prior has the lowest absolute
mean contact slip, but it moves much less and has the worst rear/front slip
ratio. The RL policies reduce the relative rear-leg slip imbalance, with v2_30k
best among the three (`1.69x`).

The v2_30k residual action is also more balanced between shoulder/hip and
knee/lower-leg groups (`0.99x`) than the deployable 10k policy (`1.04x`).
However, the final target motion still has larger knee/lower-leg amplitude than
shoulder/hip amplitude because the residual trot reference remains knee-heavy.

## Conclusion

The RL residual policies do provide measurable value over the current
sinusoidal hand gait prior in flat-ground simulation:

```text
1. Much greater forward distance.
2. Similar fall rate.
3. Similar body attitude stability.
4. Better rear/front contact-slip balance.
```

The current best simulation candidate is `gait_quality_v2_30k`, but it should
still be visually reviewed and evaluated over more episodes before replacing the
current deployable ONNX/STM32 artifacts.

This comparison does not prove that RL beats a mature Petoi/OpenCat official
gait. It only proves that RL beats the current simplified sinusoidal gait prior
used as this project's scaffold.
