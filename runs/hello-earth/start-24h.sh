#!/usr/bin/env bash
set -euo pipefail

case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
data_dir="${GAMERA_24H_DATA_DIR:-/nfs/urdr/scratch/juha/gamera/hello-earth-24h}"
mkdir -p "$data_dir/output"

pid_file="$data_dir/output/run.pid"
if [[ -s "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
  echo "24-hour run is already active as PID $(cat "$pid_file")" >&2
  exit 2
fi

nohup "$case_dir/run-24h.sh" > "$data_dir/output/launcher.log" 2>&1 &
pid=$!
echo "$pid" > "$pid_file"
echo "Started 24-hour run as PID $pid"
echo "Log: $data_dir/output/run.log"
