#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${1:-training/logs}"
HOST="${TENSORBOARD_HOST:-127.0.0.1}"
PORT="${TENSORBOARD_PORT:-6006}"

cd "${ROOT_DIR}"

if [[ ! -x "${ROOT_DIR}/.venv/bin/tensorboard" ]]; then
  echo "Missing tensorboard. Run: bash scripts/setup_env.sh" >&2
  exit 1
fi

echo "Starting TensorBoard"
echo "  logdir: ${LOG_DIR}"
echo "  host:   ${HOST}"
echo "  port:   ${PORT}"
echo
echo "For local access over SSH, run this on your local machine:"
echo "  ssh -L ${PORT}:127.0.0.1:${PORT} ubuntu@<server-ip>"
echo

"${ROOT_DIR}/.venv/bin/tensorboard" --logdir "${LOG_DIR}" --host "${HOST}" --port "${PORT}"
