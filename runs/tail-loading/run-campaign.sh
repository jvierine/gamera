#!/usr/bin/env bash
set -euo pipefail
case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$case_dir/common.sh"
guard_other_run

[[ -r "$data_root/manifest.json" ]] || { echo "Run prepare-campaign.sh first." >&2; exit 2; }
if [[ ! -r "$data_root/baseline/COMPLETED" ]]; then
  "$case_dir/run-baseline.sh"
fi
for duration in control 10 30 60 120 240 600 1200 1800 3600 7200; do
  if [[ "$duration" == control ]]; then runid=tail_control; else runid="$(printf 'tail_pulse_%05ds' "$duration")"; fi
  if [[ -r "$data_root/cases/$runid/COMPLETED" ]]; then
    echo "Skipping completed $runid"
  else
    "$case_dir/run-case.sh" "$duration"
  fi
done
