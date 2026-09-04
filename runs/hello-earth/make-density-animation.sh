#!/usr/bin/env bash
set -euo pipefail

case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$case_dir/env.sh"
work_dir="$case_dir/output/hour"
plot_cpus="${PLOT_CPUS:-16}"
frame_rate="${FRAME_RATE:-10}"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required to encode the animation." >&2
  exit 1
fi

cd "$work_dir"
msphpic -d "$work_dir" -id hello_earth_hour -den -vid -overwrite \
  --ncpus "$plot_cpus"

ffmpeg -y -framerate "$frame_rate" -pattern_type glob \
  -i 'msphVid/msphpic.*.png' -c:v libx264 -pix_fmt yuv420p \
  hello-earth-density.mp4

echo "$work_dir/hello-earth-density.mp4"
