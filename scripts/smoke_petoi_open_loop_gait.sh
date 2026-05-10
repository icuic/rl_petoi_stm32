#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-.venv/bin/python}"
MODEL="${PETOI_MJCF_OUTPUT:-build/petoi_bittle/petoi_bittle_v0.xml}"

if [ ! -x "${PYTHON}" ]; then
  PYTHON="python3"
fi

if [ ! -f "${MODEL}" ]; then
  bash scripts/build_petoi_mjcf.sh
fi

"${PYTHON}" tools/smoke_petoi_open_loop_gait.py "${MODEL}" "$@"
