#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-.venv/bin/python}"
URDF="${PETOI_URDF_OUTPUT:-build/petoi_bittle/robot.urdf}"
OUTPUT="${PETOI_MJCF_OUTPUT:-build/petoi_bittle/petoi_bittle_v0.xml}"

if [ ! -x "${PYTHON}" ]; then
  PYTHON="python3"
fi

if [ ! -f "${URDF}" ]; then
  bash scripts/build_petoi_urdf.sh
fi

"${PYTHON}" tools/build_petoi_bittle_mjcf.py \
  --urdf "${URDF}" \
  --output "${OUTPUT}"
