# RL Serial Protocol v0

This note defines the first RL-oriented protocol plan between:

- `STM32H747I-DISCO`
- `Petoi Bittle X V2` running `OpenCatEsp32`

The design deliberately keeps the policy contract separate from transport
details. The policy interface remains defined by
`docs/deployable_v0_interface.md`.

## Design Choice

The project adopts a firmware-extension path:

- reuse the open `OpenCatEsp32` firmware base
- add a minimal RL-specific binary interface
- keep existing Petoi serial commands useful for manual debug and fallback

`OpenCatEsp32` already contains:

- IMU handling
- feedback-servo handling
- multi-joint target execution

The RL protocol should therefore be a small adapter layer, not a new robot
control stack.

## Interface Roles

### Formal Runtime Command

```text
RL_STEP
```

One control-cycle exchange:

```text
STM32 -> Bittle:
  sequence_id
  joint_target[8]

Bittle -> STM32:
  sequence_id
  status
  roll
  pitch
  angular_velocity_x/y/z
  joint_feedback[8]
```

`RL_STEP` is the intended closed-loop runtime interface.

### Bring-up Commands

These commands exist to debug the two halves of the closed loop separately.

```text
RL_GET_STATE
```

Response payload:

```text
status
roll
pitch
angular_velocity_x/y/z
joint_feedback[8]
```

Purpose:

- verify IMU telemetry
- verify feedback-servo ordering
- verify units and byte decoding

```text
RL_SET_TARGETS
```

Request payload:

```text
joint_target[8]
```

Purpose:

- verify joint ordering
- verify sign conventions
- verify external periodic target execution

## Why Keep Bring-up Commands

`RL_STEP` is the final closed-loop command, but it mixes telemetry and action
execution in one transaction. During first hardware integration, separate
debug commands reduce ambiguity:

- `RL_GET_STATE` isolates sensor and feedback data
- `RL_SET_TARGETS` isolates actuator command execution
- `RL_STEP` is enabled after both halves are proven independently

## State Mapping to deployable_v0

The Bittle-side telemetry returned by `RL_GET_STATE` or `RL_STEP` fills the
first 13 entries of `deployable_v0`:

| Observation slice | Source |
| --- | --- |
| `0:2` | `roll`, `pitch` |
| `2:5` | `angular_velocity_x/y/z` |
| `5:13` | `joint_feedback[8]` |

STM32 fills the remaining entries locally:

| Observation slice | Source |
| --- | --- |
| `13:21` | `previous_action[8]` |
| `21:23` | `sin(2*pi*phase)`, `cos(2*pi*phase)` |

## Units

The protocol-level semantic units are:

| Field | Unit |
| --- | --- |
| `roll`, `pitch` | `rad` |
| `angular_velocity_x/y/z` | `rad/s` |
| `joint_feedback[8]` | `rad` |
| `joint_target[8]` | `rad` |

If OpenCat internal helpers naturally use degrees, firmware conversion must
occur at the protocol boundary so STM32 sees stable SI-style units.

## Joint Ordering

The protocol uses the same 8-joint order as the trained policy:

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

The following arrays must all share this ordering:

- `joint_feedback[8]`
- `joint_target[8]`
- policy-side `action[8]`

## Packet Direction and Timing

Recommended closed-loop sequencing:

```text
cycle k:
  STM32 owns observation[k]
  STM32 runs policy -> action[k]
  STM32 reconstructs joint_target[k]
  STM32 sends RL_STEP(sequence_id=k, joint_target[k])
  Bittle executes target and replies with telemetry[k+1]

cycle k+1:
  STM32 constructs observation[k+1]
```

This keeps the runtime pipeline simple and gives one explicit exchange per
control cycle.

## Status and Freshness

`RL_STEP` responses should include a compact `status` field. The first version
only needs enough bits to report:

- telemetry valid
- feedback servo data valid
- command accepted
- internal fault / timeout

`sequence_id` allows STM32 to reject stale or out-of-order replies.

## Binary Encoding

The runtime protocol should be binary.

Rationale:

- it is machine-to-machine traffic
- payload shape is fixed
- parsing cost should stay low
- periodic control benefits from bounded packet size

ASCII commands remain useful through existing Petoi facilities for manual
testing, but the RL runtime path should not depend on text parsing.

## OpenCatEsp32 Implementation Notes

Source review on 2026-05-13 confirmed:

- simultaneous indexed joint motion already exists through the current ESP32
  firmware's multi-joint control path
- `j` reports firmware-maintained joint angles, not necessarily physical servo
  feedback
- feedback-servo reads are handled through the existing feedback-servo path
- gyro / IMU handling is present and grouped under gyro-related command logic
- `read_serial()` uses `~` as the terminator for existing uppercase binary
  command payloads, which is unsafe for arbitrary RL frame bytes because
  payload or CRC can legitimately contain `0x7E`

Therefore the RL extension should reuse:

- existing IMU state
- existing servo feedback readers
- existing target-joint execution helpers
- a dedicated length-driven RL binary read path instead of wrapping the entire
  frame under text-like `X...` extension parsing

instead of duplicating them.

## Immediate Firmware Milestones

1. Add `RL_GET_STATE`.
2. Add `RL_SET_TARGETS`.
3. Add `RL_STEP`.
4. Add a host-side Python protocol probe for desktop bring-up.
5. Once hardware arrives, validate units, latency, and packet cadence before
   connecting the STM32 policy loop.
