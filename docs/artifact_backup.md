# Artifact Backup

The repository intentionally ignores generated models, checkpoints, logs, videos,
third-party source trees, and build outputs. These files must be backed up
outside the Git working tree before a rented server expires.

## Must Keep

These artifacts are required to resume the current project state without
retraining:

```text
training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0/final_model.zip
training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue_10000_steps.zip
training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_steps.zip
models/onnx/petoi_bittle_v0_gait_quality_v2_30k_actor.onnx
models/reports/petoi_bittle_v0_gait_quality_v2_30k_actor_onnx.json
models/onnx/petoi_bittle_v0_deployable_v0_best_actor.onnx
models/reports/petoi_bittle_v0_deployable_v0_best_actor_onnx.json
firmware/stm32h747_disco/test_vectors/gait_quality_v2_30k_policy_vector.json
experiments/reports/checkpoint_eval/
experiments/reports/action_analysis/
experiments/reports/gait_contact_analysis/
experiments/reports/gait_baseline_comparison/
assets/videos/
experiments/petoi_bittle_v0_gait_diagnosis.md
experiments/gait_baseline_comparison.md
docs/hardware_bringup_checklist.md
```

The gait_quality_v2 30k checkpoint is the current deployable simulation
candidate. Keep its ONNX export, ONNX parity report, policy vector, evaluation
reports, and tracking-camera video together.

The 10k continuation checkpoint is the previous deployable baseline and should
be retained as rollback/comparison evidence. The 100k continuation
`final_model.zip` should be backed up only as experiment evidence, not as the
preferred deployment model.

## Useful To Keep

These artifacts are useful for fast rebuilds and debugging, but can be recreated
from code plus network access:

```text
build/petoi_bittle/
build/stedgeai/generate/
build/stm32h747_m7_inference_smoke/
firmware/stm32h747_disco/App/inference/stedgeai/
firmware/stm32h747_disco/App/cmsis/stm32h7/
third_party/petoi/ros_opencat/
third_party/st/STM32CubeH7/
```

## Optional

These can become large. Keep them when comparing training curves or debugging
regressions:

```text
training/logs/
training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue/*_steps.zip
st_ai_ws/
```

## Restore Checklist

After cloning on a new server:

```bash
bash scripts/setup_env.sh
bash scripts/setup_stedgeai.sh
bash scripts/check_env.sh
bash scripts/build_petoi_mjcf.sh
bash scripts/generate_stedgeai.sh models/onnx/petoi_bittle_v0_gait_quality_v2_30k_actor.onnx
bash scripts/prepare_stm32_cmsis.sh
bash scripts/prepare_stm32_ai_runtime.sh
bash scripts/build_stm32_m7_smoke.sh
```

Then verify:

```bash
bash scripts/select_checkpoint.sh 'experiments/reports/checkpoint_eval/*.json' --min-episodes 5
bash scripts/test_stedgeai_runtime_link.sh
```

## Backup Method

The current project uses milestone archives instead of backing up after every
training command. Create an archive only when a run produces a new best
checkpoint, a new deployable ONNX/ELF, a useful video, or before the server
expires.

Default milestone archive:

```bash
bash scripts/pack_artifacts.sh
```

The script writes to:

```text
artifacts/rl_petoi_artifacts_<utc-time>_<git-sha>.tar.*
```

It includes the current checkpoint, previous baseline checkpoint, ONNX exports,
reports, policy vectors, current rollout video, comparison videos, and status documents. It also
adds `ARTIFACT_MANIFEST.txt` with the git SHA, selected checkpoint, included
paths, and SHA-256 hashes.

For a larger debug archive that includes logs, all checkpoints for the current
runs, and rebuild caches:

```bash
bash scripts/pack_artifacts.sh --include-optional
```

After packing, download the archive to the Windows machine with WindTerm/SFTP
or `scp`.

Longer-term backup destinations can be added later:

```text
Git LFS: good for selected ONNX, reports, and small checkpoints.
Object storage or cloud drive: good for full checkpoint/log/video archives.
rsync/scp to another machine: good for quick server migration.
```

Do not rely on `git clone` alone. The important artifacts above are ignored by
`.gitignore` and will not move with the repository.

## When Not To Back Up

Do not create long-term archives for:

```text
dry-runs
failed or obviously regressed training runs
temporary smoke ONNX models
build outputs that can be recreated from a saved ONNX
```

Evaluate first, then back up only the milestone result.
