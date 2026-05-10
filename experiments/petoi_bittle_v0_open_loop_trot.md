# Petoi Bittle v0 open-loop trot reference

This experiment introduces a simple phase-based trot reference for the imported
Petoi Bittle MJCF. The goal is not to solve locomotion directly; it is to find a
stable enough gait prior for a later residual RL policy.

## Reference

Module:

```text
sim/envs/gait_reference.py
```

Smoke test:

```text
tools/smoke_petoi_open_loop_gait.py
scripts/smoke_petoi_open_loop_gait.sh
```

Joint order:

```text
shrfs_joint, shrft_joint, shrrs_joint, shrrt_joint,
shlfs_joint, shlft_joint, shlrs_joint, shlrt_joint
```

The reference is a symmetric trot around the calibrated stand pose:

```text
stand_pose = 0.2,1.4,0.2,1.4,0.2,1.4,0.2,1.4
```

Diagonal pairs RF/LR and LF/RR move in opposite phase.

## Scan

The initial scan varied:

```text
period_steps:       80, 120, 160
shoulder_amplitude: 0.08, 0.12, 0.16
knee_amplitude:     0.08, 0.12
```

All tested combinations stayed finite for 1000 MuJoCo steps. Faster 80-step
periods produced larger tilt in several cases. Slower 160-step periods mostly
moved backward. The best positive displacement from this small scan was:

```text
period_steps       120
shoulder_amplitude 0.08
knee_amplitude     0.12
distance_x         0.042319
distance_y         0.020204
final_z            0.050264
min_z              0.038608
final_roll        -0.011123
final_pitch        0.058141
max_tilt           0.068540
max_abs_qvel       5.107850
```

## Conclusion

The gait prior is promising: it produces measurable positive x displacement
without falling. It also produces noticeable lateral drift, so the residual
policy should include a lateral drift penalty and possibly learn small
asymmetric corrections.

The next step should be a residual policy:

```text
target = trot_reference(phase) + residual_action * action_scale
```

The first residual run should keep a small action scale and start from the stand
checkpoint. The reference itself should not be treated as final; it is a scaffold
for exploration.
