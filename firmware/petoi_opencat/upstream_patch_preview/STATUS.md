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
  - applies accepted targets through `calibratedPWM(...)`
- the corresponding real-tree diff was captured in:
  - `0005-opencat-rl-get-state-real-tree.patch`
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
  - flash: `1295053 / 1310720 bytes`
  - RAM: `50712 / 327680 bytes`
- the same compile result was reproduced through:
  - `bash scripts/compile_opencat_rl_get_state.sh`

Not verified yet:

- hardware IMU axis sign convention against a real Bittle X V2
- whether `currentAng[]` is sufficient for the first real-machine policy run or a separate feedback-servo refresh cache is needed; `kStatusFeedbackValid` is only set when `connectedFeedbackServo[]` indicates feedback has been observed
- Bluetooth / Serial2 reply routing

Compile notes:

- the compile check used a temporary sketch directory named `/tmp/OpenCatEsp32`
  so Arduino CLI would accept the `OpenCatEsp32.ino` primary sketch name
- `CAMERA` and `WEB_SERVER` were disabled only in that temporary copy because
  they pull optional external libraries unrelated to the RL serial path

Next technical step:

1. decide whether to keep `T_RL_FRAME = 'Y'`
2. validate reply routing over the actual USB/BLE/WiFi path
3. add `RL_STEP` after `GET_STATE` and `SET_TARGETS` pass hardware smoke tests
