# Bittle Firmware Flash And Bring-Up

This note is the hardware-side gate between simulation/STM32 work and the
Petoi Bittle X V2 body. It assumes the host can reach the robot serial device
from the Ubuntu PC that is physically connected to the robot.

## Current State

The stock OpenCat firmware responded to the first `RL_GET_STATE` frame as an
unknown command. That is expected until the OpenCat RL extension is flashed.

The patched OpenCatEsp32 tree must compile before any flash attempt:

```bash
bash scripts/compile_opencat_rl_get_state.sh
```

The latest known compile result for the patched tree was:

```text
Sketch uses 1295153 bytes (98%) of program storage space.
Global variables use 50712 bytes (15%) of dynamic memory.
```

## Flash Gate

Do not flash until all of these are true:

```text
[ ] The robot is on the floor or a stable stand, away from edges.
[ ] A fast physical power cutoff is ready.
[ ] Factory calibration and basic stock behavior have been recorded.
[ ] The serial device is stable, for example /dev/ttyACM0.
[ ] The patched OpenCatEsp32 firmware compiles locally.
[ ] The operator explicitly approves flashing.
```

Use the preflight script for the software checks:

```bash
bash scripts/bittle_preflight_check.sh --port /dev/ttyACM0 --compile
```

The script is read-only with respect to the robot. It does not flash firmware
and it does not send motion commands.

## Expected First Probe After Flash

After flashing the patched OpenCat firmware, the first command must still be a
read-only telemetry request:

```bash
bash scripts/bittle_bringup_probe.sh --port /dev/ttyACM0 --timeout 1.5 --get-state
```

The expected result is a decoded JSON response with the binary `RL` frame magic,
not a text error such as `Unknown`.

Only continue if:

```text
[ ] The response decodes successfully.
[ ] Roll and pitch are finite and plausible.
[ ] Joint angles are finite and in the expected order.
[ ] Feedback/status bits are understandable.
[ ] Repeating the command produces stable telemetry.
```

## First Motion Gate

Do not send target commands until read-only telemetry is stable. The first
target write is the neutral vector, with the robot physically supported:

```bash
bash scripts/bittle_bringup_probe.sh --port /dev/ttyACM0 --index 0 --allow-motion
```

Stop immediately if any joint binds, chatters, moves in an unexpected direction,
or the robot rotates/falls in a way that does not match the command.

## Escalation Path

The hardware sequence should be:

```text
1. Compile patched OpenCat firmware.
2. Flash only after explicit approval.
3. Run RL_GET_STATE until telemetry is stable.
4. Send neutral target while physically supported.
5. Test one tiny single-joint target at a time.
6. Test low-amplitude scripted gait.
7. Only then connect STM32 policy output to the Bittle command link.
```

The learned policy is intentionally last. First-day hardware work is about
proving the command link, joint order, sign conventions, and safety fallback.

## First Accepted Target

The first accepted `RL_SET_TARGETS` smoke target on the Bittle X V2 was the
generated index `0` neutral target after resetting the bring-up neutral around
the OpenCat hold pose:

```text
target: [71.5, 71.5, 71.5, 71.5, -54.5, -54.5, -54.5, -54.5] degrees
status: command_accepted
feedback after command: [71, 71, 71, 71, -54, -54, -54, -54] degrees
```

The half-degree target values are intentional. OpenCat stores `currentAng[]` as
integers, so exact integer-degree float targets can drift by one degree when
converted back into that cache.

## Next Hardware Session

The Bittle was not available after the 2026-05-23 morning session, so further
motion tests should resume with the single-joint mapping log:

```text
docs/bittle_joint_mapping_log.md
```

The next live motion test should start at index `1`, not at a low-amplitude gait
phase or learned policy.
