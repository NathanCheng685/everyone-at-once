#!/usr/bin/env bash
# Build all three new IPs (zh then en). Resumable; logs under artifacts/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LOG=artifacts/pipeline_all.log
mkdir -p artifacts
exec > >(tee -a "$LOG") 2>&1

echo "=== pipeline start $(date) ==="
for IP in harry-potter avengers naruto; do
  for LANG in zh en; do
    echo "--- $IP / $LANG ---"
    bash scripts/pipeline_ip.sh "$IP" "$LANG"
  done
done
echo "=== pipeline done $(date) ==="
