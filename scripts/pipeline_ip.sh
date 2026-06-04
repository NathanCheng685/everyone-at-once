#!/usr/bin/env bash
# Full offline pipeline for one IP + language (response surface -> infer table).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
IP="${1:?usage: pipeline_ip.sh <ip_id> [lang]}"
LANG="${2:-zh}"
N="${N:-400}"
WORKERS="${WORKERS:-4}"

echo "=== $IP / $LANG (N=$N) ==="
python3 build_response_surface.py --ip "$IP" --lang "$LANG" --n "$N" --workers "$WORKERS"
python3 precompute_posterior_table.py --ip "$IP" --lang "$LANG"
python3 validate_inference.py --ip "$IP" --lang "$LANG" || true
echo "done $IP $LANG"
