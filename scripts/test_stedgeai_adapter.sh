#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${TMPDIR:-/tmp}/rl_stedgeai_policy_v0.o"
STEDGEAI_ROOT="${STEDGEAI_ROOT:-${ROOT_DIR}/.tools/stedgeai/install/4.0}"
GENERATED_DIR="${STEDGEAI_GENERATED_DIR:-${ROOT_DIR}/build/stedgeai/generate}"
export TMPDIR="${TMPDIR:-/tmp}"

if [[ ! -f "${GENERATED_DIR}/network.h" ]]; then
  echo "Missing generated ST Edge AI network.h. Run: bash scripts/generate_stedgeai.sh" >&2
  exit 1
fi

if [[ ! -f "${STEDGEAI_ROOT}/Middlewares/ST/AI/Inc/stai.h" ]]; then
  echo "Missing ST Edge AI headers. Run: bash scripts/setup_stedgeai.sh" >&2
  exit 1
fi

arm-none-eabi-gcc -std=c11 -Wall -Wextra -Werror \
  -DRL_POLICY_INFERENCE_V0_ENABLE_STEDGEAI \
  -I"${ROOT_DIR}/firmware/stm32h747_disco" \
  -I"${GENERATED_DIR}" \
  -I"${STEDGEAI_ROOT}/Middlewares/ST/AI/Inc" \
  -c "${ROOT_DIR}/firmware/stm32h747_disco/rl_stedgeai_policy_v0.c" \
  -o "${OUT}"

printf 'stm32 rl_stedgeai_policy_v0 compile test: PASS\n'
