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
[ ] Wire Petoi dual-mode Bluetooth module to STM32H747I-DISCO UART8:
    D1/PJ8/UART8_TX -> module RXD, D0/PJ9/UART8_RX <- module TXD,
    +5V -> VCC, GND -> GND.
[ ] Confirm the Bluetooth module is configured for 115200 8N1.
[ ] Verify UART8 smoke traffic before connecting STM32 motion output to Bittle.
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
[ ] For `wkF`-based learned-policy tests, use an entry ramp before the first
    gait frame. A direct jump from stand-up neutral to the first `wkF` reference
    frame has triggered pitch aborts.
[ ] Treat `wkF` scale 0.5, stride 1, residual scale 1.0, 30 ms period, and
    10-step ramp as the current cautious semi-load starting point.
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

2026-06-07 hardware note: the low-amplitude reference was too small compared
with Petoi's official `kwkF` gait. The host runner can now use the official
`wkF` frames as its reference. On the support stand, full `wkF` scale at 25 ms
passed a 348-step run, while 20 ms triggered a pitch abort. Semi-load tests
should start slower and lower, with an entry ramp.

2026-06-07 STM32 handoff note: the tabletop host-side `wkF + RL residual`
baseline passed at `wkF` scale 0.6, stride 1, residual scale 1.0, 22 ms period,
10-step ramp, 348 steps, and `state_every=12`. Result: 360 accepted target
writes, 29 telemetry checks, max roll/pitch about 0.140/0.118 rad, max residual
delta about 0.0437 rad, no abort, final GET_STATE telemetry_valid. Use this as
the first STM32 pipeline comparison target before further speed, direction, or
gait tuning.

Afternoon STM32 pipeline order:

```text
[ ] Wire and verify the Petoi Bluetooth transparent-serial module on UART8.
[ ] Capture or generate host-side baseline observations/actions/targets.
[ ] Run the same observations through STM32 inference.
[ ] Compare STM32 actions against host ONNX actions.
[ ] Compare final clamped target joints against host runner targets.
[ ] Keep Bittle disconnected from STM32 motion output until numerical checks pass.
[ ] Re-run the 348-step tabletop baseline with STM32 in the loop.
```
