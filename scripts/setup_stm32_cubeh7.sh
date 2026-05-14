#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CUBEH7_DIR="${STM32CUBEH7_DIR:-${ROOT_DIR}/third_party/st/STM32CubeH7}"
CUBEH7_REPO="${STM32CUBEH7_REPO:-https://github.com/STMicroelectronics/STM32CubeH7.git}"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

main() {
  mkdir -p "$(dirname "${CUBEH7_DIR}")"

  if [[ ! -d "${CUBEH7_DIR}/.git" ]]; then
    log "Cloning STM32CubeH7 from ${CUBEH7_REPO}"
    git clone --depth 1 "${CUBEH7_REPO}" "${CUBEH7_DIR}"
  else
    log "STM32CubeH7 already exists: ${CUBEH7_DIR}"
  fi

  log "Initializing CMSIS Device STM32H7 submodule"
  git -C "${CUBEH7_DIR}" submodule update --init --depth 1 Drivers/CMSIS/Device/ST/STM32H7xx

  log "STM32CubeH7 ready"
  git -C "${CUBEH7_DIR}" rev-parse --short HEAD
  git -C "${CUBEH7_DIR}/Drivers/CMSIS/Device/ST/STM32H7xx" rev-parse --short HEAD
}

main "$@"
