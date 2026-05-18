# Hardware Bring-Up Checklist

Use this checklist when the Petoi Bittle X V2 hardware arrives. The current
policy is not yet approved for direct hardware deployment; bring-up should start
with static checks and low-amplitude commands.

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
```

## Communication Bring-Up

```text
[ ] Identify the actual command path: serial, BLE bridge, WiFi UDP, or adapter.
[ ] Verify read-only telemetry or state query before sending motion commands.
[ ] Verify command framing with a no-motion or zero-action packet.
[ ] Log every command and response during first tests.
```

## Low-Risk Motion Tests

```text
[ ] Test one joint at a time with very small amplitude.
[ ] Confirm joint direction matches the simulation joint convention.
[ ] Confirm joint limits and emergency fallback.
[ ] Test static stand target while holding the robot.
[ ] Test scripted low-amplitude trot before any learned policy.
```

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

The current deployable candidate moves forward in simulation, but gait quality
needs review. Prior visual observations suggest the robot may rely too much on
lower-leg motion. Treat this as a simulation research issue before hardware
deployment.
