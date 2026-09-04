#!/usr/bin/env bash
set -euo pipefail

case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$case_dir/env.sh"
ranks="${MPI_RANKS:-9}"
if [[ "$ranks" != 9 ]]; then
  echo "This case requires 8 GAMERA ranks plus 1 VOLTRON coordinator rank (MPI_RANKS=9)." >&2
  exit 2
fi

work_dir="$case_dir/output/smoke"
mkdir -p "$work_dir"
cd "$work_dir"
ln -sfn ../../lfmD.h5 lfmD.h5
ln -sfn ../../bcwind.h5 bcwind.h5
ln -sfn ../../raijuconfig.h5 raijuconfig.h5
cp ../../hello-earth-smoke.xml .

mpirun -np "$ranks" --map-by "slot:PE=$OMP_NUM_THREADS" --bind-to core \
  "$KAIJUHOME/build_mpi/bin/voltron_mpi.x" hello-earth-smoke.xml \
  2>&1 | tee run.log

"$case_dir/verify-output.sh" "$work_dir" hello_earth_smoke
