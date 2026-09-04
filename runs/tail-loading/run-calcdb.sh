#!/usr/bin/env bash
set -euo pipefail
case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$case_dir/common.sh"
guard_other_run

case_name="${1:-}"
if [[ "$case_name" =~ ^[0-9]+$ ]]; then case_name="$(printf 'tail_pulse_%05ds' "$case_name")"; fi
[[ "$case_name" == tail_control || "$case_name" =~ ^tail_pulse_([0-9]{5})s$ ]] || {
  echo "Usage: $0 {tail_control|10|30|...|7200}" >&2
  exit 2
}
work="$data_root/cases/$case_name"
xml="$case_name-calcdb.xml"
[[ -r "$work/COMPLETED" && -r "$work/$xml" ]] || { echo "$case_name is not complete or lacks $xml" >&2; exit 2; }
[[ -x "$KAIJUHOME/build_serial/bin/calcdb.x" ]] || {
  echo "Missing build_serial/bin/calcdb.x. Build target calcdb.x with at most make -j 50." >&2
  exit 2
}
[[ ! -e "$work/$case_name.deltab.h5" ]] || { echo "Refusing to overwrite existing ground-field output." >&2; exit 2; }
cd "$work"
"$KAIJUHOME/build_serial/bin/calcdb.x" "$xml" 2>&1 | tee calcdb.log
