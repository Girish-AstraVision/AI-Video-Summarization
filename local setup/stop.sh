#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_DIR="${SCRIPT_DIR}/.runtime"
BACKEND_PID_FILE="${RUNTIME_DIR}/backend.pid"
FRONTEND_PID_FILE="${RUNTIME_DIR}/frontend.pid"

if [[ ! -d "${RUNTIME_DIR}" ]]; then
  echo "Runtime directory not found: ${RUNTIME_DIR}"
  exit 0
fi

stop_process_tree() {
  local pid="$1"
  local label="$2"

  if [[ -z "${pid}" ]]; then
    echo "${label} PID is empty."
    return 0
  fi

  if ! kill -0 "${pid}" 2>/dev/null; then
    echo "${label} is already stopped."
    return 0
  fi

  local children
  children="$(ps -o pid= --ppid "${pid}" 2>/dev/null | tr -d ' ' | tr '\n' ' ' | sed 's/[[:space:]]*$//')"

  if [[ -n "${children}" ]]; then
    for child_pid in ${children}; do
      stop_process_tree "${child_pid}" "${label} child"
    done
  fi

  kill "${pid}" 2>/dev/null || true
  sleep 1

  if kill -0 "${pid}" 2>/dev/null; then
    kill -9 "${pid}" 2>/dev/null || true
  fi

  echo "Stopped ${label} (PID: ${pid})"
}

stop_pid_file() {
  local pid_file="$1"
  local label="$2"

  if [[ ! -f "${pid_file}" ]]; then
    echo "${label} PID file not found."
    return 0
  fi

  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  rm -f "${pid_file}"

  stop_process_tree "${pid}" "${label}"
}

main() {
  stop_pid_file "${BACKEND_PID_FILE}" "Backend"
  stop_pid_file "${FRONTEND_PID_FILE}" "Frontend"
  echo
  echo "Stopped local development services."
}

main "$@"
