#!/usr/bin/env bash
set -euo pipefail

case_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$case_dir/env.sh"
cd "$case_dir"

for path in lfmD.h5 bcwind.h5 raijuconfig.h5; do
  if [[ -e "$path" ]]; then
    echo "Refusing to overwrite $case_dir/$path; move or remove it first." >&2
    exit 2
  fi
done

genLFM -gid D
cda2wind -t0 2016-08-09T09:00:00 -t1 2016-08-09T11:00:00 \
  -interp -bx -f107 100 -kp 3
genRAIJU

sha256sum lfmD.h5 bcwind.h5 raijuconfig.h5
