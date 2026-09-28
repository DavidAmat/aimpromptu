#!/usr/bin/env bash
# Copies the gitignored data of this clone (the Mac) into a clone on the Ubuntu machine.
#
#   scripts/migrate/push-data-to-ubuntu.sh <ubuntu-repo-path> [ssh-host]
#
#   <ubuntu-repo-path>  the absolute path of the aimpromptu clone on Ubuntu,
#                       for example /home/david/Documents/projects/music/aimpromptu
#   [ssh-host]          the SSH alias of the Ubuntu machine, "ubuntu" by default
#
# The folders are listed in data-paths.txt. The copy uses rsync, so running it a second
# time copies only what changed or what an interrupted run did not finish. It never
# deletes a file on Ubuntu. At the end it compares the file list and the sizes of both
# sides with manifest.sh, and prints the count and the size of each folder.
set -euo pipefail
export LC_ALL=C

if [[ $# -lt 1 || "$1" == -h || "$1" == --help ]]; then
  sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
fi
dest="${1%/}"
host="${2:-ubuntu}"

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
cd "$root"

if [[ "$dest" != /* || "$dest" == *" "* ]]; then
  echo "The Ubuntu path must be absolute and have no spaces: $dest" >&2
  exit 1
fi

echo "== Checking that $host:$dest is a clone of aimpromptu"
if ! ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" "test -f '$dest/scripts/migrate/data-paths.txt'"; then
  echo "$host:$dest/scripts/migrate/data-paths.txt was not found." >&2
  echo "Clone the repository on Ubuntu first (git clone git@github.com:DavidAmat/aimpromptu.git)," >&2
  echo "and make sure the clone has this commit (git pull)." >&2
  exit 1
fi

folders=()
while IFS= read -r folder; do
  if [[ -d "$folder" ]]; then
    folders+=("$folder")
  else
    echo "   (skipped, not on this machine: $folder)"
  fi
done < <(grep -vE '^[[:space:]]*(#|$)' scripts/migrate/data-paths.txt)

echo "== Copying ${#folders[@]} folders to $host:$dest"
# -a keeps times and permissions, so a second run skips every file that did not change.
# -R keeps each folder's path under the repository root.
# --partial keeps a half-copied file, so an interrupted run continues where it stopped.
rsync -a -R --partial --stats \
  --exclude .DS_Store --exclude __pycache__ \
  "${folders[@]}" "$host:$dest/"

echo
echo "== Comparing the Mac and Ubuntu"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
"$here/manifest.sh" "$root" > "$tmp/mac.tsv"
ssh "$host" "bash -s -- '$dest'" < "$here/manifest.sh" > "$tmp/ubuntu.tsv"

"$here/manifest.sh" --summary "$root" > "$tmp/mac-summary.tsv"
printf '%8s  %10s  %s\n' files MB folder
awk -F'\t' '{printf "%8d  %10.1f  %s\n", $1, $2/1e6, $3; n+=$1; b+=$2}
            END {printf "%8d  %10.1f  %s\n", n, b/1e6, "TOTAL on the Mac"}' "$tmp/mac-summary.tsv"
awk -F'\t' '{n++; b+=$1} END {printf "%8d  %10.1f  %s\n", n, b/1e6, "TOTAL on Ubuntu (same folders)"}' "$tmp/ubuntu.tsv"

missing="$(comm -23 <(LC_ALL=C sort "$tmp/mac.tsv") <(LC_ALL=C sort "$tmp/ubuntu.tsv") | wc -l | tr -d ' ')"
if [[ "$missing" == 0 ]]; then
  echo
  echo "OK: every file of the Mac is on Ubuntu with the same size."
else
  echo
  echo "NOT COMPLETE: $missing files of the Mac are missing on Ubuntu or have another size. The first ones:"
  comm -23 <(LC_ALL=C sort "$tmp/mac.tsv") <(LC_ALL=C sort "$tmp/ubuntu.tsv") | head -10
  echo "Run the script again: it copies only what is missing."
  exit 2
fi
