#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
kaipy_dir="${KAIPY_DIR:-$(cd -- "$repo_dir/.." && pwd)/kaipy}"
kaipy_revision="0028c69c52a91ff378a5798708daaba4cdfb5790"
patch_files=(
  "$repo_dir/patches/kaipy-numpy2-scalar-conversion.patch"
  "$repo_dir/patches/kaipy-mixpic-argparse-help.patch"
  "$repo_dir/patches/kaipy-scipy-griddata-points.patch"
)

if [[ ! -d "$kaipy_dir/.git" ]]; then
  git clone https://github.com/JHUAPL/kaipy.git "$kaipy_dir"
fi

git -C "$kaipy_dir" fetch origin "$kaipy_revision"
git -C "$kaipy_dir" checkout --detach "$kaipy_revision"

for patch_file in "${patch_files[@]}"; do
  if git -C "$kaipy_dir" apply --unidiff-zero --check "$patch_file"; then
    git -C "$kaipy_dir" apply --unidiff-zero "$patch_file"
  elif ! git -C "$kaipy_dir" apply --unidiff-zero --reverse --check "$patch_file"; then
    echo "Kaipy patch is neither applicable nor already applied: $patch_file" >&2
    exit 1
  fi
done

python3 -m venv "$repo_dir/.venv"
"$repo_dir/.venv/bin/python" -m pip install --upgrade pip
"$repo_dir/.venv/bin/python" -m pip install --ignore-requires-python --editable "$kaipy_dir"
"$repo_dir/.venv/bin/python" -m pip install pytplot-mpl-temp pytz psutil
"$repo_dir/.venv/bin/python" -m pip check

echo "Kaipy is ready in $repo_dir/.venv"
