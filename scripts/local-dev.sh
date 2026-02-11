#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PID_FILE="${ROOT}/.local-server.pid"
LOG_FILE="${ROOT}/.local-server.log"

usage() {
  cat <<EOF
Usage: $0 <start|stop|restart|status|logs>
EOF
}

is_running() {
  if [[ ! -f "$PID_FILE" ]]; then
    return 1
  fi
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -z "${pid}" ]]; then
    return 1
  fi
  if kill -0 "$pid" >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

wait_for_health() {
  local tries=20
  while [[ $tries -gt 0 ]]; do
    if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
    tries=$((tries - 1))
  done
  return 1
}

start_server() {
  if is_running; then
    echo "Local server already running (PID $(cat "$PID_FILE"))."
    return 0
  fi

  nohup "$ROOT/scripts/run-local.sh" --no-build-ui --no-reload >"$LOG_FILE" 2>&1 &
  echo "$!" >"$PID_FILE"

  if is_running && wait_for_health; then
    echo "Local server started: http://127.0.0.1:8000/spearhead/ (PID $(cat "$PID_FILE"))"
    return 0
  fi

  rm -f "$PID_FILE" || true
  echo "Failed to start local server. Last log lines:"
  tail -n 40 "$LOG_FILE" || true
  exit 1
}

stop_server() {
  if ! is_running; then
    rm -f "$PID_FILE" || true
    echo "Local server is not running."
    return 0
  fi

  local pid
  pid="$(cat "$PID_FILE")"
  kill "$pid" >/dev/null 2>&1 || true
  sleep 1
  if kill -0 "$pid" >/dev/null 2>&1; then
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi
  rm -f "$PID_FILE" || true
  echo "Local server stopped."
}

status_server() {
  if is_running; then
    echo "RUNNING pid=$(cat "$PID_FILE") url=http://127.0.0.1:8000/spearhead/"
    return 0
  fi
  rm -f "$PID_FILE" || true
  echo "STOPPED"
}

logs_server() {
  if [[ ! -f "$LOG_FILE" ]]; then
    echo "No log file yet: $LOG_FILE"
    return 0
  fi
  tail -n 80 "$LOG_FILE"
}

ACTION="${1:-}"
case "$ACTION" in
  start)
    start_server
    ;;
  stop)
    stop_server
    ;;
  restart)
    stop_server
    start_server
    ;;
  status)
    status_server
    ;;
  logs)
    logs_server
    ;;
  *)
    usage
    exit 1
    ;;
esac
