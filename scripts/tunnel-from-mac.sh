#!/usr/bin/env bash
# Run this on the Mac. It opens the app that runs on the Ubuntu machine (implementation 08, plan
# section 10.4).
#
#   scripts/tunnel-from-mac.sh              then open http://localhost:5173
#   scripts/tunnel-from-mac.sh ubuntu 5174  another SSH host alias, or another port
#
# One port is enough: the page, the backend (under /api), the audio files and the progress stream
# all go through the Vite server on 5173. The command is the same as typing
#
#   ssh -N -L 5173:localhost:5173 ubuntu
#
# and it stays open until Ctrl-C. `ssh ubuntu` must already work (context/02b-local-setup.md).
set -euo pipefail

host="${1:-ubuntu}"
port="${2:-5173}"

echo "Tunnel to ${host}: open http://localhost:${port} in the browser. Ctrl-C closes it."
exec ssh -N \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -L "${port}:localhost:${port}" \
  "${host}"
