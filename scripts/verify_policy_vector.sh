#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VECTOR_PATH="${1:-firmware/stm32h747_disco/test_vectors/deployable_v0_policy_vector.json}"

cd "${ROOT_DIR}"

if [[ ! -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  echo "Missing virtual environment. Run: bash scripts/setup_env.sh" >&2
  exit 1
fi

"${ROOT_DIR}/.venv/bin/python" training/scripts/verify_policy_vector.py "${VECTOR_PATH}" "${@:2}"
