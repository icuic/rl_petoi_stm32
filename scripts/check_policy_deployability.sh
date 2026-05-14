#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ONNX_PATH="${1:-models/onnx/petoi_bittle_v0_deployable_v0_best_actor.onnx}"

cd "${ROOT_DIR}"

if [[ ! -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  echo "Missing virtual environment. Run: bash scripts/setup_env.sh" >&2
  exit 1
fi

"${ROOT_DIR}/.venv/bin/python" training/scripts/check_policy_deployability.py "${ONNX_PATH}" "${@:2}"
