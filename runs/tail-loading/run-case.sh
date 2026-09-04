#!/usr/bin/env bash
set -euo pipefail
case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$case_dir/common.sh"
guard_other_run

duration="${1:-}"
if [[ "$duration" == control ]]; then
  runid="tail_control"
  pulse_value=0
elif [[ "$duration" =~ ^(10|30|60|120|240|600|1200|1800|3600|7200)$ ]]; then
  runid="$(printf 'tail_pulse_%05ds' "$duration")"
  pulse_value="$duration"
else
  echo "Usage: $0 {control|10|30|60|120|240|600|1200|1800|3600|7200}" >&2
  exit 2
fi
work="$data_root/cases/$runid"
xml="$runid.xml"
[[ -r "$data_root/baseline/COMPLETED" ]] || { echo "Baseline is not complete." >&2; exit 2; }
[[ -r "$work/$xml" && -r "$work/bcwind.h5" ]] || { echo "Run prepare-campaign.sh first." >&2; exit 2; }
if [[ -e "$work/run.log" ]] || find "$work" -maxdepth 1 -name "$runid*.h5" -print -quit | grep -q .; then
  echo "Refusing to overwrite case output in $work" >&2
  exit 2
fi
cd "$work"
ln -sfn "$case_dir/../hello-earth/lfmD.h5" lfmD.h5
ln -sfn "$case_dir/../hello-earth/raijuconfig.h5" raijuconfig.h5
for restart in "$data_root"/baseline/tail_baseline*.Res.00000.h5; do
  [[ -e "$restart" ]] || { echo "Baseline restart set is incomplete." >&2; exit 2; }
  ln -sfn "$restart" "$(basename "$restart")"
done
test "$(find . -maxdepth 1 -name 'tail_baseline*.Res.00000.h5' | wc -l)" -ge 29
printf 'started=%s\nsource_commit=%s\npulse_duration_s=%s\nmpi_ranks=%s\nopenmp_threads=%s\n' \
  "$(date --iso-8601=seconds)" "$(git -C "$KAIJUHOME" rev-parse HEAD)" "$pulse_value" "$ranks" "$OMP_NUM_THREADS" > provenance.txt
run_mage "$xml"
date --iso-8601=seconds > COMPLETED
