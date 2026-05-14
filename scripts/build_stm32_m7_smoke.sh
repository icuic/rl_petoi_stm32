#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${STM32_M7_SMOKE_BUILD_DIR:-${ROOT_DIR}/build/stm32h747_m7_inference_smoke}"
SOURCE_DIR="${ROOT_DIR}/firmware/stm32h747_disco/m7_inference_smoke"
TOOLCHAIN_FILE="${ROOT_DIR}/firmware/stm32h747_disco/cmake/arm-none-eabi-gcc.cmake"

if [[ ! -f "${ROOT_DIR}/firmware/stm32h747_disco/App/inference/stedgeai/generated/network.c" ]]; then
  echo "Missing staged ST Edge AI generated network. Run: bash scripts/prepare_stm32_ai_runtime.sh" >&2
  exit 1
fi

if [[ ! -f "${ROOT_DIR}/firmware/stm32h747_disco/App/cmsis/stm32h7/startup/startup_stm32h747xihx.s" ]]; then
  echo "Missing staged STM32H747 CMSIS startup. Run: bash scripts/prepare_stm32_cmsis.sh" >&2
  exit 1
fi

cmake -S "${SOURCE_DIR}" -B "${BUILD_DIR}" \
  -DCMAKE_TOOLCHAIN_FILE="${TOOLCHAIN_FILE}" \
  -DCMAKE_BUILD_TYPE=Release

cmake --build "${BUILD_DIR}" --target m7_inference_smoke.elf -- -j"$(nproc)"

printf '\nSTM32H747 M7 inference smoke ELF:\n'
printf '  %s/m7_inference_smoke.elf\n' "${BUILD_DIR}"
