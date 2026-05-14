#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CUBEH7_DIR="${STM32CUBEH7_DIR:-${ROOT_DIR}/third_party/st/STM32CubeH7}"
DEST_DIR="${STM32_CMSIS_DIR:-${ROOT_DIR}/firmware/stm32h747_disco/App/cmsis/stm32h7}"

STARTUP_SRC="${CUBEH7_DIR}/Projects/STM32H747I-DISCO/Templates_LL/STM32CubeIDE/CM7/Example/User/Startup/startup_stm32h747xihx.s"
SYSTEM_SRC="${CUBEH7_DIR}/Projects/STM32H747I-DISCO/Templates_LL/Common/Src/system_stm32h7xx.c"
DEVICE_INC="${CUBEH7_DIR}/Drivers/CMSIS/Device/ST/STM32H7xx/Include"
CORE_INC="${CUBEH7_DIR}/Drivers/CMSIS/Core/Include"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "Missing required file: $1" >&2
    echo "Fetch STM32CubeH7 first:" >&2
    echo "  bash scripts/setup_stm32_cubeh7.sh" >&2
    exit 1
  fi
}

main() {
  require_file "${STARTUP_SRC}"
  require_file "${SYSTEM_SRC}"
  require_file "${DEVICE_INC}/stm32h747xx.h"
  require_file "${DEVICE_INC}/stm32h7xx.h"
  require_file "${DEVICE_INC}/system_stm32h7xx.h"
  require_file "${CORE_INC}/core_cm7.h"

  log "Preparing STM32H747 CMSIS staging directory"
  rm -rf "${DEST_DIR}"
  mkdir -p "${DEST_DIR}/startup" "${DEST_DIR}/src" "${DEST_DIR}/device" "${DEST_DIR}/core"

  cp "${STARTUP_SRC}" "${DEST_DIR}/startup/startup_stm32h747xihx.s"
  cp "${SYSTEM_SRC}" "${DEST_DIR}/src/system_stm32h7xx.c"
  cp "${DEVICE_INC}"/*.h "${DEST_DIR}/device/"
  cp "${CORE_INC}"/*.h "${DEST_DIR}/core/"

  log "Prepared STM32H747 CMSIS staging directory: ${DEST_DIR}"
  find "${DEST_DIR}" -maxdepth 2 -type f | sort
}

main "$@"
