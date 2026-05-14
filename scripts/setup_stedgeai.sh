#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="${STEDGEAI_TOOLS_DIR:-${ROOT_DIR}/.tools/stedgeai}"
ARCHIVE_PATH="${STEDGEAI_ARCHIVE:-${1:-}}"

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

  return 1
}

print_next_steps() {
  printf '\nST Edge AI Core was not found.\n\n'
  printf 'This project uses the local ST Edge AI CLI only. Download/install ST Edge AI Core\n'
  printf "locally, then make the 'stedgeai' command visible in one of these ways:\n\n"
  printf '  1. Add the ST Edge AI Core bin directory to PATH.\n'
  printf '  2. Set STEDGEAI_ARCHIVE to a local .zip/.tar.gz/.tgz archive and re-run:\n'
  printf '       STEDGEAI_ARCHIVE=/path/to/stedgeai-package.zip bash scripts/setup_stedgeai.sh\n'
  printf '  3. Place an executable at:\n'
  printf '       %s/bin/stedgeai\n\n' "${TOOLS_DIR}"
  printf 'After installation, verify with:\n'
  printf '  bash scripts/check_env.sh\n'
  printf '  bash scripts/check_stedgeai.sh\n'
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
    die "archive extracted, but no stedgeai executable was found under ${TOOLS_DIR}"
  fi

  print_next_steps
  return 0
}

main "$@"
