#!/usr/bin/env bash
set -euo pipefail

case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
work_dir="$case_dir/output/hour"
pid_file="$work_dir/run.pid"
mkdir -p "$work_dir"

if [[ -s "$pid_file" ]] && kill -0 "$(<"$pid_file")" 2>/dev/null; then
  echo "The hour run is already active as PID $(<"$pid_file")." >&2
  exit 2
fi

nohup "$case_dir/run-hour.sh" >"$work_dir/launcher.log" 2>&1 &
pid=$!
echo "$pid" >"$pid_file"
echo "Started the one-hour model run as PID $pid."
echo "Follow progress with: tail -f $work_dir/run.log"
