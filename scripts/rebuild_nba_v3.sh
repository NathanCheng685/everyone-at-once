#!/usr/bin/env bash
# NBA surface rebuild after the 2026-07-11 giannis persona v3 (anti-jokic axes).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p artifacts/nba/v2-backup
for f in response_surface_zh.jsonl response_surface_en.jsonl response_surface_zh.npz response_surface_en.npz infer_table_zh.npz infer_table_en.npz; do
  [ -f "artifacts/nba/$f" ] && mv "artifacts/nba/$f" "artifacts/nba/v2-backup/$f"
done
N=400 WORKERS=8 bash scripts/pipeline_ip.sh nba zh
N=400 WORKERS=8 bash scripts/pipeline_ip.sh nba en
echo "=== nba v2 rebuild done $(date) ==="
