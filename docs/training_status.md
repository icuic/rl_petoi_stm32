# Training Status

Last updated: 2026-05-18

## Current Candidate

The current deployable policy candidate is not the final checkpoint from the
100k continuation run. The best evaluated checkpoint is:

```text
training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue_10000_steps.zip
```

Recommended config:

```text
training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue.yaml
```

The deployed ONNX and STM32 M7 smoke ELF were regenerated from this 10k
checkpoint.

## Evaluation Summary

Checkpoint selection report:

```text
experiments/reports/checkpoint_eval/ranking.json
```

Best 5-episode deterministic evaluation:

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

Best ONNX actor:

```text
models/onnx/petoi_bittle_v0_deployable_v0_best_actor.onnx
```

ONNX parity report:

```text
models/reports/petoi_bittle_v0_deployable_v0_best_actor_onnx.json
```

STM32 policy vector:

```text
firmware/stm32h747_disco/test_vectors/deployable_v0_policy_vector.json
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
sha256: 0cdb372a613850d1c65a7ce832f5ed4df7423c34e6b22a705851b0c1c44925bb
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
- The current policy moves forward in simulation, but visual quality still needs
  review. Prior observations suggest the gait may rely too much on lower-leg
  motion rather than coordinated hip/thigh motion.
- Deployment to hardware should wait until the simulated motion is visually
  acceptable and the action distribution is reviewed.

## Suggested Next Checks

1. Record the selected 10k checkpoint rollout and inspect the gait visually.
2. Run a longer deterministic evaluation, such as 30 or 50 episodes.
3. Compare joint action traces for hip joints versus knee joints.
4. If thigh/hip motion is weak, revise the residual gait prior, action scale,
   or reward terms before hardware deployment.
