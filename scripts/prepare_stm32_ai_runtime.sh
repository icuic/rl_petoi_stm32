#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GENERATED_DIR="${STEDGEAI_GENERATED_DIR:-${ROOT_DIR}/build/stedgeai/generate}"
STEDGEAI_ROOT="${STEDGEAI_ROOT:-${ROOT_DIR}/.tools/stedgeai/install/4.0}"
DEST_DIR="${STM32_AI_RUNTIME_DIR:-${ROOT_DIR}/firmware/stm32h747_disco/App/inference/stedgeai}"

GENERATED_DEST="${DEST_DIR}/generated"
INCLUDE_DEST="${DEST_DIR}/include"
LIB_DEST="${DEST_DIR}/lib/gcc/stm32h7"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "Missing required file: $1" >&2
    exit 1
  fi
}

copy_required_headers() {
  local source_dir="${STEDGEAI_ROOT}/Middlewares/ST/AI/Inc"
  require_file "${source_dir}/stai.h"
  mkdir -p "${INCLUDE_DEST}"
  cp "${source_dir}"/*.h "${INCLUDE_DEST}/"
}

copy_generated_network() {
  local files=(
    LICENSE.txt
    network.c
    network.h
    network_data.c
    network_data.h
    network_details.h
    network_c_info.json
    network_generate_report.txt
  )

  mkdir -p "${GENERATED_DEST}"
  for file in "${files[@]}"; do
    require_file "${GENERATED_DIR}/${file}"
    cp "${GENERATED_DIR}/${file}" "${GENERATED_DEST}/"
  done
}

copy_runtime_library() {
  local source_dir="${STEDGEAI_ROOT}/Middlewares/ST/AI/Lib/GCC/STM32H7"
  local runtime_lib="${source_dir}/NetworkRuntime1200_CM7_GCC.a"

  require_file "${runtime_lib}"
  mkdir -p "${LIB_DEST}"
  cp "${runtime_lib}" "${LIB_DEST}/"
}

main() {
  cd "${ROOT_DIR}"

  log "Preparing STM32 AI runtime staging directory"
  rm -rf "${DEST_DIR}"

  copy_generated_network
  copy_required_headers
  copy_runtime_library

  log "Prepared STM32 AI runtime staging directory: ${DEST_DIR}"
  find "${DEST_DIR}" -maxdepth 3 -type f | sort
}

main "$@"
