#!/usr/bin/env bash
set -euo pipefail
case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$case_dir/common.sh"

for name in baseline tail_control tail_pulse_00010s tail_pulse_00030s tail_pulse_00060s tail_pulse_00120s tail_pulse_00240s tail_pulse_00600s tail_pulse_01200s tail_pulse_01800s tail_pulse_03600s tail_pulse_07200s; do
  if [[ "$name" == baseline ]]; then dir="$data_root/baseline"; else dir="$data_root/cases/$name"; fi
  if [[ -r "$dir/COMPLETED" ]]; then state=COMPLETE
  elif [[ -s "$dir/run.log" ]]; then state=STARTED
  elif [[ -r "$dir/bcwind.h5" ]]; then state=PREPARED
  else state=MISSING
  fi
  printf '%-22s %s\n' "$name" "$state"
done
