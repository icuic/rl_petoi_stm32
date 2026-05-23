# Bittle Joint Mapping Log

Use this log during the next Bittle X V2 hardware session. The goal is to map
each generated bring-up vector to the real moving joint before any low-amplitude
gait or learned policy is attempted.

Current availability:

```text
2026-05-23 afternoon: Bittle is not available; a colleague took it back after
the morning bring-up session. Continue with offline preparation only.
```

Already verified:

```text
[x] patched OpenCatEsp32 firmware flashed
[x] RL_GET_STATE returns telemetry_valid
[x] index 0 neutral target returns command_accepted
[x] index 0 readback remains stable around [71, 71, 71, 71, -54, -54, -54, -54] deg
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

| Index | Expected test | Expected joint | Expected delta | Observed movement | Direction ok | Accepted | Notes |
| ---: | --- | --- | ---: | --- | --- | --- | --- |
| 0 | neutral | all | 0 deg | verified hold pose | yes | yes | first accepted neutral |
| 1 | single_joint_0_positive | shrfs_joint | +2.006 deg |  |  |  |  |
| 2 | single_joint_0_negative | shrfs_joint | -2.006 deg |  |  |  |  |
| 3 | single_joint_1_positive | shrft_joint | +2.006 deg |  |  |  |  |
| 4 | single_joint_1_negative | shrft_joint | -2.006 deg |  |  |  |  |
| 5 | single_joint_2_positive | shrrs_joint | +2.006 deg |  |  |  |  |
| 6 | single_joint_2_negative | shrrs_joint | -2.006 deg |  |  |  |  |
| 7 | single_joint_3_positive | shrrt_joint | +2.006 deg |  |  |  |  |
| 8 | single_joint_3_negative | shrrt_joint | -2.006 deg |  |  |  |  |
| 9 | single_joint_4_positive | shlfs_joint | +2.006 deg |  |  |  |  |
| 10 | single_joint_4_negative | shlfs_joint | -2.006 deg |  |  |  |  |
| 11 | single_joint_5_positive | shlft_joint | +2.006 deg |  |  |  |  |
| 12 | single_joint_5_negative | shlft_joint | -2.006 deg |  |  |  |  |
| 13 | single_joint_6_positive | shlrs_joint | +2.006 deg |  |  |  |  |
| 14 | single_joint_6_negative | shlrs_joint | -2.006 deg |  |  |  |  |
| 15 | single_joint_7_positive | shlrt_joint | +2.006 deg |  |  |  |  |
| 16 | single_joint_7_negative | shlrt_joint | -2.006 deg |  |  |  |  |

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
