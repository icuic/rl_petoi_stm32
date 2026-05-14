#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"

ok() {
  printf '[ OK ] %s\n' "$*"
}

warn() {
  printf '[WARN] %s\n' "$*"
}

fail() {
  printf '[FAIL] %s\n' "$*"
}

section() {
  printf '\n== %s ==\n' "$*"
}

run_or_warn() {
  local description="$1"
  shift

  if "$@"; then
    ok "${description}"
  else
    warn "${description}"
  fi
}

python_cmd() {
  if [[ -x "${VENV_DIR}/bin/python" ]]; then
    printf '%s\n' "${VENV_DIR}/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    command -v python3
  elif command -v python >/dev/null 2>&1; then
    command -v python
  else
    return 1
  fi
}

section "System"
if command -v lsb_release >/dev/null 2>&1; then
  lsb_release -ds 2>/dev/null || true
else
  uname -a
fi

section "CPU"
if command -v lscpu >/dev/null 2>&1; then
  lscpu | awk -F: '
    /Model name/ {gsub(/^[ \t]+/, "", $2); print "Model: " $2}
    /^CPU\(s\)/ {gsub(/^[ \t]+/, "", $2); print "vCPU: " $2}
    /Thread\(s\) per core/ {gsub(/^[ \t]+/, "", $2); print "Threads per core: " $2}
  '
else
  warn "lscpu not found"
fi

section "Memory"
if command -v free >/dev/null 2>&1; then
  free -h
else
  warn "free not found"
fi

section "Disk"
df -h "${ROOT_DIR}" 2>/dev/null || df -h .

section "GPU"
if command -v nvidia-smi >/dev/null 2>&1; then
  if nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv,noheader 2>/dev/null; then
    ok "nvidia-smi is available"
  else
    fail "nvidia-smi exists but cannot communicate with the NVIDIA driver"
  fi
else
  warn "nvidia-smi not found"
fi

if compgen -G "/dev/nvidia*" >/dev/null; then
  ls -l /dev/nvidia*
else
  warn "/dev/nvidia* device nodes not found in this shell"
fi

section "Python"
PYTHON_BIN="$(python_cmd || true)"
if [[ -n "${PYTHON_BIN}" ]]; then
  ok "Python: ${PYTHON_BIN}"
  "${PYTHON_BIN}" --version
else
  fail "Python not found"
fi

if [[ -x "${VENV_DIR}/bin/python" ]]; then
  ok "Virtual environment found: ${VENV_DIR}"
else
  warn "Virtual environment not found: ${VENV_DIR}"
fi

if [[ -n "${PYTHON_BIN}" ]]; then
  "${PYTHON_BIN}" -m pip --version >/dev/null 2>&1 \
    && "${PYTHON_BIN}" -m pip --version \
    || warn "pip not available for ${PYTHON_BIN}"
fi

section "Python Packages"
if [[ -n "${PYTHON_BIN}" ]]; then
  "${PYTHON_BIN}" -c '
import importlib

packages = [
    ("numpy", "numpy"),
    ("gymnasium", "gymnasium"),
    ("mujoco", "mujoco"),
    ("stable_baselines3", "stable-baselines3"),
    ("torch", "torch"),
    ("onnx", "onnx"),
    ("onnxruntime", "onnxruntime"),
]

for module_name, display_name in packages:
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", "unknown")
        print(f"[ OK ] {display_name}: {version}")
    except Exception as exc:
        print(f"[WARN] {display_name}: not available ({exc.__class__.__name__})")
'
else
  warn "Skipping package checks because Python is not available"
fi

section "PyTorch CUDA"
if [[ -n "${PYTHON_BIN}" ]]; then
  "${PYTHON_BIN}" -c '
try:
    import torch
except Exception as exc:
    print(f"[WARN] torch unavailable: {exc.__class__.__name__}")
    raise SystemExit(0)

print("torch:", torch.__version__)
print("torch cuda build:", torch.version.cuda)
print("cuda available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("cuda device count:", torch.cuda.device_count())
    for idx in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(idx)
        total_gib = props.total_memory / (1024 ** 3)
        print(f"device {idx}: {props.name}, {total_gib:.1f} GiB")
'
fi

section "MuJoCo Smoke Test"
if [[ -n "${PYTHON_BIN}" ]]; then
  "${PYTHON_BIN}" -c '
try:
    import mujoco
    xml = """
    <mujoco>
      <worldbody>
        <body name="box" pos="0 0 0.1">
          <joint name="free" type="free"/>
          <geom type="box" size="0.05 0.05 0.05" mass="1"/>
        </body>
      </worldbody>
    </mujoco>
    """
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    mujoco.mj_step(model, data)
    print("[ OK ] MuJoCo import and mj_step succeeded")
except Exception as exc:
    print(f"[WARN] MuJoCo smoke test failed: {exc.__class__.__name__}: {exc}")
'
fi

section "ST Edge AI"
STEDGEAI_BIN=""
if command -v stedgeai >/dev/null 2>&1; then
  STEDGEAI_BIN="$(command -v stedgeai)"
else
  STEDGEAI_BIN="$(find "${ROOT_DIR}/.tools/stedgeai" -type f -name stedgeai -perm /111 2>/dev/null | head -n 1 || true)"
fi

if [[ -n "${STEDGEAI_BIN}" ]]; then
  ok "stedgeai: ${STEDGEAI_BIN}"
  "${STEDGEAI_BIN}" --version || warn "stedgeai --version failed"
else
  warn "stedgeai not found; run scripts/setup_stedgeai.sh after installing ST Edge AI Core locally"
fi

section "ARM Toolchain"
if command -v arm-none-eabi-gcc >/dev/null 2>&1; then
  ARM_GCC_BIN="$(command -v arm-none-eabi-gcc)"
  ok "arm-none-eabi-gcc: ${ARM_GCC_BIN}"
  arm-none-eabi-gcc --version | head -n 1
else
  warn "arm-none-eabi-gcc not found; install gcc-arm-none-eabi for STM32 target code-size estimates"
fi

section "Recommended Minimums"
printf 'CPU: 8 vCPU is OK for env development and small CPU rollouts.\n'
printf 'RAM: 30 GiB is OK for early RL experiments.\n'
printf 'GPU: Tesla T4 15 GiB is OK for PPO/SAC prototyping; larger experiments may benefit from L4/A10/4090.\n'
printf 'Disk: keep checkpoints/logs synced; 50 GiB free can fill quickly during training.\n'
