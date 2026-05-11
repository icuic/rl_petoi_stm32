#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${ROOT_DIR}"

if [[ ! -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  echo "Missing virtual environment. Run: bash scripts/setup_env.sh" >&2
  exit 1
fi

"${ROOT_DIR}/.venv/bin/python" tools/select_checkpoint.py "$@"
