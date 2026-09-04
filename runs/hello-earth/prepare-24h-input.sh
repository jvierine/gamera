#!/usr/bin/env bash
set -euo pipefail

case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$case_dir/env.sh"
data_dir="${GAMERA_24H_DATA_DIR:-/nfs/urdr/scratch/juha/gamera/hello-earth-24h}"

mkdir -p "$data_dir"
if [[ -e "$data_dir/bcwind.h5" ]]; then
  echo "Refusing to overwrite $data_dir/bcwind.h5" >&2
  exit 2
fi

cd "$data_dir"
cda2wind -t0 2016-08-09T09:00:00 -t1 2016-08-10T10:00:00 \
  -o bcwind.h5 -interp -bx -f107 100 -kp 3
h5dump -H bcwind.h5 >/dev/null
sha256sum bcwind.h5

cat >&2 <<'EOF'
CAUTION: OMNI has a genuine 2016-08-09 09:44--12:02 UTC plasma-data gap
(09:46--11:59 for IMF). Kaipy linearly interpolates it. Keep this limitation
with every scientific interpretation of the run.
EOF
