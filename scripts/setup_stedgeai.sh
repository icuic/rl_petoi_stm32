#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="${STEDGEAI_TOOLS_DIR:-${ROOT_DIR}/.tools/stedgeai}"
ARCHIVE_PATH="${STEDGEAI_ARCHIVE:-${1:-}}"
INSTALL_ROOT="${STEDGEAI_INSTALL_ROOT:-${TOOLS_DIR}/install}"
PACKAGE_NAME="${STEDGEAI_PACKAGE:-stedgeai0400.stm32mcu}"
ONLINE_INSTALLER="${STEDGEAI_INSTALLER:-}"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

find_stedgeai() {
  if command -v stedgeai >/dev/null 2>&1; then
    command -v stedgeai
    return 0
  fi

  if [[ -x "${TOOLS_DIR}/stedgeai" ]]; then
    printf '%s\n' "${TOOLS_DIR}/stedgeai"
    return 0
  fi

  if [[ -x "${TOOLS_DIR}/bin/stedgeai" ]]; then
    printf '%s\n' "${TOOLS_DIR}/bin/stedgeai"
    return 0
  fi

  if [[ -x "${INSTALL_ROOT}/stedgeai" ]]; then
    printf '%s\n' "${INSTALL_ROOT}/stedgeai"
    return 0
  fi

  if [[ -x "${INSTALL_ROOT}/bin/stedgeai" ]]; then
    printf '%s\n' "${INSTALL_ROOT}/bin/stedgeai"
    return 0
  fi

  local candidate
  candidate="$(find "${TOOLS_DIR}" -type f -name stedgeai -perm /111 2>/dev/null | head -n 1 || true)"
  if [[ -n "${candidate}" ]]; then
    printf '%s\n' "${candidate}"
    return 0
  fi

  return 1
}

find_online_installer() {
  if [[ -n "${ONLINE_INSTALLER}" && -x "${ONLINE_INSTALLER}" ]]; then
    printf '%s\n' "${ONLINE_INSTALLER}"
    return 0
  fi

  if [[ -x "${TOOLS_DIR}/stedgeai-linux-onlineinstaller" ]]; then
    printf '%s\n' "${TOOLS_DIR}/stedgeai-linux-onlineinstaller"
    return 0
  fi

  local candidate
  candidate="$(find "${TOOLS_DIR}" -maxdepth 3 -type f -name 'stedgeai*onlineinstaller' -perm /111 2>/dev/null | head -n 1 || true)"
  if [[ -n "${candidate}" ]]; then
    printf '%s\n' "${candidate}"
    return 0
  fi

  return 1
}

print_next_steps() {
  printf '\nST Edge AI Core was not found.\n\n'
  printf 'This project uses the local ST Edge AI CLI only. Download/install ST Edge AI Core\n'
  printf "locally, then make the 'stedgeai' command visible in one of these ways:\n\n"
  printf '  1. Add the ST Edge AI Core bin directory to PATH.\n'
  printf '  2. Set STEDGEAI_ARCHIVE to a local .zip/.tar.gz/.tgz archive and re-run:\n'
  printf '       STEDGEAI_ARCHIVE=/path/to/stedgeai-package.zip bash scripts/setup_stedgeai.sh\n'
  printf '  3. Set STEDGEAI_INSTALLER to a local stedgeai-linux-onlineinstaller and re-run:\n'
  printf '       STEDGEAI_INSTALLER=/path/to/stedgeai-linux-onlineinstaller bash scripts/setup_stedgeai.sh\n'
  printf '  4. Place an executable at:\n'
  printf '       %s/bin/stedgeai\n\n' "${TOOLS_DIR}"
  printf 'After installation, verify with:\n'
  printf '  bash scripts/check_env.sh\n'
  printf '  bash scripts/check_stedgeai.sh\n'
}

run_online_installer() {
  local installer="$1"

  log "Installing ST Edge AI package ${PACKAGE_NAME} into ${INSTALL_ROOT}"
  "${installer}" \
    --root "${INSTALL_ROOT}" \
    --accept-licenses \
    --confirm-command \
    install "${PACKAGE_NAME}"
}

install_from_archive() {
  local archive="$1"

  [[ -f "${archive}" ]] || die "STEDGEAI_ARCHIVE does not exist: ${archive}"

  log "Installing ST Edge AI Core archive into ${TOOLS_DIR}"
  mkdir -p "${TOOLS_DIR}"

  case "${archive}" in
    *.zip)
      command -v unzip >/dev/null 2>&1 || die "unzip is required to extract ${archive}"
      unzip -q -o "${archive}" -d "${TOOLS_DIR}"
      ;;
    *.tar.gz|*.tgz)
      tar -xzf "${archive}" -C "${TOOLS_DIR}"
      ;;
    *)
      die "unsupported archive format: ${archive}"
      ;;
  esac

  chmod +x "${TOOLS_DIR}/stedgeai-linux-onlineinstaller" 2>/dev/null || true
}

main() {
  cd "${ROOT_DIR}"

  if EDGEAI_BIN="$(find_stedgeai)"; then
    log "Found ST Edge AI CLI: ${EDGEAI_BIN}"
    "${EDGEAI_BIN}" --version || true
    return 0
  fi

  if [[ -n "${ARCHIVE_PATH}" ]]; then
    install_from_archive "${ARCHIVE_PATH}"
    if EDGEAI_BIN="$(find_stedgeai)"; then
      log "Found ST Edge AI CLI after archive install: ${EDGEAI_BIN}"
      "${EDGEAI_BIN}" --version || true
      return 0
    fi
  fi

  if INSTALLER_BIN="$(find_online_installer)"; then
    run_online_installer "${INSTALLER_BIN}"
    if EDGEAI_BIN="$(find_stedgeai)"; then
      log "Found ST Edge AI CLI after online install: ${EDGEAI_BIN}"
      "${EDGEAI_BIN}" --version || true
      return 0
    fi
    die "online install completed, but no stedgeai executable was found under ${TOOLS_DIR}"
  fi

  print_next_steps
  return 0
}

main "$@"
