# Deployable v0 Interface

This document freezes the first deployment-oriented policy interface for the
Petoi Bittle X V2 project.

## Scope

`deployable_v0` defines:

- the policy observation vector
- the policy action vector
- field ordering, units, and ownership

It does not yet define:

- STM32-to-Bittle packet format
- Bluetooth / WiFi transport
- whether residual reconstruction runs on STM32 or in OpenCat firmware

Those belong to the later communication protocol design.

## Hardware Feasibility

As of 2026-05-13, Petoi staff confirmed that Bittle X V2 can:

- provide `roll`
- provide `pitch`
- provide 3-axis angular velocity
- provide current joint angles for 8 feedback servos
- execute externally supplied 8-joint target angles periodically

This makes the `deployable_v0` policy interface feasible on the target robot.

## Observation Vector

Shape:

```text
observation[23]
```

Layout:

| Index range | Field | Unit | Owner |
| --- | --- | --- | --- |
| `0:2` | `roll`, `pitch` | `rad` | Bittle telemetry |
| `2:5` | `angular_velocity_x/y/z` | `rad/s` | Bittle telemetry |
| `5:13` | 8 current joint angles | `rad` | Bittle telemetry |
| `13:21` | `previous_action[8]` | normalized `[-1, 1]` | STM32 local state |
| `21:23` | `sin(2*pi*phase)`, `cos(2*pi*phase)` | dimensionless | STM32 local state |

The observation layout matches:

```text
DEPLOYABLE_OBSERVATION_LAYOUT
```

in `sim/envs/simple_quadruped_interface.py`.

## Joint Ordering

The current Petoi training configs use this 8-joint order:

```text
0  shrfs_joint
1  shrft_joint
2  shrrs_joint
3  shrrt_joint
4  shlfs_joint
5  shlft_joint
6  shlrs_joint
7  shlrt_joint
```

Both:

- `joint_position[8]`
- `previous_action[8]`
- `action[8]`

must use this same ordering.

## Action Vector

Shape:

```text
action[8]
```

Range:

```text
action[i] in [-1, 1]
```

Meaning:

```text
normalized residual joint action
```

The policy does not directly output absolute servo targets. In the current
training setup:

```text
joint_target = trot_reference(phase) + action * action_scale
```

The deployment system must preserve this interpretation.

## Runtime State Ownership

| State | Source |
| --- | --- |
| `roll`, `pitch` | Bittle X V2 |
| `angular_velocity_x/y/z` | Bittle X V2 |
| `joint_position[8]` | Bittle X V2 feedback servos |
| `previous_action[8]` | STM32 |
| `phase` | STM32 |
| `action[8]` | policy output |

## Open Design Point

The policy contract is fixed, but the execution boundary is still open:

1. STM32 reconstructs `joint_target[8]` and sends absolute joint targets.
2. STM32 sends residual action plus phase, and OpenCat reconstructs targets.

The first protocol design should compare these two options against:

- implementation complexity
- timing determinism
- firmware modification scope
- packet bandwidth
- safety handling

