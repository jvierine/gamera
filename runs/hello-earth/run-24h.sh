#!/usr/bin/env bash
set -euo pipefail

case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export OMP_THREADS="${OMP_THREADS:-5}"
source "$case_dir/env.sh"

data_dir="${GAMERA_24H_DATA_DIR:-/nfs/urdr/scratch/juha/gamera/hello-earth-24h}"
work_dir="$data_dir/output"
ranks="${MPI_RANKS:-25}"

if [[ "$ranks" != 25 ]]; then
  echo "This case requires 24 GAMERA ranks plus 1 VOLTRON coordinator (MPI_RANKS=25)." >&2
  exit 2
fi
if [[ ! -d /nfs/urdr/scratch/juha || ! -w /nfs/urdr/scratch/juha ]]; then
  echo "/nfs/urdr/scratch/juha is unavailable or not writable." >&2
  exit 2
fi
for path in "$data_dir/bcwind.h5" "$case_dir/lfmD.h5" "$case_dir/raijuconfig.h5"; do
  [[ -r "$path" ]] || { echo "Missing required input: $path" >&2; exit 2; }
done
if [[ -e "$work_dir/run.log" ]] || find "$work_dir" -maxdepth 1 -name 'hello_earth_24h*.h5' -print -quit 2>/dev/null | grep -q .; then
  echo "Refusing to overwrite existing 24-hour output in $work_dir" >&2
  exit 2
fi

mkdir -p "$work_dir"
cd "$work_dir"
ln -sfn "$case_dir/lfmD.h5" lfmD.h5
ln -sfn "$data_dir/bcwind.h5" bcwind.h5
ln -sfn "$case_dir/raijuconfig.h5" raijuconfig.h5
cp "$case_dir/hello-earth-24h.xml" .

cat > provenance.txt <<EOF
started=$(date --iso-8601=seconds)
host=$(hostname)
source_commit=$(git -C "$KAIJUHOME" rev-parse HEAD)
kaipy_commit=$(git -C /home/j/src/kaipy rev-parse HEAD)
mpi_ranks=$ranks
openmp_threads=$OMP_NUM_THREADS
data_dir=$data_dir
wind_sha256=$(sha256sum "$data_dir/bcwind.h5" | awk '{print $1}')
warning=OMNI plasma 2016-08-09T09:44--12:02Z and IMF 09:46--11:59Z are linearly interpolated
EOF

mpirun -np "$ranks" --map-by "slot:PE=$OMP_NUM_THREADS" --bind-to core \
  "$KAIJUHOME/build_mpi/bin/voltron_mpi.x" hello-earth-24h.xml \
  2>&1 | tee run.log

"$case_dir/verify-output.sh" "$work_dir" hello_earth_24h
date --iso-8601=seconds > COMPLETED
