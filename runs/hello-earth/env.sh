#!/usr/bin/env bash
set -euo pipefail

case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export KAIJUHOME="$(cd -- "$case_dir/../.." && pwd)"
export PATH="$KAIJUHOME/.venv/bin:$KAIJUHOME/build_mpi/bin:$KAIJUHOME/build_serial/bin:$PATH"
export PYTHONPATH="${PYTHONPATH:-}"
export OMP_STACKSIZE="${OMP_STACKSIZE:-128M}"
export OMP_NUM_THREADS="${OMP_THREADS:-4}"
export MPLBACKEND="${MPLBACKEND:-Agg}"
