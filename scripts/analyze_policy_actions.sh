#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${1:-training/configs/ppo_petoi_bittle_v0_trot_residual_deployable_v0_100k_continue.yaml}"

cd "${ROOT_DIR}"

export MPLCONFIGDIR="${MPLCONFIGDIR:-${ROOT_DIR}/.cache/matplotlib}"
mkdir -p "${MPLCONFIGDIR}"

if [[ ! -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  echo "Missing virtual environment. Run: bash scripts/setup_env.sh" >&2
  exit 1
fi

if [[ $# -gt 0 ]]; then
  shift
fi

"${ROOT_DIR}/.venv/bin/python" tools/analyze_policy_actions.py --config "${CONFIG_PATH}" "$@"
