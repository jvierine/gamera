#!/usr/bin/env bash
set -euo pipefail
case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$case_dir/common.sh"
guard_other_run

work="$data_root/baseline"
xml="tail-baseline.xml"
[[ -r "$work/$xml" && -r "$work/bcwind.h5" ]] || { echo "Run prepare-campaign.sh first." >&2; exit 2; }
if [[ -e "$work/run.log" ]] || find "$work" -maxdepth 1 -name 'tail_baseline*.h5' -print -quit | grep -q .; then
  echo "Refusing to overwrite baseline output in $work" >&2
  exit 2
fi
cd "$work"
ln -sfn "$case_dir/../hello-earth/lfmD.h5" lfmD.h5
ln -sfn "$case_dir/../hello-earth/raijuconfig.h5" raijuconfig.h5
printf 'started=%s\nsource_commit=%s\nmpi_ranks=%s\nopenmp_threads=%s\n' \
  "$(date --iso-8601=seconds)" "$(git -C "$KAIJUHOME" rev-parse HEAD)" "$ranks" "$OMP_NUM_THREADS" > provenance.txt
run_mage "$xml"
test "$(find . -maxdepth 1 -name 'tail_baseline*.Res.00000.h5' | wc -l)" -ge 29
date --iso-8601=seconds > COMPLETED
