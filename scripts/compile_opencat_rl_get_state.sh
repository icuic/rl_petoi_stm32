#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARDUINO_CLI="${ROOT_DIR}/.tools/arduino-cli/arduino-cli"
SOURCE_DIR="${ROOT_DIR}/third_party/petoi/OpenCatEsp32-Quadruped-Robot"
TMP_SKETCH_DIR="${TMP_SKETCH_DIR:-/tmp/OpenCatEsp32}"
FQBN="${FQBN:-esp32:esp32:esp32}"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

require_toolchain() {
  if [[ ! -x "${ARDUINO_CLI}" ]]; then
    printf 'arduino-cli is missing. Run:\n  bash %s/scripts/setup_opencat_arduino_cli.sh\n' "${ROOT_DIR}" >&2
    exit 1
  fi
}

require_source_tree() {
  if [[ ! -f "${SOURCE_DIR}/OpenCatEsp32.ino" ]]; then
    printf 'OpenCatEsp32 source tree is missing at %s\n' "${SOURCE_DIR}" >&2
    printf 'Clone it with:\n  git clone https://github.com/PetoiCamp/OpenCatEsp32-Quadruped-Robot.git %s\n' "${SOURCE_DIR}" >&2
    exit 1
  fi
}

prepare_temp_sketch() {
  log "Preparing temporary Arduino sketch at ${TMP_SKETCH_DIR}"
  rm -rf "${TMP_SKETCH_DIR}"
  mkdir -p "${TMP_SKETCH_DIR}"
  cp -a "${SOURCE_DIR}/." "${TMP_SKETCH_DIR}/"

  # Keep the compile check focused on the RL serial path. These optional modules
  # pull external libraries that are unrelated to RL_GET_STATE bring-up.
  sed -i 's/^#define CAMERA[[:space:]].*$/\/\/ #define CAMERA                 \/\/ for Mu Vision camera/' \
    "${TMP_SKETCH_DIR}/OpenCatEsp32.ino"
  sed -i 's/^#define WEB_SERVER[[:space:]].*$/\/\/ #define WEB_SERVER \/\/ toggle web server/' \
    "${TMP_SKETCH_DIR}/src/OpenCat.h"
}

compile_sketch() {
  log "Compiling OpenCatEsp32 with ${FQBN}"
  "${ARDUINO_CLI}" compile --fqbn "${FQBN}" "${TMP_SKETCH_DIR}"
}

main() {
  require_toolchain
  require_source_tree
  prepare_temp_sketch
  compile_sketch
}

main "$@"
