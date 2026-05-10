# Petoi Bittle v0 stand calibration

This note records the first stand pose sweep for the generated Petoi Bittle MJCF.

## Baseline issue

The initial smoke test only set actuator targets and left joint positions at the
default zero pose. The model loaded, but the body dropped low and produced a high
transient velocity:

```text
final_z      0.023284
min_z        0.010714
max_abs_qvel 20.539641
```

## Calibration method

`tools/calibrate_petoi_stand.py` synchronizes the initial joint positions and
actuator targets, then scans simple symmetric leg targets:

```text
[shoulder, knee, shoulder, knee, shoulder, knee, shoulder, knee]
```

The first scan found `shoulder=0.2`, `knee=1.0`. A finer scan with a wider
actuator control range found a better current baseline:

```text
best_pose=0.200000,1.400000,0.200000,1.400000,0.200000,1.400000,0.200000,1.400000
```

Representative result from the sweep:

```text
shoulder 0.200
knee     1.400
final_z  0.0492
min_z    0.0372
max_tilt 0.0158
xy_drift 0.0004
```

## Current decision

Use the pose above as the first `petoi_bittle_v0` stand baseline. It is not a
final real-robot calibration; it is a stable enough starting point for load,
drop, and stand-task integration.

The generated MJCF now uses `ctrlrange=-2.2 2.2` on the 8 leg position
actuators so this pose is inside the actuator command range.

## First PPO stand baseline

Config:

```text
training/configs/ppo_petoi_bittle_v0_stand.yaml
```

Training:

```text
total_timesteps 20480
ep_len_mean     1000
ep_rew_mean     332
```

Evaluation over 10 deterministic episodes:

```text
fall_rate                     0.0
steps_mean                    1000.0
termination_reason_counts     timeout: 10
reward_mean                   357.8329
final_torso_height_mean       0.0490
final_roll_abs_mean           0.0023
final_pitch_abs_mean          0.0103
distance_x_mean              -0.0010
```

This is the first successful stand policy on the imported Petoi Bittle MJCF.
The export and recording path is captured in
`experiments/petoi_bittle_v0_stand_milestone.md`.
