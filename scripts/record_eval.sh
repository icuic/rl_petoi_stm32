#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export MPLCONFIGDIR="${MPLCONFIGDIR:-${ROOT_DIR}/.cache/matplotlib}"
mkdir -p "$MPLCONFIGDIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Missing .venv/bin/python. Run: bash scripts/setup_env.sh" >&2
  exit 1
fi

CONFIG="${1:-training/configs/ppo_simple_quadruped.yaml}"
shift || true

exec .venv/bin/python training/scripts/record_policy.py --config "$CONFIG" "$@"
