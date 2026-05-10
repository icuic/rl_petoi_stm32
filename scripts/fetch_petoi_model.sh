#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${PETOI_ROS_REPO_URL:-https://github.com/PetoiCamp/ros_opencat.git}"
REF="${PETOI_ROS_REF:-ros1}"
DEST="${PETOI_MODEL_DEST:-third_party/petoi/ros_opencat}"
SPARSE_PATH="petoi_ROS_model_docs/bittle_ros/bittle_description"

echo "Fetching Petoi Bittle ROS description"
echo "  repo: ${REPO_URL}"
echo "  ref : ${REF}"
echo "  dest: ${DEST}"

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git is required." >&2
  exit 1
fi

mkdir -p "$(dirname "${DEST}")"

if [ -d "${DEST}/.git" ]; then
  git -C "${DEST}" fetch --depth 1 origin "${REF}"
  git -C "${DEST}" checkout FETCH_HEAD
else
  git clone --depth 1 --branch "${REF}" --no-checkout "${REPO_URL}" "${DEST}"
  git -C "${DEST}" sparse-checkout init --cone
fi

git -C "${DEST}" sparse-checkout set "${SPARSE_PATH}"
git -C "${DEST}" checkout

MODEL_DIR="${DEST}/${SPARSE_PATH}"
if [ ! -f "${MODEL_DIR}/urdf/bittle.xacro" ]; then
  echo "ERROR: bittle.xacro was not found at ${MODEL_DIR}/urdf/bittle.xacro" >&2
  exit 1
fi

mesh_count="$(find "${MODEL_DIR}/meshes" -type f -name '*.stl' | wc -l | tr -d ' ')"

echo "Petoi Bittle model is ready:"
echo "  ${MODEL_DIR}"
echo "  xacro: ${MODEL_DIR}/urdf/bittle.xacro"
echo "  STL meshes: ${mesh_count}"
