#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_DIR="${SCRIPT_DIR}/.runtime"
BACKEND_LOG="${RUNTIME_DIR}/backend.log"
FRONTEND_LOG="${RUNTIME_DIR}/frontend.log"
BACKEND_PID_FILE="${RUNTIME_DIR}/backend.pid"
FRONTEND_PID_FILE="${RUNTIME_DIR}/frontend.pid"

mkdir -p "${RUNTIME_DIR}"

require_exists() {
  local path="$1"
  if [[ ! -e "${path}" ]]; then
    echo "Missing required path: ${path}" >&2
    exit 1
  fi
}

is_pid_running() {
  local pid="$1"
  if [[ -z "${pid}" ]]; then
    return 1
  fi

  kill -0 "${pid}" 2>/dev/null
}

start_backend() {
  if [[ -f "${BACKEND_PID_FILE}" ]]; then
    local existing_pid
    existing_pid="$(cat "${BACKEND_PID_FILE}" 2>/dev/null || true)"
    if is_pid_running "${existing_pid}"; then
      echo "Backend already running (PID: ${existing_pid})"
      return 0
    fi
    rm -f "${BACKEND_PID_FILE}"
  fi

  setsid bash -lc "cd '${PROJECT_ROOT}/backend' && exec '${PROJECT_ROOT}/backend/venv/bin/python' -m uvicorn app.main:app --reload --port 8000" >"${BACKEND_LOG}" 2>&1 &

  local backend_pid=$!
  echo "${backend_pid}" > "${BACKEND_PID_FILE}"
  echo "Backend started (PID: ${backend_pid})"
}

start_frontend() {
  if [[ -f "${FRONTEND_PID_FILE}" ]]; then
    local existing_pid
    existing_pid="$(cat "${FRONTEND_PID_FILE}" 2>/dev/null || true)"
    if is_pid_running "${existing_pid}"; then
      echo "Frontend already running (PID: ${existing_pid})"
      return 0
    fi
    rm -f "${FRONTEND_PID_FILE}"
  fi

  setsid bash -lc "cd '${PROJECT_ROOT}/frontend' && exec npm run dev -- --host 0.0.0.0" >"${FRONTEND_LOG}" 2>&1 &

  local frontend_pid=$!
  echo "${frontend_pid}" > "${FRONTEND_PID_FILE}"
  echo "Frontend started (PID: ${frontend_pid})"
}

main() {
  require_exists "${PROJECT_ROOT}/backend/venv"
  require_exists "${PROJECT_ROOT}/frontend/package.json"

  start_backend
  start_frontend

  echo
  echo "Backend: http://localhost:8000"
  echo "Frontend: http://localhost:5173"
}

main "$@"
