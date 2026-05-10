#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-.venv/bin/python}"
OUTPUT="${PETOI_URDF_OUTPUT:-build/petoi_bittle/robot.urdf}"

if [ ! -x "${PYTHON}" ]; then
  PYTHON="python3"
fi

if [ ! -f third_party/petoi/ros_opencat/petoi_ROS_model_docs/bittle_ros/bittle_description/urdf/bittle.xacro ]; then
  bash scripts/fetch_petoi_model.sh
fi

"${PYTHON}" tools/build_petoi_bittle_urdf.py \
  --output "${OUTPUT}" \
  --mesh-paths basename \
  --copy-meshes \
  --mujoco-sanitize
