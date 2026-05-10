# Control Interface v0

This document defines the first policy-control interface that connects the current MuJoCo/SB3 policy to the future STM32 and Petoi/OpenCat integration work.

The v0 interface intentionally mirrors the minimal quadruped environment. It is not yet a final Bittle hardware protocol. Its purpose is to freeze the first deployable policy contract: observation layout, action layout, units, timing assumptions, safety limits, and the mapping from normalized policy output to joint targets.

## Scope

```text
state estimator / simulator -> observation[29] -> policy -> action[8] -> joint target mapper -> robot command
```

Current policy artifact:

- Source: SB3 PPO `MlpPolicy`
- Export: deterministic actor ONNX
- ONNX input: `observation`, shape `[batch, 29]`, `float32`
- ONNX output: `action`, shape `[batch, 8]`, `float32`
- Action range: clamped to `[-1, 1]`

## Timing

| Item | v0 Value | Notes |
| --- | ---: | --- |
| Policy tick | 50 Hz | Matches `SimpleQuadrupedEnv.metadata["render_fps"]` and `phase += 0.02` per policy step. |
| Policy period | 20 ms | STM32 side should treat this as the first real-time scheduling target. |
| Low-level servo update | TBD | May be equal to or faster than the policy tick after Petoi/OpenCat integration. |
| Watchdog timeout | 100 ms | If policy output or wireless link stalls for 5 policy ticks, enter safe behavior. |

## Observation Layout

All values are `float32`, little-endian when serialized for test vectors or telemetry.

| Index | Name | Unit | Source | Notes |
| ---: | --- | --- | --- | --- |
| 0 | `torso_height_m` | m | simulator / estimator | Torso height above ground. |
| 1 | `torso_quat_w` | unitless | simulator / IMU estimator | Quaternion scalar component. |
| 2 | `torso_quat_x` | unitless | simulator / IMU estimator | Quaternion x component. |
| 3 | `torso_quat_y` | unitless | simulator / IMU estimator | Quaternion y component. |
| 4 | `torso_quat_z` | unitless | simulator / IMU estimator | Quaternion z component. |
| 5 | `base_vx` | m/s | simulator / estimator | Base linear velocity x. On hardware this may be estimated or replaced later. |
| 6 | `base_vy` | m/s | simulator / estimator | Base linear velocity y. |
| 7 | `base_vz` | m/s | simulator / estimator | Base linear velocity z. |
| 8 | `base_wx` | rad/s | simulator / IMU | Base angular velocity x. |
| 9 | `base_wy` | rad/s | simulator / IMU | Base angular velocity y. |
| 10 | `base_wz` | rad/s | simulator / IMU | Base angular velocity z. |
| 11 | `front_left_hip_pos` | rad | joint sensor / command estimate | Current joint angle. |
| 12 | `front_left_knee_pos` | rad | joint sensor / command estimate | Current joint angle. |
| 13 | `front_right_hip_pos` | rad | joint sensor / command estimate | Current joint angle. |
| 14 | `front_right_knee_pos` | rad | joint sensor / command estimate | Current joint angle. |
| 15 | `rear_left_hip_pos` | rad | joint sensor / command estimate | Current joint angle. |
| 16 | `rear_left_knee_pos` | rad | joint sensor / command estimate | Current joint angle. |
| 17 | `rear_right_hip_pos` | rad | joint sensor / command estimate | Current joint angle. |
| 18 | `rear_right_knee_pos` | rad | joint sensor / command estimate | Current joint angle. |
| 19 | `front_left_hip_vel` | rad/s | joint sensor / finite difference | Current joint velocity. |
| 20 | `front_left_knee_vel` | rad/s | joint sensor / finite difference | Current joint velocity. |
| 21 | `front_right_hip_vel` | rad/s | joint sensor / finite difference | Current joint velocity. |
| 22 | `front_right_knee_vel` | rad/s | joint sensor / finite difference | Current joint velocity. |
| 23 | `rear_left_hip_vel` | rad/s | joint sensor / finite difference | Current joint velocity. |
| 24 | `rear_left_knee_vel` | rad/s | joint sensor / finite difference | Current joint velocity. |
| 25 | `rear_right_hip_vel` | rad/s | joint sensor / finite difference | Current joint velocity. |
| 26 | `rear_right_knee_vel` | rad/s | joint sensor / finite difference | Current joint velocity. |
| 27 | `phase_sin` | unitless | gait phase generator | `sin(2*pi*phase)`. |
| 28 | `phase_cos` | unitless | gait phase generator | `cos(2*pi*phase)`. |

## Action Layout

The policy outputs normalized joint target commands. Each element is clipped to `[-1, 1]` before mapping to radians.

| Index | Joint | Neutral rad | Scale rad | Target Mapping |
| ---: | --- | ---: | ---: | --- |
| 0 | `front_left_hip` | 0.15 | 0.55 | `neutral + action[0] * scale` |
| 1 | `front_left_knee` | -0.75 | 0.55 | `neutral + action[1] * scale` |
| 2 | `front_right_hip` | 0.15 | 0.55 | `neutral + action[2] * scale` |
| 3 | `front_right_knee` | -0.75 | 0.55 | `neutral + action[3] * scale` |
| 4 | `rear_left_hip` | -0.15 | 0.55 | `neutral + action[4] * scale` |
| 5 | `rear_left_knee` | -0.75 | 0.55 | `neutral + action[5] * scale` |
| 6 | `rear_right_hip` | -0.15 | 0.55 | `neutral + action[6] * scale` |
| 7 | `rear_right_knee` | -0.75 | 0.55 | `neutral + action[7] * scale` |

Reference implementation:

```python
joint_target_rad = neutral_pose_rad + clip(action, -1.0, 1.0) * action_scale_rad
```

The source of truth in code is `sim/envs/simple_quadruped_interface.py`.

## Safety Rules

STM32 should enforce these rules before sending commands to Bittle:

- Reject or clamp any non-finite policy output.
- Clamp normalized actions to `[-1, 1]`.
- Clamp mapped joint targets to the final hardware joint limits once measured.
- Apply a per-joint target slew-rate limit before transmission.
- Enter safe pose if inference, observation update, or wireless command transmission stalls longer than `100 ms`.
- Enter safe pose if IMU roll or pitch exceeds the hardware fall threshold.

## Petoi/OpenCat Mapping Notes

The current joint names are simulator names, not final OpenCat servo IDs. The next hardware-facing revision should add a mapping table:

```text
policy_joint_index -> bittle_leg -> bittle_servo_id -> sign -> zero_offset_deg -> min_deg -> max_deg
```

Until Bittle is available, this document keeps all policy-side units in radians and normalized action space. The Petoi adapter should own conversion to degrees, servo ticks, command packets, or OpenCat internal units.

## Versioning

- Interface version: `control_interface_v0`
- Compatible model family: `simple_quadruped_actor`
- Breaking changes require a new document version and new test vectors.
- Examples of breaking changes: observation index reorder, action index reorder, unit change, different phase representation, or different action scale.

## Test Vector

See `protocol/test_vectors/control_interface_v0.json` for a neutral-pose smoke vector. It is intentionally simple and should remain stable across refactors.
