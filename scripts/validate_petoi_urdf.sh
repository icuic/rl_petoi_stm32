#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-.venv/bin/python}"
MODEL="${PETOI_URDF_OUTPUT:-build/petoi_bittle/robot.urdf}"

if [ ! -x "${PYTHON}" ]; then
  PYTHON="python3"
fi

if [ ! -f "${MODEL}" ]; then
  bash scripts/build_petoi_urdf.sh
fi

"${PYTHON}" tools/validate_mujoco_model.py "${MODEL}"
