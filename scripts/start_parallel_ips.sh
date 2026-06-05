#!/usr/bin/env bash
# Start HP + Avengers + Naruto response-surface builds in parallel.
# ROG Ollama is set to OLLAMA_NUM_PARALLEL=4 — use WORKERS=1–2 per IP (default 2).
#
# Usage:
#   bash scripts/start_parallel_ips.sh          # zh, workers=2 each
#   bash scripts/start_parallel_ips.sh en       # en
#   WORKERS=1 bash scripts/start_parallel_ips.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LANG="${1:-zh}"
export WORKERS="${WORKERS:-2}"

echo "=== parallel builds lang=$LANG workers=$WORKERS per IP ==="
for IP in harry-potter avengers naruto; do
  bash scripts/start_build.sh "$IP" "$LANG"
done
echo ""
echo "monitor:"
echo "  pgrep -fl build_response_surface"
echo "  wc -l artifacts/*/response_surface_${LANG}.jsonl"
echo "  tail -f artifacts/harry-potter_${LANG}_build.log"
