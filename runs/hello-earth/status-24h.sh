#!/usr/bin/env bash
set -euo pipefail

data_dir="${GAMERA_24H_DATA_DIR:-/nfs/urdr/scratch/juha/gamera/hello-earth-24h}"
work_dir="$data_dir/output"
pid="$(cat "$work_dir/run.pid" 2>/dev/null || true)"

if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
  echo "run=RUNNING pid=$pid"
elif [[ -e "$work_dir/COMPLETED" ]]; then
  echo "run=COMPLETED at $(cat "$work_dir/COMPLETED")"
else
  echo "run=STOPPED"
fi
tail -n 25 "$work_dir/run.log" 2>/dev/null || true
du -sh "$work_dir" 2>/dev/null || true
