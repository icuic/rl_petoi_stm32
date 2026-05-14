#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ONNX_PATH="${1:-models/onnx/petoi_bittle_v0_deployable_v0_best_actor.onnx}"
TARGET="${STEDGEAI_TARGET:-stm32h7}"
OUT_DIR="${STEDGEAI_OUT_DIR:-build/stedgeai/generate}"
TOOLS_DIR="${STEDGEAI_TOOLS_DIR:-${ROOT_DIR}/.tools/stedgeai}"

cd "${ROOT_DIR}"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

find_stedgeai() {
  if command -v stedgeai >/dev/null 2>&1; then
    command -v stedgeai
    return 0
  fi

  local candidate
  candidate="$(find "${TOOLS_DIR}" -type f -name stedgeai -perm /111 2>/dev/null | head -n 1 || true)"
  if [[ -n "${candidate}" ]]; then
    printf '%s\n' "${candidate}"
    return 0
  fi

  return 1
}

if [[ ! -f "${ONNX_PATH}" ]]; then
  echo "ONNX model not found: ${ONNX_PATH}" >&2
  exit 1
fi

if ! EDGEAI_BIN="$(find_stedgeai)"; then
  echo "stedgeai not found. Run: bash scripts/setup_stedgeai.sh" >&2
  exit 1
fi

log "Running local ONNX deployability checker"
bash scripts/check_policy_deployability.sh "${ONNX_PATH}"

log "Found ST Edge AI CLI: ${EDGEAI_BIN}"
"${EDGEAI_BIN}" --version || true

mkdir -p "${OUT_DIR}"
log "Generating ST Edge AI C code for target ${TARGET}"
"${EDGEAI_BIN}" generate --quiet -m "${ONNX_PATH}" --target "${TARGET}" -o "${OUT_DIR}" "${@:2}"

log "ST Edge AI generated output directory: ${OUT_DIR}"
find "${OUT_DIR}" -maxdepth 2 -type f | sort
