# Upstream Patch Preview Status

Current state:

- repo-local protocol / frame-reader / command-adapter / dispatch tests pass
- official `OpenCatEsp32` source has been pulled locally as an ignored reference tree
- `RL_GET_STATE` and `RL_SET_TARGETS` were wired into that real tree at:
  - `src/OpenCat.h`
  - `src/moduleManager.h`
  - `src/reaction.h`
- the current `RL_GET_STATE` response now maps:
  - `roll/pitch` from OpenCat `ypr[]`
  - angular velocity from ICM42670 `gx_real/gy_real/gz_real`, with MPU-only ypr-difference fallback
  - 8 walking joint-angle cache values from `currentAng[DOF - WALKING_DOF ... DOF - 1]`
- the current `RL_SET_TARGETS` path:
  - decodes 8 target joint angles in radians
  - converts them to OpenCat degrees
  - rejects non-finite or out-of-`angleLimit[]` targets
  - returns diagnostic high bits on rejected targets while keeping the response
    as a normal `RL_SET_TARGETS` status frame
  - applies accepted targets through `calibratedPWM(...)`
- the BLE client path now has a binary-safe receive branch:
  - JDY-23 `FFE0/FFE1` notify bytes beginning with `T_RL_FRAME = 'Y'`
    are fed directly into `rlFrameReader`
  - complete frames reuse the same RL response encoder as the USB serial path
  - BLE responses are cached from the notify callback and written later from
    the main loop as raw `RL` frames, not `Y + RL`, because the STM32 transport
    reader waits for the `RL` header
  - BLE responses are split as `20/20/20/4` byte writes for the current
    64-byte `RL_GET_STATE_RESP`; a single 64-byte `writeValue()` did not reach
    STM32 UART8
  - non-RL BLE payloads still fall back to the original text parser
- the corresponding real-tree diff was captured in:
  - `0005-opencat-rl-get-state-real-tree.patch`
- the BLE client binary-frame diff was captured in:
  - `0007-opencat-ble-client-rl-frame.patch`
- the BLE client now has a retry scan patch captured in:
  - `0008-opencat-ble-client-rescan.patch`
  - rationale: the original BLE client only scanned once at startup; if it
    missed JDY-23 `PetoiBLE-3671`, the module kept blinking and STM32 received
    no `RL_GET_STATE` responses
- the BLE client now has a robust loop/token scan patch captured in:
  - `0009-opencat-ble-client-robust-loop-token-scan.patch`
  - rationale: OpenCat only called `readSignal()` while `tQueue` was clear,
    which could starve BLE scan/reply handling during posture tasks; JDY also
    emitted leading NUL notification fragments after STM32 reset, so the BLE RL
    parser now scans each notification for `T_RL_FRAME` instead of requiring it
    at byte 0
- repeatable compile helpers were added:
  - `scripts/setup_opencat_arduino_cli.sh`
  - `scripts/compile_opencat_rl_get_state.sh`
- host-side smoke probe support was added to:
  - `tools/rl_serial_protocol_v0.py`

Verified so far:

- standalone C++ compilation of the new upstream helper files:
  - `rlSerialProtocolV0.cpp`
  - `rlFrameReaderV0.cpp`
- full firmware compile of the patched `RL_GET_STATE` / `RL_SET_TARGETS` bring-up using:
  - `arduino-cli 1.4.1`
  - `esp32:esp32@2.0.12`
  - `ArduinoJson 7.4.3`
  - `pyserial 3.5`
- compile result:
  - flash: `1295153 / 1310720 bytes`
  - RAM: `50712 / 327680 bytes`
- the same compile result was reproduced through:
  - `bash scripts/compile_opencat_rl_get_state.sh`
- hardware smoke on Bittle X V2:
  - stock firmware rejected `RL_GET_STATE` as an unknown command before flashing
  - patched firmware returned stable `telemetry_valid` `RL_GET_STATE`
  - generated index `0` neutral target returned `command_accepted` after the
    bring-up neutral was reset to the accepted OpenCat hold pose
  - 2026-06-07 route-3 BLE client firmware compiled and uploaded to Petoi
    ESP32 on local Ubuntu `/dev/ttyACM1`
  - first binary `RL_GET_STATE` route-3 smoke passed:
    - Petoi log showed 5 `BLE RL frame ready` events
    - Petoi wrote each 64-byte response as `20/20/20/4` BLE chunks
    - STM32 RAM showed `g_uart8_rl_get_state_attempt_count = 5`
    - STM32 RAM showed `g_uart8_rl_get_state_ok_count = 5`
    - STM32 RAM showed `g_uart8_rl_transport_rx_bytes = 0x140` (`5 * 64`)
    - last response began with `52 4c 00 81`, the `RL_GET_STATE_RESP` header
  - 2026-06-13 STM32-resident `gait_quality_v2_30k` deployment smoke passed:
    - Petoi BLE retry firmware was compiled and uploaded to `/dev/ttyACM1`
    - Petoi log showed `PetoiBLE-3671` discovered and connected
    - STM32 M7 ran the ST Edge AI actor and executed 8 guarded low-sine
      residual policy steps over UART8/JDY-23/BLE
    - STM32 RAM showed `deploy_step_attempt_count = 8`
    - STM32 RAM showed `deploy_step_ok_count = 8`
    - STM32 RAM showed `deploy_state_ok_count = 8`
    - STM32 RAM showed `deploy_policy_ok_count = 8`
    - STM32 RAM showed `deploy_abort_reason = 0`
    - STM32 RAM showed `deploy_neutral_end_ok_count = 1`
  - 2026-06-14 route-3 regression recovery:
    - Petoi BLE client firmware with the loop/token-scan fix was compiled and
      uploaded to `/dev/ttyACM1`
    - Petoi log showed `BLE RL token`, `BLE RL frame ready`, and split response
      chunks after STM32 reset despite leading NUL notification fragments
    - STM32 RAM showed initial `g_uart8_rl_get_state_ok_count = 1`
    - STM32 RAM showed neutral `RL_SET_TARGETS` accepted with protocol status
      `0x0004`
    - STM32 RAM showed `deploy_ramp_attempt_count = 10`,
      `deploy_ramp_ok_count = 10`
    - STM32 RAM showed `deploy_step_attempt_count = 6`,
      `deploy_step_ok_count = 6`, `deploy_state_ok_count = 6`,
      `deploy_policy_ok_count = 6`
    - STM32 RAM showed `deploy_abort_reason = 0`
  - 2026-06-14 post-push 65-second route-3 deployment window:
    - after a controlled Petoi reset and confirmed `PetoiBLE-3671` connection,
      STM32 M7 completed the full guarded deployment window
    - STM32 RAM showed `g_uart8_rl_get_state_ok_count = 1`
    - STM32 RAM showed neutral `RL_SET_TARGETS` accepted
    - STM32 RAM showed `deploy_ramp_attempt_count = 10`,
      `deploy_ramp_ok_count = 10`
    - STM32 RAM showed `deploy_step_attempt_count = 12`,
      `deploy_step_ok_count = 12`, `deploy_state_ok_count = 12`,
      `deploy_policy_ok_count = 12`
    - STM32 RAM showed `deploy_abort_reason = 0`
    - STM32 RAM showed `deploy_neutral_end_ok_count = 1`
  - 2026-06-14 fast suspended route-3 deployment window:
    - STM32 M7 fast profile uses 80 deployment steps, 8 ramp steps, official
      gait baseline frame stride 1, and refreshes telemetry every 5 target
      updates
    - STM32 RAM showed `deploy_ramp_attempt_count = 8`,
      `deploy_ramp_ok_count = 8`
    - STM32 RAM showed `deploy_step_attempt_count = 80`,
      `deploy_step_ok_count = 80`, `deploy_state_ok_count = 80`,
      `deploy_policy_ok_count = 80`
    - STM32 RAM showed `deploy_abort_reason = 0`
    - STM32 RAM showed `deploy_neutral_end_ok_count = 1`
  - 2026-06-14 extended fast suspended route-3 deployment window:
    - STM32 M7 fast profile was extended to 120 deployment steps
    - STM32 RAM showed `deploy_ramp_attempt_count = 8`,
      `deploy_ramp_ok_count = 8`
    - STM32 RAM showed `deploy_step_attempt_count = 120`,
      `deploy_step_ok_count = 120`, `deploy_state_ok_count = 120`,
      `deploy_policy_ok_count = 120`
    - STM32 RAM showed `deploy_abort_reason = 0`
    - STM32 RAM showed `deploy_neutral_end_ok_count = 1`

STM32 route-3 smoke status:

- local Ubuntu identifies:
  - `/dev/ttyACM0`: STMicroelectronics STLINK-V3 / STM32H747I-DISCO
  - `/dev/ttyACM1`: USB single serial / Petoi ESP32 upload port
- the current `m7_inference_smoke` diagnostic build sends five read-only
  `RL_GET_STATE` requests over UART8 after the existing safe `d\n` text probe,
  with a 2000 ms response timeout
- local build passes with the ARM toolchain on PATH:
  - `PATH=/opt/gcc-arm-none-eabi-9-2020-q2-update/bin:$PATH bash scripts/build_stm32_m7_smoke.sh`
  - ELF: `build/stm32h747_m7_inference_smoke/m7_inference_smoke.elf`
  - size: `text=32584 data=1072 bss=6936`

Not verified yet:

- hardware IMU axis sign convention against a real Bittle X V2
- whether `currentAng[]` is sufficient for the first real-machine policy run or a separate feedback-servo refresh cache is needed; `kStatusFeedbackValid` is only set when `connectedFeedbackServo[]` indicates feedback has been observed
- closed-loop `RL_SET_TARGETS` over STM32 UART8/JDY-23/BLE

Compile notes:

- the compile check used a temporary sketch directory named `/tmp/OpenCatEsp32`
  so Arduino CLI would accept the `OpenCatEsp32.ino` primary sketch name
- `CAMERA` and `WEB_SERVER` were disabled only in that temporary copy because
  they pull optional external libraries unrelated to the RL serial path

Next technical step:

1. decide whether to keep `T_RL_FRAME = 'Y'`
2. remove or gate the temporary BLE RL Serial diagnostics before final firmware
3. validate conservative `RL_SET_TARGETS` over STM32 UART8/JDY-23/BLE
4. add `RL_STEP` after `GET_STATE` and `SET_TARGETS` pass hardware smoke tests
