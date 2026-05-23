#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRP_VERSION="${FRP_VERSION:-0.64.0}"
FRP_ARCHIVE="${FRP_ARCHIVE:-frp_${FRP_VERSION}_linux_amd64.tar.gz}"
FRP_BASE_URL="${FRP_BASE_URL:-https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}}"
FRP_DIR="${ROOT_DIR}/.tools/frp"
FRPS_BIN="${FRP_DIR}/frps"
FRPC_BIN="${FRP_DIR}/frpc"
FRPS_CONFIG="${FRPS_CONFIG:-${FRP_DIR}/frps.toml}"
FRPC_CONFIG="${FRPC_CONFIG:-${FRP_DIR}/frpc.toml}"
FRP_BIND_PORT="${FRP_BIND_PORT:-7000}"
FRP_REMOTE_PORT="${FRP_REMOTE_PORT:-60022}"
FRP_LOCAL_SSH_HOST="${FRP_LOCAL_SSH_HOST:-127.0.0.1}"
FRP_LOCAL_SSH_PORT="${FRP_LOCAL_SSH_PORT:-58985}"
FRP_PROXY_NAME="${FRP_PROXY_NAME:-local-ubuntu-ssh}"
MODE="server"
START=0
WRITE_CLIENT=0
PRINT_CLIENT=0

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/setup_reverse_ssh_frp.sh [server|client] [--start] [--write-client] [--print-client]

Environment:
  FRP_TOKEN             Required to write runnable frps/frpc configs.
                        If omitted, the script reuses an existing token from
                        .tools/frp/frps.toml when available.
  FRP_SERVER_ADDR       Required for client config; new cloud public IP.
  FRP_VERSION           Default: 0.64.0
  FRP_BIND_PORT         Default: 7000
  FRP_REMOTE_PORT       Default: 60022
  FRP_LOCAL_SSH_PORT    Default: 58985

Examples:
  FRP_TOKEN="$(openssl rand -hex 24)" bash scripts/setup_reverse_ssh_frp.sh server --start
  FRP_TOKEN="..." FRP_SERVER_ADDR="NEW_CLOUD_IP" bash scripts/setup_reverse_ssh_frp.sh client --print-client

Notes:
  - Configs are written under ignored .tools/frp/.
  - Do not commit FRP tokens.
  - Server mode binds the reverse SSH proxy to 127.0.0.1:${FRP_REMOTE_PORT}.
USAGE
}

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    server|client)
      MODE="$1"
      shift
      ;;
    --start)
      START=1
      shift
      ;;
    --write-client)
      WRITE_CLIENT=1
      shift
      ;;
    --print-client)
      PRINT_CLIENT=1
      shift
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

download_frp() {
  mkdir -p "${FRP_DIR}"
  if [[ -x "${FRPS_BIN}" && -x "${FRPC_BIN}" ]]; then
    log "FRP binaries already exist in ${FRP_DIR}"
    return
  fi

  local tmp_dir
  tmp_dir="$(mktemp -d)"
  local archive_path="${tmp_dir}/${FRP_ARCHIVE}"
  local url="${FRP_BASE_URL}/${FRP_ARCHIVE}"

  log "Downloading FRP ${FRP_VERSION}"
  curl -L -o "${archive_path}" "${url}"
  tar -xzf "${archive_path}" -C "${tmp_dir}"
  cp "${tmp_dir}/frp_${FRP_VERSION}_linux_amd64/frps" "${FRPS_BIN}"
  cp "${tmp_dir}/frp_${FRP_VERSION}_linux_amd64/frpc" "${FRPC_BIN}"
  chmod +x "${FRPS_BIN}" "${FRPC_BIN}"
}

require_token() {
  if [[ -z "${FRP_TOKEN:-}" && -f "${FRPS_CONFIG}" ]]; then
    FRP_TOKEN="$(awk -F '"' '/auth\.token[[:space:]]*=/ { print $2; exit }' "${FRPS_CONFIG}")"
  fi
  if [[ -z "${FRP_TOKEN:-}" ]]; then
    fail "FRP_TOKEN is required unless ${FRPS_CONFIG} already contains auth.token. Generate one with: openssl rand -hex 24"
  fi
}

write_server_config() {
  require_token
  log "Writing frps config to ${FRPS_CONFIG}"
  cat > "${FRPS_CONFIG}" <<EOF
bindAddr = "0.0.0.0"
bindPort = ${FRP_BIND_PORT}
proxyBindAddr = "127.0.0.1"

auth.method = "token"
auth.token = "${FRP_TOKEN}"
EOF
  chmod 600 "${FRPS_CONFIG}"
}

client_config_text() {
  local allow_placeholder="${1:-0}"
  local server_addr="${FRP_SERVER_ADDR:-}"
  if [[ -z "${server_addr}" && "${allow_placeholder}" -eq 1 ]]; then
    server_addr="NEW_CLOUD_PUBLIC_IP"
  fi
  if [[ -z "${server_addr}" ]]; then
    fail "FRP_SERVER_ADDR is required for client config"
  fi
  require_token
  cat <<EOF
serverAddr = "${server_addr}"
serverPort = ${FRP_BIND_PORT}

auth.method = "token"
auth.token = "${FRP_TOKEN}"

[[proxies]]
name = "${FRP_PROXY_NAME}"
type = "tcp"
localIP = "${FRP_LOCAL_SSH_HOST}"
localPort = ${FRP_LOCAL_SSH_PORT}
remotePort = ${FRP_REMOTE_PORT}
EOF
}

write_client_config() {
  log "Writing frpc config to ${FRPC_CONFIG}"
  client_config_text 0 > "${FRPC_CONFIG}"
  chmod 600 "${FRPC_CONFIG}"
}

print_client_config() {
  printf '\n# Local Ubuntu frpc.toml\n'
  client_config_text 1
}

start_server() {
  log "Starting frps. Keep this process running while debugging hardware."
  exec "${FRPS_BIN}" -c "${FRPS_CONFIG}"
}

main() {
  cd "${ROOT_DIR}"
  download_frp

  case "${MODE}" in
    server)
      write_server_config
      if [[ "${WRITE_CLIENT}" -eq 1 ]]; then
        write_client_config
      fi
      if [[ "${PRINT_CLIENT}" -eq 1 ]]; then
        print_client_config
      fi
      if [[ "${START}" -eq 1 ]]; then
        start_server
      fi
      ;;
    client)
      write_client_config
      if [[ "${PRINT_CLIENT}" -eq 1 ]]; then
        print_client_config
      fi
      ;;
  esac

  log "FRP setup complete"
  printf 'Verify after local frpc connects:\n'
  printf '  ssh -p %s ubuntu@127.0.0.1 "hostname && whoami && pwd"\n' "${FRP_REMOTE_PORT}"
}

main "$@"
