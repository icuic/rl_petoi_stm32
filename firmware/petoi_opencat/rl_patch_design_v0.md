# OpenCatEsp32 RL Patch Design v0

This note describes the first firmware patch plan for adding the RL serial
protocol to Petoi's open `OpenCatEsp32` firmware.

## Goal

Implement the protocol defined in:

```text
protocol/rl_serial_protocol_v0.md
```

with three RL-oriented commands:

- `RL_GET_STATE`
- `RL_SET_TARGETS`
- `RL_STEP`

`RL_STEP` is the final closed-loop command. The other two commands exist to
bring up telemetry and actuation separately.

## Upstream Source Baseline

The design was checked against the current official ESP32 firmware tree on
2026-05-13:

```text
PetoiCamp/OpenCatEsp32-Quadruped-Robot
```

Relevant upstream files:

```text
src/OpenCat.h
src/reaction.h
src/espServo.h
```

## Existing OpenCatEsp32 Hooks

### Command Dispatch

`src/OpenCat.h` defines:

```text
T_EXTENSION 'X'
```

`src/reaction.h` already contains:

```text
case T_EXTENSION:
```

Recommendation:

- keep RL extensions under `T_EXTENSION`
- reserve a dedicated subcommand namespace such as:
  - `XRG` for `RL_GET_STATE`
  - `XRT` for `RL_SET_TARGETS`
  - `XRS` for `RL_STEP`

The exact subcommand labels can change later. The key design point is that RL
support should live under the existing extension command family instead of
consuming unrelated top-level Petoi tokens.

## State Collection Plan

### IMU Fields

The protocol needs:

- roll
- pitch
- angular velocity x/y/z

OpenCatEsp32 already keeps IMU state and owns gyro update / print logic through
the gyro command family in `reaction.h`.

Implementation plan:

1. factor out a helper that reads the latest in-memory IMU state without
   printing text
2. convert values into the protocol semantic units:
   - `rad`
   - `rad/s`
3. write them directly into the RL response payload

Do not parse text output from existing print helpers.

### Feedback Servo Fields

The protocol needs:

```text
joint_feedback[8]
```

`src/espServo.h` already implements:

```text
servoFeedback(...)
```

That function currently:

- reads physical servo feedback
- converts the measured pulse to an angle
- updates `currentAng`
- prints text output

Implementation plan:

1. factor the measurement logic into a helper that can fill an array without
   printing
2. preserve the existing `servoFeedback()` text behavior by letting it call the
   helper internally
3. make RL telemetry use the non-printing helper

This avoids:

- duplicating conversion logic
- treating `j/currentAng` as equivalent to measured feedback
- scraping formatted strings inside firmware

## Target Execution Plan

The protocol needs:

```text
joint_target[8]
```

OpenCatEsp32 already supports multi-joint target execution through the same
logic used by binary indexed simultaneous control.

Implementation plan:

1. decode the 8 protocol targets in radians
2. convert to OpenCat internal angle units if needed
3. map policy joint order to the OpenCat joint indices
4. populate a local `targetFrame`
5. reuse the same actuator execution path that ultimately calls:
   - `transform(...)`
   - `skill->convertTargetToPosture(...)`

The RL path should not introduce a second actuator stack.

## Joint Order Mapping

The policy contract uses:

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

Patch implementation must define one explicit conversion table:

```text
policy_joint_index -> OpenCat joint index
```

That table should be centralized in the RL patch code and reused by:

- telemetry packing
- target unpacking
- test helpers

## Proposed Firmware Helpers

Add a small RL-specific helper layer, for example:

```text
src/rlProtocol.h
src/rlProtocol.cpp
```

or a single header if the upstream style favors headers.

Suggested responsibilities:

- frame header validation
- CRC16-CCITT
- fixed-payload parsing
- status-bit construction
- RL telemetry packing
- RL target dispatch

Keep `reaction.h` limited to command dispatch and high-level orchestration.

## Command Behavior

### `RL_GET_STATE`

1. validate binary frame
2. read latest IMU values
3. read feedback joint angles
4. set status bits
5. send binary state response

### `RL_SET_TARGETS`

1. validate binary frame
2. decode 8 joint targets
3. apply target execution path
4. return status response

### `RL_STEP`

1. validate binary frame
2. decode 8 joint targets
3. execute targets
4. collect fresh telemetry
5. echo `sequence_id`
6. return combined state response

## Status Bits

Reuse the host protocol values:

| Bit | Meaning |
| ---: | --- |
| `0` | telemetry valid |
| `1` | feedback servo data valid |
| `2` | command accepted |
| `3` | internal fault / timeout |

The first implementation should set bits conservatively. For example:

- missing servo feedback clears bit `1`
- malformed CRC clears acceptance and should return an error path
- target decode failure should not move actuators

## Test Strategy

Use the shared host-side vectors from:

```text
protocol/test_vectors/rl_serial_protocol_v0.json
```

The first firmware patch should be considered correct only when it can:

1. accept the reference `RL_STEP_REQ` frame
2. decode the eight target floats correctly
3. emit a binary response with:
   - matching `sequence_id`
   - valid CRC
   - expected message type
4. interoperate with:

```text
tools/rl_serial_protocol_v0.py
```

## Implementation Order

1. Add binary frame parser / serializer.
2. Add `RL_GET_STATE` with stub telemetry values if hardware is absent.
3. Connect real IMU and feedback-servo sources.
4. Add `RL_SET_TARGETS`.
5. Add `RL_STEP`.
6. Run host-side probe against firmware over serial.

## Open Questions Before Real Patch

1. Exact top-level extension subcommand bytes under `T_EXTENSION`.
2. Whether RL binary frames should be carried entirely after `X...` command
   parsing or use a new dedicated parser branch earlier in the serial pipeline.
3. The exact OpenCat joint-index table for the eight controlled leg joints.
4. Whether executing targets should disable or bypass any balancing behavior
   during RL control mode.

