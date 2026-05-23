# Project Handoff

Last updated: 2026-05-23

This file is the shortest path for a new Codex session to understand the
project after a cloud server replacement. Read this first, then `README.md`,
`docs/training_status.md`, `docs/bittle_flash_bringup.md`, and
`docs/reverse_ssh_recovery.md`.

## One-Sentence State

The project has a deployable simulation policy candidate, STM32H747 M7 inference
smoke build, and a patched Petoi OpenCat firmware path that has already flashed
successfully onto a Bittle X V2 and accepted the first conservative neutral
`RL_SET_TARGETS` command.

## Current Hardware Topology

```text
cloud server:
  repo path: /home/ubuntu/rl_petoi_stm32
  role: training/build/docs, FRP relay server, Codex workspace

local Ubuntu host:
  LAN SSH: ubuntu@192.168.0.154 -p 58985
  reverse SSH from cloud: ssh -p 60022 ubuntu@127.0.0.1
  repo path: /mnt/sda5/rl_petoi_stm32
  Bittle serial: /dev/ttyACM0

Bittle:
  model: Petoi Bittle X V2
  onboard firmware: patched OpenCatEsp32 with RL serial extension
  current availability: not available after the 2026-05-23 morning session;
    a colleague took the robot back for the afternoon
```

Do not assume the current cloud server is permanent. Its replacement path is in
`docs/reverse_ssh_recovery.md`.

## Simulation / Deployment Candidate

Use this policy candidate unless intentionally doing a comparison:

```text
config:
training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2.yaml

checkpoint:
training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2/ppo_petoi_bittle_v0_trot_residual_deployable_v0_gait_quality_v2_30000_steps.zip

ONNX:
models/onnx/petoi_bittle_v0_gait_quality_v2_30k_actor.onnx

STM32 test vector:
firmware/stm32h747_disco/test_vectors/gait_quality_v2_30k_policy_vector.json

STM32 smoke ELF:
build/stm32h747_m7_inference_smoke/m7_inference_smoke.elf
```

Do not use the v2 `final_model.zip` as the current deployment candidate; it
regressed after the 30k checkpoint. Details are in `docs/training_status.md`.

## Verified Hardware Milestones

Completed:

```text
[x] Cloud can SSH into local Ubuntu through FRP reverse tunnel.
[x] Local Ubuntu sees Bittle serial device at /dev/ttyACM0.
[x] Stock OpenCat firmware rejected RL_GET_STATE as an unknown command.
[x] Patched OpenCatEsp32 compiled with Arduino CLI / esp32:esp32@2.0.12.
[x] Patched OpenCatEsp32 flashed successfully to Bittle X V2.
[x] RL_GET_STATE returns decoded binary RL response with telemetry_valid.
[x] Host serial reader skips OpenCat startup text and scans for RL frame magic.
[x] First conservative neutral RL_SET_TARGETS index 0 returned command_accepted.
```

First accepted target:

```text
target degrees: [71.5, 71.5, 71.5, 71.5, -54.5, -54.5, -54.5, -54.5]
feedback degrees after command: [71, 71, 71, 71, -54, -54, -54, -54]
```

Notes:

```text
- The half-degree neutral is intentional because OpenCat stores currentAng[] as int.
- GET_STATE currently sets telemetry_valid but not feedback_valid.
- Do not treat missing feedback_valid as solved.
- Do not run learned walking yet.
```

## Commands That Are Safe To Re-run

Read-only / dry-run:

```bash
bash scripts/bittle_preflight_check.sh --port /dev/ttyACM0 --compile
bash scripts/bittle_bringup_probe.sh --list
bash scripts/bittle_bringup_probe.sh --index 0
bash scripts/bittle_bringup_probe.sh --port /dev/ttyACM0 --timeout 2.0 --get-state
```

Via cloud-to-local SSH:

```bash
ssh -p 60022 ubuntu@127.0.0.1 'cd /mnt/sda5/rl_petoi_stm32 && bash scripts/bittle_bringup_probe.sh --port /dev/ttyACM0 --timeout 2.0 --get-state'
```

## Commands Requiring Explicit Human Confirmation

Motion commands:

```bash
bash scripts/bittle_bringup_probe.sh --port /dev/ttyACM0 --index 0 --allow-motion
```

Before any `--allow-motion` command, the user should physically support or
suspend the robot and have a fast power cutoff ready. Test only one target at a
time.

Firmware flashing:

```bash
bash scripts/compile_opencat_rl_get_state.sh
.tools/arduino-cli/arduino-cli upload --fqbn esp32:esp32:esp32 --port /dev/ttyACM0 /tmp/OpenCatEsp32
```

Do not flash without explicit user approval.

## New Cloud Server Recovery

The local Ubuntu `frpc` service keeps its token in:

```text
/usr/local/frp/frpc.toml
```

On a new cloud server:

```bash
git clone git@github.com:icuic/rl_petoi_stm32.git
cd rl_petoi_stm32
FRP_TOKEN="token copied from local Ubuntu frpc.toml" \
bash scripts/setup_reverse_ssh_frp.sh server --print-client --start
```

Then on local Ubuntu, edit only `serverAddr` in `/usr/local/frp/frpc.toml` to
the new cloud public IP and restart:

```bash
sudo systemctl restart frpc
```

Verify from the new cloud server:

```bash
ssh -p 60022 ubuntu@127.0.0.1 'hostname && whoami && pwd'
```

## Recommended Next Step

Continue hardware bring-up with single-joint tests from
`protocol/test_vectors/bittle_bringup_v0.json`, starting at index `1`.
Use `docs/bittle_joint_mapping_log.md` as the live observation table.

For each test:

```text
1. User physically supports Bittle.
2. Send exactly one tiny target.
3. User observes which leg/joint moved and whether direction matches expectation.
4. Run GET_STATE.
5. Stop immediately on wrong joint, wrong direction, binding, chatter, or fall risk.
```

Do not connect STM32 policy output or run the learned gait until neutral,
single-joint, and low-amplitude scripted targets are verified on hardware.
