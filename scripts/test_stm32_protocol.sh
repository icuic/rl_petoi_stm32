#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_OUT="${TMPDIR:-/tmp}/stm32_rl_serial_protocol_v0_test"
TRANSPORT_OUT="${TMPDIR:-/tmp}/stm32_rl_serial_transport_v0_test"

cc -std=c11 -Wall -Wextra -Werror \
  -I"${ROOT_DIR}/firmware/stm32h747_disco" \
  "${ROOT_DIR}/firmware/stm32h747_disco/rl_serial_protocol_v0.c" \
  "${ROOT_DIR}/firmware/stm32h747_disco/tests/rl_serial_protocol_v0_test.c" \
  -lm \
  -o "${PROTO_OUT}"

"${PROTO_OUT}"

cc -std=c11 -Wall -Wextra -Werror \
  -I"${ROOT_DIR}/firmware/stm32h747_disco" \
  "${ROOT_DIR}/firmware/stm32h747_disco/rl_serial_protocol_v0.c" \
  "${ROOT_DIR}/firmware/stm32h747_disco/rl_serial_transport_v0.c" \
  "${ROOT_DIR}/firmware/stm32h747_disco/tests/rl_serial_transport_v0_test.c" \
  -lm \
  -o "${TRANSPORT_OUT}"

"${TRANSPORT_OUT}"
