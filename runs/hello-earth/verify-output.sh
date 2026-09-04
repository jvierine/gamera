#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 OUTPUT_DIRECTORY RUN_ID" >&2
  exit 2
fi

output_dir="$1"
run_id="$2"
case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$case_dir/env.sh"

"$KAIJUHOME/.venv/bin/python" - "$output_dir" "$run_id" <<'PY'
from pathlib import Path
import sys
import h5py

directory = Path(sys.argv[1]).resolve()
run_id = sys.argv[2]
files = sorted(directory.glob(f"{run_id}*.h5"))
if not files:
    raise SystemExit(f"No HDF5 outputs matching {run_id}*.h5 in {directory}")

for path in files:
    with h5py.File(path, "r") as handle:
        if len(handle.keys()) == 0:
            raise SystemExit(f"Empty HDF5 root: {path}")

log_path = directory / "run.log"
log = log_path.read_text(errors="replace") if log_path.exists() else ""
fatal_markers = ("Segmentation fault", "Fatal Error", "MPI_ABORT", "Traceback")
found = [marker for marker in fatal_markers if marker in log]
if found:
    raise SystemExit(f"Fatal marker(s) in run log: {', '.join(found)}")

print(f"Verified {len(files)} readable, non-empty HDF5 output files in {directory}")
PY
