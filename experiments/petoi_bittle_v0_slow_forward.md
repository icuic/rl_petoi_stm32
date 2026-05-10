# Petoi Bittle v0 slow-forward baseline

This experiment tests whether a small forward reward can move the imported
Petoi Bittle MJCF policy out of the successful stand policy.

## Setup

Config:

```text
training/configs/ppo_petoi_bittle_v0_slow_forward.yaml
```

Warm start:

```text
training/checkpoints/ppo_petoi_bittle_v0_stand/final_model.zip
```

The reward keeps the stand-policy stability terms and adds a small forward
velocity weight:

```text
forward 0.15
```

The run used 30k configured timesteps. PPO collected full rollouts, so the final
training step count was:

```text
total_timesteps 30208
```

## Training behavior

The policy remained stable throughout training:

```text
ep_len_mean 1000
ep_rew_mean 351 to 352 near the end
```

One implementation detail worth recording: because the policy is loaded from an
SB3 checkpoint, the logged learning rate remained `0.0003` from the stand model
despite the slow-forward config setting `0.00025`. If we need strict schedule
control, the training script should override optimizer/schedule state when
loading warm-start checkpoints.

## Evaluation

Evaluation over 10 deterministic episodes:

```text
fall_rate                     0.0
steps_mean                    1000.0
termination_reason_counts     timeout: 10
reward_mean                   365.8183
final_torso_height_mean       0.0491
final_roll_abs_mean           0.0026
final_pitch_abs_mean          0.0109
distance_x_mean              -0.0014
distance_x_std                0.0005
```

## Conclusion

The first slow-forward baseline preserved the stand policy but did not learn
forward locomotion. This is a useful negative result: the imported Petoi model is
stable under PPO fine-tuning, but a small forward reward alone is not enough to
escape the stand local optimum.

The next step should be a gait-prior curriculum:

- add a phase variable that maps to a simple trot reference,
- train residual actions around the stand pose plus reference gait,
- keep the current height, roll, pitch, drift, and action-smoothness penalties,
- begin with very small target velocity and short evaluation windows.
