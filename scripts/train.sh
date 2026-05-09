#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${1:-training/configs/ppo_simple_quadruped.yaml}"

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

"${ROOT_DIR}/.venv/bin/python" training/scripts/train_ppo.py --config "${CONFIG_PATH}" "$@"
