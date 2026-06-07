# Bittle Joint Mapping Log

Use this log during the next Bittle X V2 hardware session. The goal is to map
each generated bring-up vector to the real moving joint before any low-amplitude
gait or learned policy is attempted.

Current availability:

```text
2026-05-23 afternoon: Bittle is not available; a colleague took it back after
the morning bring-up session. Continue with offline preparation only.
2026-05-30: Bittle is available through local Ubuntu over FRP reverse SSH.
Patched OpenCatEsp32 was re-flashed after the robot had been restored to stock
firmware. Joint mapping was continued through a persistent serial session to
avoid repeated ESP32 auto-reset on /dev/ttyACM0 open.
```

Already verified:

```text
[x] patched OpenCatEsp32 firmware flashed
[x] RL_GET_STATE returns telemetry_valid
[x] index 0 neutral target returns command_accepted
[x] index 0 readback remains stable around [71, 71, 71, 71, -54, -54, -54, -54] deg
[x] index 1-16 single-joint mapping verified on hardware
[x] index 17-24 low-amplitude reference phases accepted one frame at a time
```

Before the next motion test:

```text
[ ] Bittle is physically supported or suspended.
[ ] A fast power cutoff is ready.
[ ] Run GET_STATE first.
[ ] Send index 0 neutral once and confirm command_accepted.
[ ] Test only one single-joint index at a time.
```

Useful commands:

```bash
bash scripts/bittle_bringup_probe.sh --plan
bash scripts/bittle_bringup_probe.sh --port /dev/ttyACM0 --timeout 2.0 --get-state
bash scripts/bittle_bringup_probe.sh --port /dev/ttyACM0 --timeout 2.0 --index 0 --allow-motion
```

## Mapping Table

Fill this table while watching the robot. "Expected joint" is the simulation /
protocol name; "observed movement" is what the real Bittle actually does.

The 2026-05-30 mapping used a persistent serial runner so the robot would not
restart before each command. The single-joint tests were temporarily amplified
from the generated +/-2.006 deg to +/-5 deg for easier visual confirmation.

| Index | Expected test | Expected joint | Expected delta | Observed movement | Direction ok | Accepted | Notes |
| ---: | --- | --- | ---: | --- | --- | --- | --- |
| 0 | neutral | all | 0 deg | low/rest-like hold pose | yes | yes | looks low/crouched; used as bring-up baseline |
| 1 | single_joint_0_positive | shrfs_joint | +5 deg | left-front thigh | yes | yes | persistent serial runner |
| 2 | single_joint_0_negative | shrfs_joint | -5 deg | left-front thigh reverse | yes | yes | same joint as index 1 |
| 3 | single_joint_1_positive | shrft_joint | +5 deg | right-front thigh | yes | yes | persistent serial runner |
| 4 | single_joint_1_negative | shrft_joint | -5 deg | right-front thigh reverse | yes | yes | same joint as index 3 |
| 5 | single_joint_2_positive | shrrs_joint | +5 deg | right-rear thigh | yes | yes | persistent serial runner |
| 6 | single_joint_2_negative | shrrs_joint | -5 deg | right-rear thigh reverse | yes | yes | same joint as index 5 |
| 7 | single_joint_3_positive | shrrt_joint | +5 deg | left-rear thigh | yes | yes | re-tested after neutral |
| 8 | single_joint_3_negative | shrrt_joint | -5 deg | left-rear thigh reverse | yes | yes | same joint as index 7 |
| 9 | single_joint_4_positive | shlfs_joint | +5 deg | left-front lower leg | yes | yes | persistent serial runner |
| 10 | single_joint_4_negative | shlfs_joint | -5 deg | left-front lower leg reverse | yes | yes | same joint as index 9 |
| 11 | single_joint_5_positive | shlft_joint | +5 deg | right-front lower leg | yes | yes | re-tested after neutral for clarity |
| 12 | single_joint_5_negative | shlft_joint | -5 deg | right-front lower leg reverse | yes | yes | same joint as index 11 |
| 13 | single_joint_6_positive | shlrs_joint | +5 deg | right-rear lower leg | yes | yes | persistent serial runner |
| 14 | single_joint_6_negative | shlrs_joint | -5 deg | right-rear lower leg reverse | yes | yes | same joint as index 13 |
| 15 | single_joint_7_positive | shlrt_joint | +5 deg | left-rear lower leg | yes | yes | persistent serial runner |
| 16 | single_joint_7_negative | shlrt_joint | -5 deg | left-rear lower leg reverse | yes | yes | same joint as index 15 |

## Low-Amplitude Reference Phase Check

The low-amplitude scripted reference phases were sent one frame at a time after
the single-joint mapping passed. These are not learned-policy commands.

| Index | Expected test | Accepted | Notes |
| ---: | --- | --- | --- |
| 17 | low_amplitude_reference_phase_00 | yes | command_accepted |
| 18 | low_amplitude_reference_phase_01 | yes | command_accepted |
| 19 | low_amplitude_reference_phase_02 | yes | command_accepted |
| 20 | low_amplitude_reference_phase_03 | yes | command_accepted |
| 21 | low_amplitude_reference_phase_04 | yes | command_accepted |
| 22 | low_amplitude_reference_phase_05 | yes | command_accepted |
| 23 | low_amplitude_reference_phase_06 | yes | command_accepted |
| 24 | low_amplitude_reference_phase_07 | yes | command_accepted |

Additional 2026-05-30 checks:

```text
[x] Slow sequence neutral -> 17 -> ... -> 24 -> 17 accepted one frame at a time.
[x] Sequence 17 -> ... -> 24 repeated 3 rounds at the faster interactive-send pace.
[x] Sequence 17 -> ... -> 24 repeated 5 rounds at the same faster pace.
[x] GET_STATE after the 5-round run returned telemetry_valid with roll/pitch
    still near level.
[x] PPO v2 30k policy shadow smoke accepted 8 residual-only samples at 0.5x
    action_scale around the OpenCat neutral pose. Maximum delta from neutral was
    about 1.4 deg; final GET_STATE returned telemetry_valid and near-level
    roll/pitch.
[x] PPO v2 30k policy shadow smoke accepted 8 residual-only samples at 1.0x
    action_scale around the OpenCat neutral pose. Maximum delta from neutral was
    about 2.8 deg; final GET_STATE returned telemetry_valid.
[x] PPO v2 30k hybrid shadow smoke accepted 8 samples using the verified
    low-amplitude OpenCat reference phases plus 0.5x policy residual. Maximum
    delta from neutral was about 2.1 deg; final GET_STATE returned
    telemetry_valid.
[x] PPO v2 30k hybrid shadow smoke accepted 8 samples using the verified
    low-amplitude OpenCat reference phases plus 1.0x policy residual. Maximum
    delta from neutral was about 3.5 deg; final GET_STATE returned
    telemetry_valid with roll/pitch still below the abort gate.
[x] Official OpenCat `kwkF` was used as the gait-amplitude reference. The
    Bittle ESP32 source `InstinctBittleESP.h` defines `wkF` as 116 frames with
    approximately 36-58 deg joint spans, much larger than the earlier
    low-amplitude reference.
[x] Added a `wkF` reference path to the host policy runner. On the support
    stand, `wkF` scale 1.0, stride 1, residual scale 1.0, and 25 ms period ran
    for 348 steps with 350 accepted target writes. Max roll/pitch stayed near
    0.035/0.028 rad.
[x] `wkF` scale 1.0, stride 1, residual scale 1.0 at 20 ms period triggered a
    pitch abort; `kup` restored a normal near-level state. Treat 20 ms as too
    aggressive for the current host-to-ESP32 RL serial loop.
[x] The first semi-load candidate without an entry ramp
    (`wkF` scale 0.5, stride 1, residual scale 0.5, 30 ms period) triggered a
    pitch abort. Adding a 10-step ramp from the stand-up neutral to the first
    `wkF` frame made the same configuration pass.
[x] With the 10-step ramp, `wkF` scale 0.5, stride 1, 30 ms period, residual
    scale 0.5 and 1.0 both passed one 116-step round. The residual 1.0 case
    reached max roll/pitch about 0.149/0.076 rad, so keep this as a cautious
    first semi-load configuration rather than increasing amplitude immediately.
[x] 2026-06-07 tabletop host-side RL baseline for STM32 handoff passed. The
    host policy runner now supports `--state-every` so it can run normal-speed
    `wkF` reference plus ONNX policy residual without blocking on GET_STATE at
    every frame. Baseline command:
    `bash scripts/bittle_policy_runner.sh --port /dev/ttyACM0 --profile stand-up
    --reference-mode wkf --wkf-scale 0.6 --wkf-stride 1 --period 0.022
    --ramp-steps 10 --residual-scale 1.0 --steps 348 --state-every 12
    --roll-pitch-limit 0.30 --allow-motion --summary-only`. Result: 360
    accepted target writes, 29 telemetry checks, max roll/pitch about
    0.140/0.118 rad, max policy action about 0.624, max residual delta about
    0.0437 rad, no abort. Final GET_STATE returned telemetry_valid with
    roll/pitch about -0.036/0.0025 rad.
```

## STM32 Pipeline Handoff Baseline

Use the 2026-06-07 tabletop host-side RL baseline as the first STM32 comparison
target. The goal is to prove the full pipeline before tuning speed, direction,
or step length:

```text
1. Generate or capture host-side observations, ONNX actions, residual deltas,
   wkF reference frames, and final target joints for the baseline above.
2. Run the same observation frames through the STM32 policy inference path.
3. Compare STM32 actions against host ONNX actions before sending motion.
4. Compare STM32 final target joints against host target joints after clamps.
5. Only after the numerical comparison passes, allow STM32-generated targets to
   reach the Bittle RL serial link.
6. Re-run the same 348-step tabletop baseline with STM32 in the loop, retaining
   the 10-step ramp, state checks, and roll/pitch abort gate.
```

Do not treat the host baseline as final gait tuning. The user observed that
speed, step shape, and direction still need later adjustment. For the afternoon
STM32 session, the priority is end-to-end pipeline correctness.

## Stop Conditions

Stop the session immediately if any of these happens:

```text
- wrong joint moves
- direction is opposite to expectation
- servo binds, chatters, or sounds strained
- Bittle rotates/falls unexpectedly
- command response is not command_accepted
- GET_STATE stops decoding cleanly
```

Do not continue to low-amplitude gait phases until the single-joint table is
filled and reviewed.
