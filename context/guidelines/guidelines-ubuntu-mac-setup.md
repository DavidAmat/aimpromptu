# Mac and Ubuntu

# Executive Summary

My personal computer is a Mac Mini M4, and I also have a ubuntu machine with 64GB
RAM and 32 cores with i9 processor intel. I have 2 SSD, one of 1TB and another called "ssd2" mounted in /mnt/ssd2 with 2TB where I save most of the
heavy stuff like heavy docker images and heavy AI models.  It is really powerful. Sometimes I run AI models locally in my ubuntu using ollama or
llama cpp or vllm and then in m My mac, which I only have 16GB and few storage, I connect to 192.168.0.112 (the local IP of my ubuntu machine) to
run requests there. Bear this in mind. I also run jupyter hub sometimes from my ubuntu machine and access it from my mac with this IP. So you can
see that normally when I develop with an IDE I tend to SSH into "ubuntu" host (this is the name of my etc hosts) and then develop in the SSH mode.
Remember this setup with all these details

# Home machines — LLM context
Short reference for agents working from the Mac and offloading heavy work to the Ubuntu box.
## Roles
| Machine | Role |
| --- | --- |
| **Mac** | Daily driver: IDE (Cursor), planning, light local work, orchestration |
| **Ubuntu (`david-ubuntu`)** | Compute box: GPU/CPU-heavy jobs, Docker, long-running training/inference |
Prefer: design/edit on the Mac → run heavy commands on Ubuntu over SSH → pull results back (or leave artifacts on Ubuntu).
## Mac
> Fill in if missing: model / chip / RAM / disk.
- OS: macOS
- Used for: Cursor/agents, git, SSH into Ubuntu, light scripts
- Not used for: CUDA / NVIDIA workloads (no NVIDIA GPU)
## Ubuntu (`david-ubuntu`)
| | |
| --- | --- |
| OS | Ubuntu 24.04.4 LTS (noble), kernel 6.17 |
| Hostname | `david-ubuntu` |
| User | `david` (sudo, docker group); shell `zsh` |
| CPU | Intel Core i9-14900KF (24 cores / 32 threads) |
| RAM | 64 GB |
| Disk | ~1 TB NVMe (`/` ~937 GB usable) |
| GPU | **NVIDIA GeForce RTX 4090** — 24 GB VRAM, compute capability 8.9 |
| NVIDIA driver | 595.58.03 (reports CUDA **13.2**) |
| CUDA toolkit (optional) | 12.9 under `/usr/local/cuda` |
| LAN IP (typical) | `192.168.0.112` (home Wi‑Fi; may change) |
| Docker | Installed (user in `docker` group) |
| Python tooling | System Python 3.12; **`uv`** commonly used for project envs |
### GPU notes
- Check: `nvidia-smi`
- PyTorch / CUDA workloads should target this machine, not the Mac
- If `nvidia-smi` fails, driver modules may need a reload (e.g. after reboot); do not assume a CPU fallback for GPU jobs
## Access (Mac → Ubuntu)
Normal path: **SSH on the home LAN**.
```bash
ssh david@192.168.0.112
# or, if a Host alias exists in ~/.ssh/config on the Mac:
ssh ubuntu
# ~/.ssh/config file
#Host ubuntu
#  HostName 192.168.0.112
#  User david
#  IdentityFile ~/.ssh/id_ubuntu
#  IdentitiesOnly yes
#  AddKeysToAgent yes
#  UseKeychain yes
```
- Auth: SSH keys (`authorized_keys` on Ubuntu)
- Same home network required unless VPN/port-forward is set up
- After connect: work under `/home/david/...` (e.g. `Documents/dev/...`)
Useful remote patterns:
```bash
ssh david@192.168.0.112 'hostname && nvidia-smi -L'
ssh david@192.168.0.112 'cd /path/to/project && <command>'
```
Long jobs: run in a durable session on Ubuntu (`tmux`/`screen` or a background process), not a fragile one-shot SSH that dies if the laptop sleeps.
## How agents should behave
1. Assume the **Mac session cannot run NVIDIA/CUDA** jobs.
2. For GPU, large training, embedding generation, Docker GPU, or multi-hour work: **give commands for Ubuntu** (via SSH), or run them only when already on that host.
3. Prefer **short smoke tests** first; leave long runs to the user to monitor in an Ubuntu terminal.
4. Keep secrets (tokens, `.env`) on the machine that needs them; do not invent upload/sync unless asked.
5. Paths differ per machine — always confirm `pwd` / project root on Ubuntu before running.
## Quick health checks (Ubuntu)
```bash
nvidia-smi
docker run --rm hello-world   # optional
uv --version
```

# Storage SSD

# Home storage — LLM context
Where large data and Docker live. Companion to `home-machines.md`.
## Policy
| Workload | Preferred machine / disk |
| --- | --- |
| Heavy Docker images, GPU caches, big datasets, long artifacts | **Ubuntu** |
| Light Mac work that needs space | **Mac DevSSD** (not the internal 228 Gi disk) |
Do not fill the Mac internal Data volume (often near full). Prefer paths under `Documents/` when storing on the Mac.
---
## Mac
| Volume | Size (approx) | Mount | Role |
| --- | --- | --- | --- |
| Internal APFS | ~228 Gi | `/` + `/System/Volumes/Data` | System + default user data — **tight**; avoid large stores |
| **DevSSD** (external SSD) | ~931 Gi | `/Volumes/DevSSD` | Extra project/dev storage |
### DevSSD + `Documents` symlink
On the Mac, work that needs disk space should live under a tree that ultimately sits on **DevSSD**. In practice:
- `~/Documents` (or a folder under it) is a **`ln -s`** into `/Volumes/DevSSD/...`
- Paths still look like `~/Documents/...` in the IDE; bytes are on the external volume
- If DevSSD is unplugged/unmounted, those paths break — remount before working
**Rule for agents on Mac:** put bulky local folders under `Documents/` (DevSSD-backed). Do not dump Docker images or multi‑GB caches onto the internal disk.
---
## Ubuntu (`david-ubuntu`) — two NVMe SSDs
| Disk | Device (typical) | Size | Mount | Role |
| --- | --- | --- | --- | --- |
| SSD 1 | `/dev/nvme1n1p2` | ~1 TB (~937 G usable) | `/` | OS, home (`/home/david`), default project trees under `Documents/dev/...` |
| SSD 1 EFI | `/dev/nvme1n1p1` | ~1.1 G | `/boot/efi` | Boot |
| **SSD 2** | `/dev/nvme0n1p1` | ~2 TB (~1.9 T) | **`/mnt/ssd2`** | Bulk: Docker-related data, HF caches, models, large project copies |
Example layout under `/mnt/ssd2` (illustrative): `docker`, `hf`, `ollama`, `wallapop`, etc.
### Guidance
1. **Default code** may live on `/` (e.g. `/home/david/Documents/dev/...`).
2. **Heavy Docker / model / dataset bulk** → prefer **`/mnt/ssd2`** (configure Docker data-root or bind mounts / symlinks there when needed).
3. Check free space before big pulls: `df -h / /mnt/ssd2`.
```bash
df -h / /mnt/ssd2
ls /mnt/ssd2
```
---
## Quick comparison
| | Mac internal | Mac DevSSD | Ubuntu `/` | Ubuntu `/mnt/ssd2` |
| --- | --- | --- | --- | --- |
| Size | ~228 Gi | ~931 Gi | ~1 TB | ~2 TB |
| Use for | System / light | Dev work via `Documents` symlink | OS + normal repos | Docker + large assets |

**Important Note**:  let's use the 2TB SSD, a specific folder there to put all the KB documents we generate, the temporal files, consolidated docs, the embeddings for vector database, etc... Everything should be designed to be portable so that if we move this to another computer, all the services are containers and the database (KB) is portable by moving the files via a file transfer or external disk transfers. 