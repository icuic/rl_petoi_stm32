#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARDUINO_CLI_DIR="${ROOT_DIR}/.tools/arduino-cli"
ARDUINO_CLI="${ARDUINO_CLI_DIR}/arduino-cli"
ESP32_INDEX_URL="https://espressif.github.io/arduino-esp32/package_esp32_index.json"
ESP32_CORE_VERSION="${ESP32_CORE_VERSION:-2.0.12}"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

install_arduino_cli() {
  if [[ -x "${ARDUINO_CLI}" ]]; then
    log "arduino-cli already installed: $(${ARDUINO_CLI} version | head -n 1)"
    return
  fi

  log "Installing arduino-cli into ${ARDUINO_CLI_DIR}"
  mkdir -p "${ARDUINO_CLI_DIR}"
  (
    cd "${ARDUINO_CLI_DIR}"
    curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh \
      | BINDIR="${ARDUINO_CLI_DIR}" sh
  )
}

configure_esp32_core() {
  log "Configuring Arduino CLI package indexes"
  "${ARDUINO_CLI}" config init --overwrite >/dev/null
  "${ARDUINO_CLI}" config add board_manager.additional_urls "${ESP32_INDEX_URL}" >/dev/null
  "${ARDUINO_CLI}" core update-index

  log "Installing ESP32 Arduino core ${ESP32_CORE_VERSION}"
  "${ARDUINO_CLI}" core install "esp32:esp32@${ESP32_CORE_VERSION}"
}

install_libraries() {
  log "Installing Arduino libraries used by the compile check"
  "${ARDUINO_CLI}" lib install ArduinoJson

  log "Installing Python dependency for esptool"
  python3 -m pip install --user pyserial
}

main() {
  install_arduino_cli
  configure_esp32_core
  install_libraries
  log "OpenCat Arduino CLI toolchain is ready"
}

main "$@"
