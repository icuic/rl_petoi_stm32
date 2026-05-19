# Training Status

Last updated: 2026-05-19

## Current Candidate

The current deployable policy candidate is the 30k checkpoint from the second
gait-quality run:

```text
training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_steps.zip
```

Recommended config:

```text
training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2.yaml
```

It passed visual review, a 30-episode deterministic evaluation, ONNX parity
checks, ST Edge AI generation, policy-vector verification, and STM32H747 M7
smoke ELF build.

30-episode deterministic evaluation:

```text
report: experiments/reports/petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_eval_30ep.json
reward_mean: 666.5192
reward_std: 24.3102
distance_x_mean: 1.4234
distance_x_std: 0.0223
fall_rate: 0.0
termination_reason_counts: timeout=30
```

Visual/reference artifacts:

```text
config: training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2.yaml
checkpoint: training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_steps.zip
video: assets/videos/petoi_bittle_v0_gait_quality_v2_30k_rollout_track_matte.mp4
eval: experiments/reports/petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_eval_5ep.json
eval_30ep: experiments/reports/petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_eval_30ep.json
contact: experiments/reports/gait_contact_analysis/petoi_bittle_v0_gait_quality_v2_30k_5seed_contact_summary.json
action: experiments/reports/action_analysis/petoi_bittle_v0_gait_quality_v2_30k_action_summary.json
```

5-episode deterministic evaluation:

```text
reward_mean: 671.9641
distance_x_mean: 1.4290
distance_x_std: 0.0102
fall_rate: 0.0
termination_reason_counts: timeout=5
```

Contact/action diagnostics:

```text
contact_slip_speed_mean: 0.1044 m/s
front_contact_duty_factor_mean: 0.6095
rear_contact_duty_factor_mean: 0.2229
front_contact_slip_speed_mean: 0.0778 m/s
rear_contact_slip_speed_mean: 0.1311 m/s
rear_to_front_contact_slip_ratio: 1.6867
knee_to_shoulder_action_abs_ratio: 0.9927
```

Compared with the previous deployable candidate, v2_30k improves deterministic
distance (`1.429 m` vs `1.267 m`) and slightly improves rear/front slip ratio
(`1.69x` vs `1.81x`). It does not improve rear contact duty like v1 did. Treat
v2_30k as the deployable simulation candidate for the next hardware bring-up
stage, while retaining the old 10k policy as a rollback baseline.

## Hand Gait Baseline Comparison

The current sinusoidal hand gait prior, deployable 10k policy, and v2_30k
policy were compared under the same flat-ground setup and tracking-camera video
view:

```text
report: experiments/gait_baseline_comparison.md
videos:
  assets/videos/gait_compare_A_hand_gait_prior_track.mp4
  assets/videos/gait_compare_B_deployable_10k_track.mp4
  assets/videos/gait_compare_C_gait_quality_v2_30k_track.mp4
```

Key 5-episode deterministic results:

```text
A hand gait prior:   distance_x_mean=0.4250, fall_rate=0.0, rear/front slip=2.4874
B deployable 10k:    distance_x_mean=1.2671, fall_rate=0.0, rear/front slip=1.8137
C gait_quality_v2:   distance_x_mean=1.4290, fall_rate=0.0, rear/front slip=1.6867
```

This shows that the residual RL policies do improve over the current simplified
sinusoidal gait prior in simulation. It does not prove superiority over a
mature Petoi/OpenCat official gait, which still needs to be tested after
hardware/OpenCat integration.

## Previous Deployable Baseline

The previous deployable candidate was the 10k checkpoint from the 100k
continuation run:

```text
training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue_10000_steps.zip
```

Its checkpoint selection report:

```text
experiments/reports/checkpoint_eval/ranking.json
```

Previous best 5-episode deterministic evaluation:

```text
report: experiments/reports/checkpoint_eval/continue_10000.json
reward_mean: 562.0475
distance_x_mean: 1.2671
distance_x_std: 0.0094
fall_rate: 0.0
steps_mean: 1000.0
```

Important comparison:

```text
baseline final: reward_mean=452.4233, distance_x_mean=0.9914
continue 5k:    reward_mean=499.9625, distance_x_mean=1.1206
continue 10k:   reward_mean=562.0475, distance_x_mean=1.2671
continue 15k:   reward_mean=271.6082, distance_x_std=0.6321
continue final: reward_mean=-95.2478, distance_x_mean=0.1792
```

Do not use this file as the deployment candidate:

```text
training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue/final_model.zip
```

It is the end of the 100k continuation run, but evaluation shows that the policy
regressed badly after the early checkpoints.

## Exported Artifacts

Current ONNX actor:

```text
models/onnx/petoi_bittle_v0_gait_quality_v2_30k_actor.onnx
```

ONNX parity report:

```text
models/reports/petoi_bittle_v0_gait_quality_v2_30k_actor_onnx.json
```

STM32 policy vector:

```text
firmware/stm32h747_disco/test_vectors/gait_quality_v2_30k_policy_vector.json
```

STM32H747 M7 smoke ELF:

```text
build/stm32h747_m7_inference_smoke/m7_inference_smoke.elf
```

Current ELF size:

```text
text: 30616
data: 1072
bss: 5944
sha256: c1e2a67515b6208136d5557f509f3b926c518713838794b0b89e7b029f748136
```

ST Edge AI generation summary for the selected ONNX:

```text
parameters: 6216 float32 items, 24.28 KiB
MACC: 7512
weights: 24864 B
activations: 512 B
estimated total flash: 27794 B
estimated total RAM: 512 B
```

## Notes

- The training metrics alone are misleading for this run. The 100k continuation
  looked promising early, then regressed. Always select via evaluation reports.
- The current policy moves forward in simulation and passed the first visual
  review. Hardware deployment should still start conservatively because the
  rear-leg contact duty is not clearly better than the previous baseline.
- A diagnostic gait-quality run was tested after contact analysis:

```text
config: training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v1.yaml
model: training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v1/final_model.zip
video: assets/videos/petoi_bittle_v0_gait_quality_v1_50k_rollout.mp4
eval: experiments/reports/petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v1_eval_5ep.json
contact: experiments/reports/gait_contact_analysis/petoi_bittle_v0_gait_quality_v1_50k_5seed_contact_summary.json
reward_mean: 151.2325
distance_x_mean: 0.9747
distance_x_std: 0.7302
fall_rate: 0.0
rear_to_front_contact_slip_ratio: 1.4373
```

This v1 run improved rear/front slip balance versus the current candidate
(`1.44x` vs `1.81x`) and increased rear contact duty (`0.289` vs `0.222`), but
it reduced and destabilized forward progress. Treat it as useful evidence for
the next reward/control iteration, not as the new deployable candidate.
- Video recording now uses a tracking camera by default, so the robot remains
  visible after walking forward. Use `--camera fixed` when an old fixed-scene
  comparison is needed.
- The generated Petoi MJCF now uses a checker-grid floor material, so tracking
  camera videos retain visible ground motion cues.

## Suggested Next Checks

1. Keep v2_30k as the default candidate for hardware bring-up.
2. Prepare the Bittle/OpenCat command path and a conservative safety envelope.
3. When hardware arrives, run standing/neutral command checks before any walking
   command.
4. If hardware gait quality is poor, fall back to the 10k baseline and try a v3
   reward variant with explicit rear contact duty shaping.
