#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
common=(
  -DCMAKE_BUILD_TYPE=Release
  -DCMAKE_Fortran_COMPILER=/usr/bin/gfortran-15
  -DCMAKE_Fortran_FLAGS=-I/usr/include/hdf5/serial
)

cmake -S "$repo_dir" -B "$repo_dir/build_serial" "${common[@]}" -DENABLE_MPI=OFF
cmake --build "$repo_dir/build_serial" --target voltron.x --parallel 50

cmake -S "$repo_dir" -B "$repo_dir/build_mpi" "${common[@]}" -DENABLE_MPI=ON
cmake --build "$repo_dir/build_mpi" --target voltron_mpi.x --parallel 50
