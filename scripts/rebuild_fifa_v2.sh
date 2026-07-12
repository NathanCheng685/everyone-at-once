#!/usr/bin/env bash
# FIFA surface rebuild after the 2026-07-11 mbappe/ramos persona sharpening.
# Old (v1-persona) surfaces are archived, checkpoints cleared, then a full
# N=400 rebuild for zh+en against the Ollama box.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p artifacts/fifa/v1-backup
for f in response_surface_zh.jsonl response_surface_en.jsonl response_surface_zh.npz response_surface_en.npz infer_table_zh.npz infer_table_en.npz; do
  [ -f "artifacts/fifa/$f" ] && mv "artifacts/fifa/$f" "artifacts/fifa/v1-backup/$f"
done
N=400 WORKERS=8 bash scripts/pipeline_ip.sh fifa zh
N=400 WORKERS=8 bash scripts/pipeline_ip.sh fifa en
echo "=== fifa v2 rebuild done $(date) ==="
