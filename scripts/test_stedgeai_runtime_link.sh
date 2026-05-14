#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGING_DIR="${STM32_AI_RUNTIME_DIR:-${ROOT_DIR}/firmware/stm32h747_disco/App/inference/stedgeai}"
OUT_DIR="${TMPDIR:-/tmp}/rl_petoi_stedgeai_link"
OUT_ELF="${OUT_DIR}/rl_stedgeai_smoke.elf"
export TMPDIR="${TMPDIR:-/tmp}"

mkdir -p "${OUT_DIR}"

if [[ ! -f "${STAGING_DIR}/generated/network.c" ]]; then
  echo "Missing staged ST Edge AI generated network. Run: bash scripts/prepare_stm32_ai_runtime.sh" >&2
  exit 1
fi

cat >"${OUT_DIR}/main.c" <<'C'
#include "rl_stedgeai_policy_v0.h"

int main(void) {
  float observation[RL_POLICY_V0_OBSERVATION_DIM] = {0};
  float action[RL_POLICY_V0_ACTION_DIM] = {0};
  return rl_stedgeai_policy_v0_forward(observation, action, 0) ? 0 : 1;
}
C

arm-none-eabi-gcc -std=c11 -Wall -Wextra -Werror \
  -DRL_POLICY_INFERENCE_V0_ENABLE_STEDGEAI \
  -mcpu=cortex-m7 -mthumb -mfloat-abi=hard -mfpu=fpv5-d16 \
  -I"${ROOT_DIR}/firmware/stm32h747_disco" \
  -I"${STAGING_DIR}/generated" \
  -I"${STAGING_DIR}/include" \
  -c "${ROOT_DIR}/firmware/stm32h747_disco/rl_stedgeai_policy_v0.c" \
  -o "${OUT_DIR}/rl_stedgeai_policy_v0.o"

arm-none-eabi-gcc -std=c11 -Wall -Wextra -Werror \
  -mcpu=cortex-m7 -mthumb -mfloat-abi=hard -mfpu=fpv5-d16 \
  -I"${STAGING_DIR}/generated" \
  -I"${STAGING_DIR}/include" \
  -c "${STAGING_DIR}/generated/network.c" \
  -o "${OUT_DIR}/network.o"

arm-none-eabi-gcc -std=c11 -Wall -Wextra -Werror \
  -mcpu=cortex-m7 -mthumb -mfloat-abi=hard -mfpu=fpv5-d16 \
  -I"${STAGING_DIR}/generated" \
  -I"${STAGING_DIR}/include" \
  -c "${STAGING_DIR}/generated/network_data.c" \
  -o "${OUT_DIR}/network_data.o"

arm-none-eabi-gcc -std=c11 -Wall -Wextra -Werror \
  -DRL_POLICY_INFERENCE_V0_ENABLE_STEDGEAI \
  -mcpu=cortex-m7 -mthumb -mfloat-abi=hard -mfpu=fpv5-d16 \
  -I"${ROOT_DIR}/firmware/stm32h747_disco" \
  -I"${STAGING_DIR}/generated" \
  -I"${STAGING_DIR}/include" \
  -c "${OUT_DIR}/main.c" \
  -o "${OUT_DIR}/main.o"

arm-none-eabi-gcc \
  -mcpu=cortex-m7 -mthumb -mfloat-abi=hard -mfpu=fpv5-d16 \
  -specs=nosys.specs \
  "${OUT_DIR}/main.o" \
  "${OUT_DIR}/rl_stedgeai_policy_v0.o" \
  "${OUT_DIR}/network.o" \
  "${OUT_DIR}/network_data.o" \
  "${STAGING_DIR}/lib/gcc/stm32h7/NetworkRuntime1200_CM7_GCC.a" \
  -lm \
  -o "${OUT_ELF}"

printf 'stm32 stedgeai runtime link test: PASS\n'
arm-none-eabi-size "${OUT_ELF}"
