#!/usr/bin/env bash
set -euo pipefail
case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$case_dir/common.sh"

[[ -d /nfs/urdr/scratch/juha && -w /nfs/urdr/scratch/juha ]] || {
  echo "/nfs/urdr/scratch/juha is unavailable or not writable." >&2
  exit 2
}
"$KAIJUHOME/.venv/bin/python" "$case_dir/generate_campaign.py" --root "$data_root" "$@"
