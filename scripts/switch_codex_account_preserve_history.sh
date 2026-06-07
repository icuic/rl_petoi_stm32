#!/usr/bin/env bash
set -euo pipefail

CODEX_HOME="${CODEX_HOME:-${HOME}/.codex}"
BACKUP_ROOT="${CODEX_ACCOUNT_BACKUP_ROOT:-${HOME}}"
BACKUP_ONLY=0
CLEAR_CACHE=0
QUARANTINE_CODEX_DIR=0
YES=0
RESTORE_FROM=""

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/switch_codex_account_preserve_history.sh [options]
  bash scripts/switch_codex_account_preserve_history.sh --restore-from PATH [--yes]

Purpose:
  Prepare this Ubuntu user for switching Codex accounts while preserving local
  conversation/session data.

Default behavior:
  1. Create a compressed backup of ~/.codex.
  2. Run `codex auth logout` when the codex CLI is available.
  3. Remove only known auth/token files from ~/.codex.
  4. Keep sessions, attachments, memories, and sqlite state files.

Options:
  --backup-only
      Only create the backup. Do not log out or remove auth files.

  --clear-cache
      Also remove ~/.config/codex, ~/.local/share/codex, and ~/.cache/codex.
      This is useful for revoked-token loops, but still preserves ~/.codex
      history data.

  --quarantine-codex-dir
      After backing up and logging out, move ~/.codex to a timestamped backup
      directory instead of editing it in place. This is stronger than the
      default and may hide old threads until you copy history folders back.
      It still does not delete ~/.codex.

  --yes
      Run without interactive confirmation.

  --restore-from PATH
      Restore selected conversation/history files from a previous backup.
      PATH may be either:
        - a codex-account-switch-*.tar.gz backup created by this script
        - a quarantined ~/.codex.account-switch-* directory

      The restore copies sessions, attachments, memories, sqlite state/log
      files, shell snapshots, and goal databases into ~/.codex. It intentionally
      does not restore old auth/token files.

  -h, --help
      Show this help.

Examples:
  bash scripts/switch_codex_account_preserve_history.sh
  bash scripts/switch_codex_account_preserve_history.sh --clear-cache
  bash scripts/switch_codex_account_preserve_history.sh --quarantine-codex-dir
  bash scripts/switch_codex_account_preserve_history.sh --restore-from ~/codex-account-switch-20260607T120000Z.tar.gz
  bash scripts/switch_codex_account_preserve_history.sh --restore-from ~/.codex.account-switch-20260607T120000Z

Do not restore ~/.codex/auth.json from an old account.
USAGE
}

log() {
  printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

confirm() {
  if [[ "${YES}" -eq 1 ]]; then
    return 0
  fi

  if [[ -n "${RESTORE_FROM}" ]]; then
    printf '\nThis will restore selected Codex history files from:\n  %s\n' "${RESTORE_FROM}"
    printf 'Destination:\n  %s\n' "${CODEX_HOME}"
    printf 'It will first back up the current destination and will not restore old auth/token files.\n'
    printf 'Continue? [y/N] '
    local restore_answer
    read -r restore_answer
    case "${restore_answer}" in
      y|Y|yes|YES)
        return 0
        ;;
      *)
        fail "aborted"
        ;;
    esac
  fi

  printf '\nThis will back up %s and remove Codex auth files for this user.\n' "${CODEX_HOME}"
  printf 'It will not delete sessions, attachments, memories, or sqlite state files.\n'
  if [[ "${CLEAR_CACHE}" -eq 1 ]]; then
    printf 'It will also remove Codex cache/config directories outside %s.\n' "${CODEX_HOME}"
  fi
  if [[ "${QUARANTINE_CODEX_DIR}" -eq 1 ]]; then
    printf 'It will move %s aside after backup instead of editing it in place.\n' "${CODEX_HOME}"
  fi
  printf 'Continue? [y/N] '

  local answer
  read -r answer
  case "${answer}" in
    y|Y|yes|YES)
      ;;
    *)
      fail "aborted"
      ;;
  esac
}

timestamp() {
  date -u +%Y%m%dT%H%M%SZ
}

create_backup() {
  local ts="$1"
  local backup_path="${BACKUP_ROOT}/codex-account-switch-${ts}.tar.gz"

  if [[ ! -d "${CODEX_HOME}" ]]; then
    log "Codex home does not exist: ${CODEX_HOME}"
    return 0
  fi

  mkdir -p "${BACKUP_ROOT}"
  log "Creating backup: ${backup_path}"
  tar -czf "${backup_path}" -C "$(dirname "${CODEX_HOME}")" "$(basename "${CODEX_HOME}")"
  log "Backup created"
}

restore_copy_path() {
  local source_path="$1"
  local relative_path="$2"
  local destination_path="${CODEX_HOME}/${relative_path}"

  if [[ ! -e "${source_path}" ]]; then
    return 0
  fi

  mkdir -p "$(dirname "${destination_path}")"
  rm -rf "${destination_path}"
  cp -a "${source_path}" "${destination_path}"
  log "Restored ${relative_path}"
}

restore_matching_files() {
  local source_dir="$1"
  local pattern="$2"
  local restored_any=0

  shopt -s nullglob
  local source_path
  for source_path in "${source_dir}"/${pattern}; do
    restore_copy_path "${source_path}" "$(basename "${source_path}")"
    restored_any=1
  done
  shopt -u nullglob

  if [[ "${restored_any}" -eq 0 ]]; then
    log "No files matched ${pattern}"
  fi
}

restore_history_from_dir() {
  local source_dir="$1"

  [[ -d "${source_dir}" ]] || fail "restore source is not a directory: ${source_dir}"

  mkdir -p "${CODEX_HOME}"
  log "Restoring selected history data from ${source_dir}"

  restore_copy_path "${source_dir}/sessions" "sessions"
  restore_copy_path "${source_dir}/attachments" "attachments"
  restore_copy_path "${source_dir}/memories" "memories"
  restore_copy_path "${source_dir}/shell_snapshots" "shell_snapshots"
  restore_matching_files "${source_dir}" "state_*.sqlite*"
  restore_matching_files "${source_dir}" "logs_*.sqlite*"
  restore_matching_files "${source_dir}" "goals_*.sqlite*"
  restore_matching_files "${source_dir}" "memories_*.sqlite*"

  log "Restore complete. Old auth/token files were not copied."
}

restore_history() {
  local ts="$1"
  [[ -n "${RESTORE_FROM}" ]] || return 0

  create_backup "${ts}"

  if [[ -d "${RESTORE_FROM}" ]]; then
    restore_history_from_dir "${RESTORE_FROM}"
    return 0
  fi

  if [[ -f "${RESTORE_FROM}" ]]; then
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    log "Extracting ${RESTORE_FROM}"
    tar -xzf "${RESTORE_FROM}" -C "${tmp_dir}"

    local extracted_codex="${tmp_dir}/.codex"
    if [[ ! -d "${extracted_codex}" ]]; then
      extracted_codex="${tmp_dir}/$(basename "${CODEX_HOME}")"
    fi
    restore_history_from_dir "${extracted_codex}"
    rm -rf "${tmp_dir}"
    return 0
  fi

  fail "restore source does not exist: ${RESTORE_FROM}"
}

logout_codex() {
  if command -v codex >/dev/null 2>&1; then
    log "Running codex auth logout"
    codex auth logout || log "codex auth logout returned non-zero; continuing with file cleanup"
  else
    log "codex CLI not found; skipping codex auth logout"
  fi
}

remove_auth_files() {
  if [[ ! -d "${CODEX_HOME}" ]]; then
    log "Codex home does not exist; no auth files to remove"
    return 0
  fi

  log "Removing known auth/token files under ${CODEX_HOME}"
  rm -f "${CODEX_HOME}/auth.json"
  rm -f "${CODEX_HOME}/auth.json.bak"
  rm -f "${CODEX_HOME}/credentials.json"
  rm -f "${CODEX_HOME}/token.json"
}

clear_external_cache() {
  if [[ "${CLEAR_CACHE}" -ne 1 ]]; then
    return 0
  fi

  log "Removing Codex cache/config directories outside ${CODEX_HOME}"
  rm -rf "${HOME}/.config/codex"
  rm -rf "${HOME}/.local/share/codex"
  rm -rf "${HOME}/.cache/codex"
}

quarantine_codex_home() {
  local ts="$1"
  if [[ "${QUARANTINE_CODEX_DIR}" -ne 1 ]]; then
    return 0
  fi
  if [[ ! -d "${CODEX_HOME}" ]]; then
    log "Codex home does not exist; nothing to quarantine"
    return 0
  fi

  local quarantine_path="${CODEX_HOME}.account-switch-${ts}"
  log "Moving ${CODEX_HOME} to ${quarantine_path}"
  mv "${CODEX_HOME}" "${quarantine_path}"
  log "Quarantined old Codex home. Re-login will create a fresh ${CODEX_HOME}."
}

print_next_steps() {
  cat <<EOF

Done.

Next steps:
  1. Log in with the new Codex account from the desktop/client.
  2. Start Codex normally.
  3. If old threads are missing after using --quarantine-codex-dir, copy back
     sessions/attachments/memories/state_*.sqlite*/logs_*.sqlite* from the
     timestamped ${CODEX_HOME}.account-switch-* directory.

Do not copy old auth.json back.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backup-only)
      BACKUP_ONLY=1
      shift
      ;;
    --clear-cache)
      CLEAR_CACHE=1
      shift
      ;;
    --quarantine-codex-dir)
      QUARANTINE_CODEX_DIR=1
      shift
      ;;
    --yes)
      YES=1
      shift
      ;;
    --restore-from)
      [[ $# -ge 2 ]] || fail "--restore-from requires a path"
      RESTORE_FROM="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

main() {
  local ts
  ts="$(timestamp)"

  confirm

  if [[ -n "${RESTORE_FROM}" ]]; then
    restore_history "${ts}"
    return 0
  fi

  create_backup "${ts}"

  if [[ "${BACKUP_ONLY}" -eq 1 ]]; then
    log "Backup-only mode complete"
    return 0
  fi

  logout_codex
  remove_auth_files
  clear_external_cache
  quarantine_codex_home "${ts}"
  print_next_steps
}

main "$@"
