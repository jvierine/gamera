#!/usr/bin/env bash
set -euo pipefail

case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export KAIJUHOME="$(cd -- "$case_dir/../.." && pwd)"
export PATH="$KAIJUHOME/.venv/bin:$KAIJUHOME/build_mpi/bin:$KAIJUHOME/build_serial/bin:$PATH"
export OMP_STACKSIZE="${OMP_STACKSIZE:-128M}"
export OMP_NUM_THREADS="${OMP_THREADS:-2}"
export MPLBACKEND="${MPLBACKEND:-Agg}"
data_root="${GAMERA_TAIL_DATA_ROOT:-/nfs/urdr/scratch/juha/gamera/tail-loading-pulses}"
ranks="${MPI_RANKS:-25}"

if [[ "$ranks" != 25 || "$OMP_NUM_THREADS" != 2 ]]; then
  echo "Campaign design requires MPI_RANKS=25 and OMP_THREADS=2 (50 CPU threads)." >&2
  exit 2
fi
for input in "$case_dir/../hello-earth/lfmD.h5" "$case_dir/../hello-earth/raijuconfig.h5"; do
  [[ -r "$input" ]] || { echo "Missing required input: $input" >&2; exit 2; }
done

guard_other_run() {
  local pid_file="/nfs/urdr/scratch/juha/gamera/hello-earth-24h/output/run.pid"
  if [[ -r "$pid_file" ]] && kill -0 "$(<"$pid_file")" 2>/dev/null; then
    echo "Refusing to compete with the active hello-earth 24-hour run (PID $(<"$pid_file"))." >&2
    exit 2
  fi
}

run_mage() {
  local xml="$1"
  mpirun -np "$ranks" --map-by "slot:PE=$OMP_NUM_THREADS" --bind-to core \
    "$KAIJUHOME/build_mpi/bin/voltron_mpi.x" "$xml" 2>&1 | tee run.log
}
