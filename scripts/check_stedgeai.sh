#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ONNX_PATH="${1:-models/onnx/petoi_bittle_v0_deployable_v0_best_actor.onnx}"
TARGET="${STEDGEAI_TARGET:-stm32h7}"
OUT_DIR="${STEDGEAI_OUT_DIR:-build/stedgeai/analyze}"
REPORT_PATH="${STEDGEAI_DEPLOYABILITY_REPORT:-models/reports/petoi_bittle_v0_deployability.json}"

cd "${ROOT_DIR}"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

find_stedgeai() {
  if command -v stedgeai >/dev/null 2>&1; then
    command -v stedgeai
    return 0
  fi
  if command -v stm32ai >/dev/null 2>&1; then
    command -v stm32ai
    return 0
  fi
  return 1
}

if [[ ! -f "${ONNX_PATH}" ]]; then
  echo "ONNX model not found: ${ONNX_PATH}" >&2
  echo "Export it first, for example:" >&2
  echo "  bash scripts/export_policy.sh training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue.yaml \\" >&2
  echo "    --model training/checkpoints/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue_10000_steps.zip \\" >&2
  echo "    --output ${ONNX_PATH}" >&2
  exit 1
fi

log "Running local ONNX deployability checker"
bash scripts/check_policy_deployability.sh "${ONNX_PATH}" --report "${REPORT_PATH}"

if ! EDGEAI_BIN="$(find_stedgeai)"; then
  cat <<EOF

ST Edge AI CLI was not found on this server.

Checked commands:
  - stedgeai
  - stm32ai

Current model:
  ${ONNX_PATH}

Local checker result was saved to:
  ${REPORT_PATH}

Next options:
  1. Install STM32Cube AI Studio / ST Edge AI Core locally and re-run this script.
  2. Use STM32Cube.AI Developer Cloud to upload:
       ${ONNX_PATH}
  3. Keep using scripts/check_policy_deployability.sh as a pre-flight check before cloud upload.
EOF
  exit 0
fi

log "Found ST Edge AI CLI: ${EDGEAI_BIN}"
"${EDGEAI_BIN}" --version || true

mkdir -p "${OUT_DIR}"
log "Running ST Edge AI analyze for target ${TARGET}"
"${EDGEAI_BIN}" analyze -m "${ONNX_PATH}" --target "${TARGET}" -o "${OUT_DIR}" "${@:2}"

log "ST Edge AI analyze output directory: ${OUT_DIR}"
