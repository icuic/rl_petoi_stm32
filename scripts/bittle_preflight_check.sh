#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARDUINO_CLI="${ROOT_DIR}/.tools/arduino-cli/arduino-cli"
OPENCAT_DIR="${ROOT_DIR}/third_party/petoi/OpenCatEsp32-Quadruped-Robot"
PORT=""
RUN_COMPILE=0

usage() {
  cat <<'USAGE'
Usage: bash scripts/bittle_preflight_check.sh [--port /dev/ttyACM0] [--compile]

Read-only preflight for Bittle/OpenCat RL firmware bring-up.

Checks:
  - project files and generated bring-up vectors
  - local Arduino CLI, ESP32 core, and ArduinoJson library
  - patched OpenCatEsp32 source tree markers
  - optional serial device presence and permissions
  - optional patched firmware compile

This script does not flash firmware and does not send robot motion commands.
USAGE
}

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      [[ $# -ge 2 ]] || fail "--port requires a value"
      PORT="$2"
      shift 2
      ;;
    --compile)
      RUN_COMPILE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

cd "${ROOT_DIR}"

log "Checking project bring-up files"
[[ -f "protocol/bittle_bringup_safety_v0.json" ]] || fail "missing protocol/bittle_bringup_safety_v0.json"
[[ -f "protocol/test_vectors/bittle_bringup_v0.json" ]] || fail "missing protocol/test_vectors/bittle_bringup_v0.json; run bash scripts/generate_bittle_bringup_vectors.sh"
[[ -x "scripts/bittle_bringup_probe.sh" ]] || fail "scripts/bittle_bringup_probe.sh is not executable"
[[ -x "scripts/compile_opencat_rl_get_state.sh" ]] || fail "scripts/compile_opencat_rl_get_state.sh is not executable"

log "Checking Arduino CLI and libraries"
[[ -x "${ARDUINO_CLI}" ]] || fail "arduino-cli is missing; run bash scripts/setup_opencat_arduino_cli.sh"
"${ARDUINO_CLI}" version
"${ARDUINO_CLI}" core list | grep -q '^esp32:esp32[[:space:]]' || fail "esp32 Arduino core is missing"
"${ARDUINO_CLI}" lib list | grep -q '^ArduinoJson[[:space:]]' || fail "ArduinoJson is missing; run ${ARDUINO_CLI} lib install ArduinoJson"

log "Checking patched OpenCatEsp32 source tree"
[[ -f "${OPENCAT_DIR}/OpenCatEsp32.ino" ]] || fail "OpenCatEsp32 source tree is missing at ${OPENCAT_DIR}"
[[ -f "${OPENCAT_DIR}/src/rlSerialProtocolV0.cpp" ]] || fail "missing src/rlSerialProtocolV0.cpp in patched OpenCat tree"
[[ -f "${OPENCAT_DIR}/src/rlFrameReaderV0.cpp" ]] || fail "missing src/rlFrameReaderV0.cpp in patched OpenCat tree"
grep -q "T_RL_FRAME" "${OPENCAT_DIR}/src/OpenCat.h" || fail "T_RL_FRAME marker not found in src/OpenCat.h"
grep -q "kMsgGetStateReq" "${OPENCAT_DIR}/src/rlSerialProtocolV0.h" || fail "GET_STATE message marker not found in src/rlSerialProtocolV0.h"
grep -q "kMsgSetTargetsReq" "${OPENCAT_DIR}/src/rlSerialProtocolV0.h" || fail "SET_TARGETS message marker not found in src/rlSerialProtocolV0.h"
grep -q "kMsgGetStateReq" "${OPENCAT_DIR}/src/reaction.h" || fail "GET_STATE dispatch marker not found in src/reaction.h"
grep -q "kMsgSetTargetsReq" "${OPENCAT_DIR}/src/reaction.h" || fail "SET_TARGETS dispatch marker not found in src/reaction.h"

if [[ -n "${PORT}" ]]; then
  log "Checking serial device ${PORT}"
  [[ -e "${PORT}" ]] || fail "serial device does not exist: ${PORT}"
  ls -l "${PORT}"
  [[ -r "${PORT}" && -w "${PORT}" ]] || fail "current user cannot read/write ${PORT}; check dialout group or udev permissions"
  if command -v udevadm >/dev/null 2>&1; then
    udevadm info -q property -n "${PORT}" | grep -E '^(ID_VENDOR|ID_MODEL|ID_SERIAL|DEVLINKS)=' || true
  fi
fi

if [[ "${RUN_COMPILE}" -eq 1 ]]; then
  log "Compiling patched OpenCat firmware"
  bash scripts/compile_opencat_rl_get_state.sh
fi

log "Preflight passed"
printf 'Next safe step after explicit flash approval: run read-only RL_GET_STATE after flashing.\n'
