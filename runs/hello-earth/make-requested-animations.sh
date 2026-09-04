#!/usr/bin/env bash
set -euo pipefail

case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$case_dir/env.sh"
work_dir="$case_dir/output/hour"
plot_cpus="${PLOT_CPUS:-32}"
frame_rate="${FRAME_RATE:-10}"

cd "$work_dir"
"$case_dir/render-requested-animations.py" \
  --directory "$work_dir" --runid hello_earth_hour --ncpus "$plot_cpus"

for product in density-planes north-convection fac-north fac-south; do
  ffmpeg -y -framerate "$frame_rate" -pattern_type glob \
    -i "requested-frames/$product/$product.*.png" \
    -c:v libx264 -pix_fmt yuv420p "hello-earth-$product.mp4"
done

printf '%s\n' \
  "$work_dir/hello-earth-density-planes.mp4" \
  "$work_dir/hello-earth-north-convection.mp4" \
  "$work_dir/hello-earth-fac-north.mp4" \
  "$work_dir/hello-earth-fac-south.mp4"
