#!/usr/bin/env bash
# Detached long-run builder (survives closing the launching terminal).
# Usage: ./scripts/start_build.sh harry-potter zh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
IP="${1:?ip_id}"
LANG="${2:?lang}"
LOG="artifacts/${IP}_${LANG}_build.log"
mkdir -p "artifacts/${IP}"

if pgrep -f "build_response_surface.py --ip ${IP} --lang ${LANG}" >/dev/null 2>&1; then
  echo "already running for ${IP} ${LANG}"
  pgrep -fl "build_response_surface.py --ip ${IP}"
  exit 0
fi

nohup caffeinate -dimsu env PYTHONUNBUFFERED=1 \
  python3 build_response_surface.py --ip "$IP" --lang "$LANG" --n 400 --workers 4 \
  >>"$LOG" 2>&1 </dev/null &
disown -h $! 2>/dev/null || true
echo "started PID $!  log=$LOG"
sleep 2
pgrep -fl "build_response_surface.py --ip ${IP}" || { echo "failed to stay up; tail log:"; tail -20 "$LOG"; exit 1; }
