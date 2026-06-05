#!/usr/bin/env bash
# Wait for the three response-surface builds of a given LANG to finish, then run
# precompute_posterior_table + validate for each (local CPU, no ROG needed).
# Resumable & safe to re-run.  Logs to artifacts/finish_<lang>_pipeline.log.
#
# Usage:  bash scripts/finish_pipeline.sh en
#         bash scripts/finish_pipeline.sh zh
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LANG="${1:?lang (en|zh)}"
IPS=(harry-potter avengers naruto)
LOG="artifacts/finish_${LANG}_pipeline.log"
mkdir -p artifacts

# precompute/validate need sklearn (GP emulator), which lives in .venv — NOT in
# the system python3 used for the build (build only needs numpy/openai). Prefer
# the venv interpreter so the finish step doesn't ModuleNotFoundError on sklearn.
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY=python3

say() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

say "=== finish_pipeline lang=$LANG start (waiting for surfaces) ==="

# 1) Wait until no response-surface build is still running for our IPs+lang.
while :; do
  running=()
  for ip in "${IPS[@]}"; do
    if pgrep -f "build_response_surface.py --ip ${ip} --lang ${LANG}" >/dev/null 2>&1; then
      running+=("$ip")
    fi
  done
  [ ${#running[@]} -eq 0 ] && break
  say "still building (${LANG}): ${running[*]}"
  sleep 60
done
say "all ${LANG} surface builds have exited."

# 2) For each IP: if the surface npz landed, build the posterior table + validate.
fail=0
for ip in "${IPS[@]}"; do
  if [ ! -s "artifacts/${ip}/response_surface_${LANG}.npz" ]; then
    say "SKIP ${ip}: response_surface_${LANG}.npz missing/empty (surface failed?)"
    fail=1
    continue
  fi
  say "--- ${ip}: precompute_posterior_table (${LANG}) ---"
  if "$PY" precompute_posterior_table.py --ip "$ip" --lang "$LANG" >>"$LOG" 2>&1; then
    say "--- ${ip}: validate (${LANG}) ---"
    "$PY" validate_inference.py --ip "$ip" --lang "$LANG" >>"$LOG" 2>&1 || say "validate ${ip} returned nonzero (non-fatal)"
    if [ -s "artifacts/${ip}/infer_table_${LANG}.npz" ]; then
      say "OK ${ip}: infer_table_${LANG}.npz ready ($(du -h "artifacts/${ip}/infer_table_${LANG}.npz" | cut -f1))"
    else
      say "WARN ${ip}: precompute ran but infer_table_${LANG}.npz not found"
      fail=1
    fi
  else
    say "FAIL ${ip}: precompute_posterior_table errored (see log)"
    fail=1
  fi
done

say "=== finish_pipeline lang=$LANG done (exit=$fail) ==="
exit $fail
