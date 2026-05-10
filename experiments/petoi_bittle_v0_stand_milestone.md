# Petoi Bittle v0 stand milestone

This milestone turns the imported Petoi Bittle MJCF stand policy into a
demonstrable and exportable artifact.

## Model and policy

- Robot source: Petoi ROS `bittle_description`, converted through the local
  URDF and MJCF build scripts.
- MJCF build: `build/petoi_bittle/petoi_bittle_v0.xml`
- Training config: `training/configs/ppo_petoi_bittle_v0_stand.yaml`
- PPO checkpoint: `training/checkpoints/ppo_petoi_bittle_v0_stand/final_model.zip`
- Stand pose: `0.2,1.4,0.2,1.4,0.2,1.4,0.2,1.4`

The generated build artifacts, videos, checkpoints, reports, and ONNX files are
not tracked by Git. They are reproducible with the commands below.

## Reproduce

```bash
bash scripts/fetch_petoi_model.sh
bash scripts/build_petoi_urdf.sh
bash scripts/build_petoi_mjcf.sh
.venv/bin/python training/scripts/train_ppo.py --config training/configs/ppo_petoi_bittle_v0_stand.yaml
MPLCONFIGDIR=/tmp/matplotlib .venv/bin/python training/scripts/evaluate_policy.py --config training/configs/ppo_petoi_bittle_v0_stand.yaml
bash scripts/record_eval.sh training/configs/ppo_petoi_bittle_v0_stand.yaml --output assets/videos/petoi_bittle_v0_stand.mp4 --max-steps 500 --fps 50
bash scripts/export_policy.sh training/configs/ppo_petoi_bittle_v0_stand.yaml --output models/onnx/petoi_bittle_v0_stand_actor.onnx --report models/reports/petoi_bittle_v0_stand_actor_onnx.json --samples 64
```

## Evaluation

The deterministic PPO policy was evaluated for 10 episodes:

```text
fall_rate                     0.0
steps_mean                    1000.0
termination_reason_counts     timeout: 10
reward_mean                   357.8329
reward_std                    0.0025
distance_x_mean              -0.0010
final_torso_height_mean       0.0490
final_roll_abs_mean           0.0023
final_pitch_abs_mean          0.0103
```

## Video

Recorded artifact:

```text
assets/videos/petoi_bittle_v0_stand.mp4
size: 811K
steps: 500
reward: 178.332
termination_reason: healthy
```

This video is intentionally generated locally rather than committed.

## ONNX export

Recorded artifact:

```text
models/onnx/petoi_bittle_v0_stand_actor.onnx
size: 28K
opset: 17
observation_dim: 29
action_dim: 8
```

Parity check:

```text
torch_vs_onnx_max_abs_diff 4.470348358154297e-08
torch_vs_onnx_mean_abs_diff 7.712515071034431e-09
sb3_vs_onnx_max_abs_diff   5.960464477539063e-08
sb3_vs_onnx_mean_abs_diff  1.0302869668521453e-08
action_min                -0.24181601405143738
action_max                 0.22772476077079773
```

## Next step

Use this stand policy as the warm-start for a slow-forward Petoi curriculum.
Keep the stand rewards as stability constraints and add a small forward velocity
reward only after the policy consistently preserves height and attitude.
