#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3.9}"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

create_dirs() {
  log "Creating project directories"
  mkdir -p \
    "${ROOT_DIR}/docs" \
    "${ROOT_DIR}/assets/images" \
    "${ROOT_DIR}/assets/videos" \
    "${ROOT_DIR}/sim/envs" \
    "${ROOT_DIR}/sim/robots" \
    "${ROOT_DIR}/sim/tasks" \
    "${ROOT_DIR}/sim/rewards" \
    "${ROOT_DIR}/sim/wrappers" \
    "${ROOT_DIR}/sim/tests" \
    "${ROOT_DIR}/training/configs" \
    "${ROOT_DIR}/training/scripts" \
    "${ROOT_DIR}/training/callbacks" \
    "${ROOT_DIR}/training/checkpoints" \
    "${ROOT_DIR}/training/logs" \
    "${ROOT_DIR}/training/eval" \
    "${ROOT_DIR}/models/exported" \
    "${ROOT_DIR}/models/quantized" \
    "${ROOT_DIR}/models/reports" \
    "${ROOT_DIR}/tools/export_model" \
    "${ROOT_DIR}/tools/quantization" \
    "${ROOT_DIR}/tools/telemetry" \
    "${ROOT_DIR}/tools/calibration" \
    "${ROOT_DIR}/firmware/stm32h747_disco/App/inference" \
    "${ROOT_DIR}/firmware/stm32h747_disco/App/control" \
    "${ROOT_DIR}/firmware/stm32h747_disco/App/comm" \
    "${ROOT_DIR}/firmware/stm32h747_disco/App/safety" \
    "${ROOT_DIR}/firmware/stm32h747_disco/App/telemetry" \
    "${ROOT_DIR}/firmware/petoi_opencat/protocol_adapter" \
    "${ROOT_DIR}/firmware/petoi_opencat/joint_command_mode" \
    "${ROOT_DIR}/protocol/schemas" \
    "${ROOT_DIR}/protocol/test_vectors" \
    "${ROOT_DIR}/experiments/runs" \
    "${ROOT_DIR}/experiments/notebooks" \
    "${ROOT_DIR}/experiments/reports"
}

install_apt_packages() {
  if ! command -v apt-get >/dev/null 2>&1; then
    log "apt-get not found; skipping Ubuntu package installation"
    return
  fi

  log "Installing Ubuntu packages"
  sudo apt-get update
  sudo apt-get install -y \
    build-essential \
    cmake \
    git \
    git-lfs \
    curl \
    wget \
    python3 \
    python3.9 \
    python3.9-venv \
    python3.9-dev \
    python3-venv \
    python3-pip \
    python3-dev \
    libgl1 \
    libglfw3 \
    libglew-dev \
    libosmesa6 \
    libusb-1.0-0 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-render-util0 \
    libxcb-render0 \
    libxcb-shape0 \
    libxcb-xkb1 \
    libfreetype6 \
    fontconfig \
    unzip
}

setup_python_env() {
  log "Creating Python virtual environment at ${VENV_DIR}"
  "${PYTHON_BIN}" -m venv --clear "${VENV_DIR}"
  # shellcheck source=/dev/null
  source "${VENV_DIR}/bin/activate"

  log "Upgrading pip tooling"
  python -m pip install --upgrade pip setuptools wheel

  log "Installing Python dependencies"
  python -m pip install -r "${ROOT_DIR}/requirements.txt"
}

verify_env() {
  log "Verifying environment"
  # shellcheck source=/dev/null
  source "${VENV_DIR}/bin/activate"
  python - <<'PY'
import gymnasium
import mujoco
import stable_baselines3

print("gymnasium:", gymnasium.__version__)
print("mujoco:", mujoco.__version__)
print("stable_baselines3:", stable_baselines3.__version__)
PY
}

main() {
  create_dirs
  install_apt_packages
  setup_python_env
  verify_env

  log "Setup complete"
  printf '\nNext steps:\n'
  printf '  source %s/bin/activate\n' "${VENV_DIR}"
  printf '  bash %s/scripts/setup_stedgeai.sh  # optional: local STM32 AI deployment CLI\n' "${ROOT_DIR}"
  printf '  bash %s/scripts/check_env.sh\n' "${ROOT_DIR}"
  printf '  python -c "import mujoco, gymnasium; print(\"env ok\")"\n'
}

main "$@"
