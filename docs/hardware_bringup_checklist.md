# Hardware Bring-Up Checklist

Use this checklist when the Petoi Bittle X V2 hardware arrives. The current
policy has passed simulation/export checks, but hardware bring-up must still
start with static checks, telemetry, neutral targets, and low-amplitude
commands before any learned walking loop.

## What This Means

The bring-up path separates the problem into four gates:

```text
1. OpenCat/Bittle command link:
   prove that the host/STM32 can query telemetry and send one 8-joint target
   packet through the OpenCat extension.

2. Safety limits:
   keep first-day joint targets close to neutral, reject stale telemetry, and
   abort on excessive roll/pitch or missing feedback.

3. Static and zero-action tests:
   verify that neutral targets and zero-action policy output do not bind servos
   or move the robot unexpectedly.

4. Low-amplitude scripted motion:
   verify joint order, sign, and timing with tiny deterministic targets before
   enabling the learned policy.
```

The safety source of truth is:

```text
protocol/bittle_bringup_safety_v0.json
```

The generated first-day test vectors are:

```text
protocol/test_vectors/bittle_bringup_v0.json
```

The firmware flash/read-only telemetry gate is:

```text
docs/bittle_flash_bringup.md
```

The reverse SSH recovery note for a replacement cloud server is:

```text
docs/reverse_ssh_recovery.md
```

The live joint-mapping log for the next hardware session is:

```text
docs/bittle_joint_mapping_log.md
```

## Before Power-On

```text
[ ] Confirm battery voltage and charger status.
[ ] Inspect servo horns, leg orientation, loose screws, and cable strain relief.
[ ] Confirm the robot can be physically supported with legs off the ground.
[ ] Prepare a way to cut power quickly.
[ ] Keep the first tests away from table edges.
```

## Software Baseline

```text
[ ] Record OpenCat / BiBoard firmware version.
[ ] Confirm official app or serial console can command basic poses.
[ ] Confirm neutral/stand pose does not bind any servo.
[ ] Save any factory calibration values before changing firmware.
[ ] Run the local software preflight before flashing patched OpenCat firmware.
```

Preflight is read-only with respect to the robot:

```bash
bash scripts/bittle_preflight_check.sh --port /dev/ttyACM0 --compile
```

## Communication Bring-Up

```text
[ ] Identify the actual command path: serial, BLE bridge, WiFi UDP, or adapter.
[ ] Run a read-only state probe before any motion command.
[ ] Verify read-only telemetry or state query before sending motion commands.
[ ] Verify command framing with a no-motion or zero-action packet.
[ ] Log every command and response during first tests.
```

Dry-run the read-only probe frame:

```bash
bash scripts/bittle_bringup_probe.sh --get-state
```

After the real serial path is known, use the same command with a port:

```bash
bash scripts/bittle_bringup_probe.sh --port /dev/ttyUSB0 --get-state
```

Do not send target commands until the read-only probe returns valid telemetry
and feedback status bits.

## Low-Risk Motion Tests

```text
[ ] Regenerate bring-up vectors from the safety config.
[ ] Send neutral target first while holding or suspending the robot.
[ ] Test one joint at a time with very small amplitude.
[ ] Confirm joint direction matches the simulation joint convention.
[ ] Confirm joint limits and emergency fallback.
[ ] Test static stand target while holding the robot.
[ ] Test scripted low-amplitude trot before any learned policy.
```

Generate or refresh vectors:

```bash
bash scripts/generate_bittle_bringup_vectors.sh
```

List the planned neutral, single-joint, and low-amplitude scripted targets:

```bash
bash scripts/bittle_bringup_probe.sh --plan
```

Dry-run the neutral target frame:

```bash
bash scripts/bittle_bringup_probe.sh --index 0
```

When the robot is physically supported and a power cutoff is ready, send the
neutral target. `--allow-motion` is intentionally required for any target write:

```bash
bash scripts/bittle_bringup_probe.sh --port /dev/ttyUSB0 --index 0 --allow-motion
```

Then advance through the single-joint entries from `--list`, one index at a
time. Stop if any joint moves in the wrong direction, binds, chatters, or the
status response does not include command acceptance.

## RL Policy Gate

Do not run the learned policy on hardware until these are true:

```text
[ ] Simulation rollout video is visually acceptable.
[ ] Hip/shoulder and knee/lower-leg action traces have been reviewed.
[ ] Joint mapping from simulation to Bittle servos is verified.
[ ] Safety clamps are active on both STM32 and Bittle/OpenCat sides.
[ ] A zero-action fallback is tested.
[ ] The robot can be stopped without relying on software.
```

## Current Concern

The current v2_30k candidate moves forward in simulation and passed initial
visual review. Its rear-leg contact duty is still not clearly better than the
previous 10k baseline, so first hardware tests should emphasize safety,
mapping correctness, and easy rollback rather than speed.
