#!/usr/bin/env bash
# Lists the gitignored data of a clone, so two machines can be compared.
#
#   scripts/migrate/manifest.sh [repo-root]            one line per file: <bytes> TAB <path>
#   scripts/migrate/manifest.sh --summary [repo-root]  one line per folder: <files> TAB <bytes> TAB <folder>
#
# The folders come from data-paths.txt. The script runs the same on macOS and on Ubuntu,
# and it can be sent over SSH with no copy on the other side:
#
#   ssh ubuntu 'bash -s -- --summary /path/to/aimpromptu' < scripts/migrate/manifest.sh
#
# In that case the folder list is read from the clone on the other side, which is the
# same file once the repository is pushed.
set -euo pipefail
export LC_ALL=C

summary=0
if [[ "${1:-}" == "--summary" ]]; then
  summary=1
  shift
fi
root="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$root"

paths_file="scripts/migrate/data-paths.txt"
if [[ ! -f "$paths_file" ]]; then
  echo "manifest.sh: $root/$paths_file not found; is $root a clone of aimpromptu?" >&2
  exit 1
fi

grep -vE '^[[:space:]]*(#|$)' "$paths_file" | while IFS= read -r folder; do
  if [[ ! -d "$folder" ]]; then
    if [[ $summary == 1 ]]; then
      printf '0\t0\t%s (missing)\n' "$folder"
    fi
    continue
  fi
  # perl gives the size of a file the same way on both systems (stat does not).
  find "$folder" -type f ! -name .DS_Store ! -path '*/__pycache__/*' -print0 \
    | LC_ALL=C sort -z \
    | perl -0ne 'chomp; printf "%d\t%s\n", -s $_, $_' \
    | if [[ $summary == 1 ]]; then
        awk -F'\t' -v f="$folder" '{n++; b+=$1} END {printf "%d\t%.0f\t%s\n", n, b, f}'
      else
        cat
      fi
done
