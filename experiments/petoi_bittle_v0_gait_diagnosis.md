# Petoi Bittle v0 Gait Diagnosis

Date: 2026-05-18

## Scope

This note diagnoses the current deployable policy candidate before hardware
deployment. The goal is to check whether the gait is mechanically plausible,
especially whether the learned motion depends too much on lower-leg/knee motion
instead of coordinated shoulder/hip motion.

Policy candidate:

```text
training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue_10000_steps.zip
```

Config:

```text
training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue.yaml
```

Rollout video:

```text
assets/videos/petoi_bittle_v0_deployable_v0_10k_rollout.mp4
```

Action analysis:

```text
experiments/reports/action_analysis/petoi_bittle_v0_deployable_v0_10k_action_summary.json
experiments/reports/action_analysis/petoi_bittle_v0_deployable_v0_10k_actions.png
experiments/reports/action_analysis/petoi_bittle_v0_deployable_v0_10k_targets.png
experiments/reports/action_analysis/petoi_bittle_v0_deployable_v0_10k_reference.png
experiments/reports/action_analysis/petoi_bittle_v0_deployable_v0_10k_group_comparison.png
```

Contact/clearance analysis:

```text
experiments/reports/gait_contact_analysis/petoi_bittle_v0_deployable_v0_10k_contact_summary.json
experiments/reports/gait_contact_analysis/petoi_bittle_v0_deployable_v0_10k_5seed_contact_summary.json
experiments/reports/gait_contact_analysis/petoi_bittle_v0_deployable_v0_10k_foot_heights.png
experiments/reports/gait_contact_analysis/petoi_bittle_v0_deployable_v0_10k_foot_xy_speed.png
experiments/reports/gait_contact_analysis/petoi_bittle_v0_deployable_v0_10k_contact_raster.png
experiments/reports/gait_contact_analysis/petoi_bittle_v0_deployable_v0_10k_base_attitude.png
```

## Rollout Metrics

Single deterministic rollout used for action analysis:

```text
steps: 1000
reward: 571.268
distance_x: 1.265 m
termination_reason: timeout
```

Best checkpoint selection remains based on multi-episode evaluation:

```text
reward_mean: 562.0475
distance_x_mean: 1.2671 m
fall_rate: 0.0
episodes: 5
```

## Action Summary

Grouped action statistics:

```text
shoulder_or_hip action_abs_mean: 0.1402
knee_or_lower_leg action_abs_mean: 0.1460
knee_to_shoulder_action_abs_ratio: 1.0414
```

Residual action in radians is small because the deployable action scale is
`0.06 rad` on all joints:

```text
shoulder_or_hip residual_rad_abs_mean: 0.0084 rad
knee_or_lower_leg residual_rad_abs_mean: 0.0088 rad
```

Final target motion is larger on knee/lower-leg joints:

```text
shoulder_or_hip target_rad_peak_to_peak: 0.1545 rad
knee_or_lower_leg target_rad_peak_to_peak: 0.2701 rad
```

This is mostly explained by the residual trot reference, not by an extreme
learned residual imbalance. The current reference gait uses:

```text
shoulder_amplitude: 0.08 rad
knee_amplitude: 0.12 rad
action_scale: 0.06 rad on all 8 joints
```

## Per-Joint Snapshot

```text
shrfs_joint action_abs_mean=0.0792 target_ptp=0.1747 reference_ptp=0.1600
shrft_joint action_abs_mean=0.1717 target_ptp=0.2744 reference_ptp=0.2400
shrrs_joint action_abs_mean=0.2184 target_ptp=0.1341 reference_ptp=0.1600
shrrt_joint action_abs_mean=0.0925 target_ptp=0.2575 reference_ptp=0.2400
shlfs_joint action_abs_mean=0.0855 target_ptp=0.1711 reference_ptp=0.1600
shlft_joint action_abs_mean=0.1999 target_ptp=0.2870 reference_ptp=0.2400
shlrs_joint action_abs_mean=0.1776 target_ptp=0.1382 reference_ptp=0.1600
shlrt_joint action_abs_mean=0.1198 target_ptp=0.2613 reference_ptp=0.2400
```

## Interpretation

The policy residual does not show a severe knee-only bias by normalized action
magnitude. However, the final commanded gait still has visibly larger lower-leg
motion because the hand-authored residual trot reference gives knee joints
higher amplitude than shoulder/hip joints.

If the rollout video still looks like it is "scooting" using mostly lower legs,
the likely cause is the combined controller design:

```text
reference gait knee amplitude > shoulder amplitude
small residual action scale
strong progress reward
no explicit penalty for foot dragging or weak thigh participation
```

## Contact And Slip Diagnostics

Contact analysis uses the four `shank_*` collision geoms as approximate foot/end
effector proxies. This is not a perfect foot model, but it is enough to detect
large contact timing asymmetry, body attitude issues, and obvious sliding.

Aggregate rollout diagnostics:

```text
contact_duty_factor_mean: 0.4057
contact_duty_factor_std: 0.1858
contact_slip_speed_mean: 0.1059 m/s
swing_height_mean: 0.0375 m
base_height_mean: 0.0503 m
base_roll_abs_mean: 0.0273 rad
base_pitch_abs_mean: 0.0306 rad
base_roll_abs_max: 0.0540 rad
base_pitch_abs_max: 0.0691 rad
```

Per-leg summary:

```text
right_front duty=0.595 slip_mean=0.0758 m/s slip_p95=0.1157 m/s
right_rear  duty=0.222 slip_mean=0.1424 m/s slip_p95=0.3593 m/s
left_front  duty=0.588 slip_mean=0.0732 m/s slip_p95=0.1045 m/s
left_rear   duty=0.218 slip_mean=0.1324 m/s slip_p95=0.3103 m/s
```

Interpretation:

```text
1. Body attitude is stable; roll/pitch magnitudes are small.
2. Front legs spend much more time in contact than rear legs.
3. Rear-leg contact slip is noticeably higher than front-leg contact slip.
4. This suggests the policy may be using a front-heavy support pattern while
   the rear legs contribute with more sliding or fast contact motion.
```

This is a better grounded concern than simply saying the gait "looks odd".
The next reward/control iteration should consider foot slip, contact timing,
and rear-leg contribution before hardware deployment.

Multi-seed confirmation:

```text
rollouts: 5 deterministic
seeds: 37, 38, 39, 40, 41
termination_reasons: timeout=5
reward_mean: 562.0475 +/- 8.0948
distance_x_mean: 1.2671 +/- 0.0094 m
contact_duty_factor_mean: 0.4077 +/- 0.0033
contact_slip_speed_mean: 0.1055 +/- 0.0007 m/s
swing_height_mean: 0.0375 +/- 0.0000 m
base_roll_abs_mean: 0.0273 +/- 0.0000 rad
base_pitch_abs_mean: 0.0307 +/- 0.0001 rad
front_contact_duty_factor_mean: 0.5932 +/- 0.0064
rear_contact_duty_factor_mean: 0.2223 +/- 0.0013
front_contact_slip_speed_mean: 0.0750 +/- 0.0004 m/s
rear_contact_slip_speed_mean: 0.1361 +/- 0.0016 m/s
rear_to_front_contact_slip_ratio: 1.8137 +/- 0.0274
```

The front-heavy support pattern and higher rear-leg contact slip are stable
across these seeds. The strongest next experiment is therefore not another
blind continuation run; it is a targeted gait-quality variant that changes the
reference/control balance and adds explicit pressure against dragging/sliding.

## Gait Quality v1 Follow-Up

The first targeted follow-up changed the residual gait prior and enabled contact
quality terms:

```text
config: training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v1.yaml
init_model: current 10k best checkpoint
total_timesteps: 50000
shoulder_amplitude: 0.10 rad
knee_amplitude: 0.10 rad
shoulder/hip action_scale: 0.08 rad
knee/lower-leg action_scale: 0.05 rad
contact_slip: 0.15
rear_contact_slip: 0.10
front_contact_duty: 0.015
rear_contact_bonus: 0.01
```

Training completed and produced:

```text
model: training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v1/final_model.zip
video: assets/videos/petoi_bittle_v0_gait_quality_v1_50k_rollout.mp4
eval: experiments/reports/petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v1_eval_5ep.json
contact: experiments/reports/gait_contact_analysis/petoi_bittle_v0_gait_quality_v1_50k_5seed_contact_summary.json
```

Evaluation result:

```text
reward_mean: 151.2325 +/- 515.0957
distance_x_mean: 0.9747 +/- 0.7302 m
fall_rate: 0.0
termination_reasons: timeout=5
```

Contact result:

```text
contact_slip_speed_mean: 0.1020 +/- 0.0022 m/s
front_contact_duty_factor_mean: 0.6039 +/- 0.0070
rear_contact_duty_factor_mean: 0.2890 +/- 0.0043
front_contact_slip_speed_mean: 0.0837 +/- 0.0009 m/s
rear_contact_slip_speed_mean: 0.1202 +/- 0.0049 m/s
rear_to_front_contact_slip_ratio: 1.4373 +/- 0.0693
```

Interpretation:

```text
1. v1 moved the contact diagnostics in the intended direction:
   rear/front slip ratio improved from 1.81x to 1.44x.
2. Rear contact duty increased from 0.222 to 0.289.
3. Forward progress became worse and less stable:
   distance_x_mean dropped from 1.267 m to 0.975 m.
4. v1 is therefore not a new best policy, but it proves the added diagnostics
   and reward knobs can influence the gait.
```

The next variant should keep the shoulder/action-scale change modest, reduce or
remove the rear contact bonus, and preserve stronger progress pressure. The goal
is to retain the lower rear slip without sacrificing deterministic distance.

## Recommended Next Experiments

Before hardware deployment, try one or more simulation-only variants:

```text
1. Increase shoulder_amplitude relative to knee_amplitude.
2. Give shoulder/hip joints a larger action_scale than knee joints.
3. Add a reward or diagnostic for hip/shoulder target amplitude.
4. Add foot contact or foot clearance terms if contact data is available.
5. Record side-view videos for each candidate, not only numeric evaluation.
6. Penalize high contact slip or asymmetric contact duty.
```

Deployment should wait until the gait is visually acceptable, because the
current numeric reward can improve even when the motion quality is not the gait
we want on the real Bittle.
