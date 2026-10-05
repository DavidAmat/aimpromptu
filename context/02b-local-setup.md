# Local setup: Mac Mini M4 + Ubuntu compute box

This document describes the home development environment. It is for a person or an AI agent that starts with no prior knowledge of these machines.

The environment is a pair of machines on the same Wi-Fi network:

- A **Mac mini M4** is the daily workstation (Cursor, git, planning, light local work).
- An **Ubuntu desktop** (`david-ubuntu`) is the compute box (GPU, Docker image storage, large models, long jobs).

The Mac has limited RAM and a small internal disk. The Ubuntu machine has a strong CPU, 64 GB of RAM, an NVIDIA RTX 4090, and much more disk. The default pattern is: edit on the Mac, run heavy work on Ubuntu over SSH.

**AImpromptu is the exception.** Since implementation 08 (October 2026) the whole project lives and runs on Ubuntu: the code, the data, the containers, and the IDE session of the agent. The Mac is only the browser, and it reaches the app through one SSH tunnel. Section 12 describes this way of working.

---

## 1. How the two machines relate

| Machine | Role | What belongs here |
| --- | --- | --- |
| Mac mini M4 | Daily driver | IDE, git, SSH orchestration, light scripts, local files that need Mac bind-mounts |
| Ubuntu (`david-ubuntu`) | Compute box | NVIDIA/CUDA jobs, Docker images and builds, Ollama/vLLM/llama.cpp, ComfyUI, large datasets |

Rules:

1. The Mac cannot run NVIDIA/CUDA work.
2. Default Docker on the Mac talks to the Ubuntu Docker daemon. Images and containers live on Ubuntu, not on the Mac.
3. Use Colima on the Mac only when a container must mount files that exist on the Mac (example: a local `supabase/` folder).
4. Do not store large files on the Mac internal disk. Use DevSSD paths (usually via `~/Documents/...`).
5. On Ubuntu, keep large assets on `/mnt/ssd2`. Keep normal code under `/home/david/Documents/...` unless the project is already on SSD2.

---

## 2. Network and how to reach Ubuntu

Both machines are on the home Vodafone Wi-Fi.

The Ubuntu LAN IP is **fixed** at `192.168.0.112`. This is a DHCP reservation in the Vodafone Station router (`192.168.0.1`, expert mode, LAN static DHCP). The reservation name is `Ubuntu-AI`. The Wi-Fi MAC is `c8:5e:a9:c7:01:32` (interface `wlp0s20f3`).

On the Mac, `/etc/hosts` maps several names to that IP:

```
192.168.0.112  ubuntu
192.168.0.112  glasic.local
192.168.0.112  dev-glasic.com
```

SSH from the Mac:

```bash
ssh ubuntu
# equivalent:
ssh david@192.168.0.112
```

Mac `~/.ssh/config` host `ubuntu`:

- HostName: `192.168.0.112`
- User: `david`
- IdentityFile: `~/.ssh/id_ubuntu`

There is a second alias `ubuntu-hubadmin` (same IP, user `hubadmin`) for JupyterHub-style admin access.

The SSH server on Ubuntu is enabled and persistent. After connect, the user is `david`, shell is `zsh`, home is `/home/david`. The user is in the `docker` and `sudo` groups.

Long jobs on Ubuntu should run in `tmux`/`screen` or as a background process. A one-shot SSH command dies if the Mac sleeps.

Useful checks:

```bash
ssh ubuntu 'hostname && nvidia-smi -L'
ssh ubuntu 'cd /path/to/project && <command>'
```

Remote services that are sometimes used from the Mac, via `192.168.0.112`:

- Docker daemon on TCP port **2375** (unauthenticated, LAN only)
- A process currently listens on port **8000** (used for local hubs / app frontends)
- Ollama and other local model servers when they are started

---

## 3. Mac mini M4

| Item | Value |
| --- | --- |
| Model | Mac mini (Mac16,10) |
| Chip | Apple M4, 10 CPU cores (4 performance + 6 efficiency), 10 GPU cores |
| RAM | 16 GB |
| OS | macOS 26.6.2 |
| User | `david` |
| NVIDIA | None. No CUDA. |

### Disks

| Volume | Size | Mount | Free (approx) | Role |
| --- | --- | --- | --- | --- |
| Internal APFS | 228 Gi | `/` and `/System/Volumes/Data` | Data volume ~26 Gi free (about 87% used) | System and default user data. Tight. Avoid large stores. |
| DevSSD | 931 Gi | `/Volumes/DevSSD` | ~839 Gi free | Project and tool storage |

The internal Data volume is often close to full. Agents must not write multi-GB caches, models, or Docker data there.

### Acasis enclosure

DevSSD is an external NVMe inside an **ACASIS M002Pro** Thunderbolt enclosure, connected at 40 Gb/s. The volume appears as `/Volumes/DevSSD`. If the enclosure is unplugged, every symlink that targets DevSSD breaks until the volume is mounted again.

---

## 4. Mac storage layout and symlinks

`~/Documents` itself is a normal folder on the internal disk. The large work trees inside it are **symlinks** to DevSSD. Several home-dot folders are also symlinks, so tool caches do not fill the internal disk.

### Home (`~`) symlinks to DevSSD

| Path on Mac | Target |
| --- | --- |
| `~/.colima` | `/Volumes/DevSSD/.colima` |
| `~/.lmstudio` | `/Volumes/DevSSD/.lmstudio` |
| `~/.vscode` | `/Volumes/DevSSD/home/.vscode` |
| `~/.gemini` | `/Volumes/DevSSD/home/.gemini` |
| `~/.antigravity` | `/Volumes/DevSSD/home/.antigravity` |
| `~/Pictures/Photos Library.photoslibrary` | `/Volumes/DevSSD/Pictures/Photos Library.photoslibrary` |

`~/Desktop/test_internal_folder` is an old test symlink and can be ignored.

### `~/Documents` symlinks to DevSSD

These are the main project folders. Paths still look like `~/Documents/work/...` in the IDE. Bytes live on DevSSD.

| Path | Target |
| --- | --- |
| `~/Documents/dev` | `/Volumes/DevSSD/Documents/dev` |
| `~/Documents/work` | `/Volumes/DevSSD/Documents/work` |
| `~/Documents/projects` | `/Volumes/DevSSD/Documents/projects` |
| `~/Documents/repos` | `/Volumes/DevSSD/Documents/repos` |
| `~/Documents/utils` | `/Volumes/DevSSD/Documents/utils` |
| `~/Documents/storage` | `/Volumes/DevSSD/Documents/storage` |
| `~/Documents/media` | `/Volumes/DevSSD/Documents/media` |

### `~/Documents` folders that stay on the internal disk

These are small or app-managed and are **not** symlinked:

- `Codex/`
- `icons/`
- `MuseScore3/`, `MuseScore4/`
- `Obsidian/`, `Obsidian Vault/`
- `other/`
- `screenshots/`

### DevSSD root (what lives only on the SSD)

```
/Volumes/DevSSD/
  Documents/     # target of the Documents symlinks above (~34 G)
  home/          # .vscode, .gemini, .antigravity
  Pictures/      # Photos library
  Claude/        # VM bundles
  .colima/       # local Docker VM state (~23 G)
  .lmstudio/     # local LM Studio data (~9 G)
```

---

## 5. Mac `Documents/` structure (two levels)

Convention:

- `work/` — paid client / company repos
- `dev/` — personal experiments and side development
- `projects/` — product-style personal or client-adjacent apps
- `repos/` — cloned libraries and reference code
- `utils/` — setup scripts and templates
- `storage/` — bulky files that are not source trees
- `media/` — books and extra screenshots

```
~/Documents/
  work/                  -> DevSSD
    glasic/
    nova_hiring/
    wallapop/
  dev/                   -> DevSSD
    ai/
    glovo_dev/
    ios/
    learning/
    prompts/
    tasks/
    wallapop_dev/
    world-cup-sweepstake/
  projects/              -> DevSSD
    ai/
    archive/
    backend/
    board-ai/
    daocb/
    frontend/
    mlp-demo/
    mlp-gitops/
    music/
    news-digest/
    portfolio/
    squadeat/
  repos/                 -> DevSSD
    external/
    internal/
    llms/
  utils/                 -> DevSSD
    ai/
    coding/
    setup/
    uni/
  storage/               -> DevSSD
    glasic/
  media/                 -> DevSSD
    books/
    screenshots/
  Codex/
  icons/
  Obsidian/
  Obsidian Vault/
  other/
  screenshots/
```

Notable `work/` contents:

- `work/glasic/` — Glasic Lab (admin app, iOS app, security case)
- `work/nova_hiring/` — Nova Hiring (API, front, interview, worker, AWS infra)
- `work/wallapop/` — Wallapop ML platform and case material

`~/Documents/projects/squadeat/` contains a `supabase/` directory. That is the canonical example of a Mac-local folder that must be bind-mounted into Docker.

---

## 6. Ubuntu machine (`david-ubuntu`)

| Item | Value |
| --- | --- |
| OS | Ubuntu 24.04.4 LTS (noble), kernel reported as 7.0.0-34-generic in `uname` (October 2026) |
| Hostname | `david-ubuntu` |
| User | `david` (sudo, docker, ollama groups), shell `zsh` |
| CPU | Intel Core i9-14900KF, 24 cores / 32 threads, up to 6.0 GHz |
| RAM | 64 GB (~62 Gi visible), 8 GB swap |
| GPU | NVIDIA GeForce RTX 4090, 24 GB VRAM, compute capability 8.9 |
| NVIDIA driver | 595.58.03, reports CUDA **13.2** |
| CUDA toolkit | 12.9 at `/usr/local/cuda` (symlink to `/usr/local/cuda-12.9`) |
| Python | System Python 3.12. Project environments often use `uv` |
| Other local AI | Ollama, llama.cpp GGUF files, vLLM images, ComfyUI, LM Studio models |

GPU check: `nvidia-smi`. If it fails after a reboot, driver modules may need a reload. Do not silently fall back to CPU for GPU jobs.

The BIOS was updated to version 1836 (Intel Default Settings) on 2026-09-29. Before that, the i9-14900KF crashed under load ("invalid opcode", machine check errors), which is the known instability of Intel 13th and 14th generation processors. After a BIOS reset, check that the Intel Default Settings are still selected.

ComfyUI currently runs from `/mnt/ssd2/image-generation/ComfyUI`.

### Disks

| Disk | Device | Size | Mount | Role |
| --- | --- | --- | --- | --- |
| SSD 1 (Predator GM7) | `/dev/nvme1n1p2` | ~1 TB (~937 G usable) | `/` | OS, `/home/david`, default `Documents/` trees |
| SSD 1 EFI | `/dev/nvme1n1p1` | ~1.1 G | `/boot/efi` | Boot |
| SSD 2 (HP FX700) | `/dev/nvme0n1p1` | ~2 TB (~1.9 T usable) | `/mnt/ssd2` | Docker data-root, models, datasets, heavy copies |
| HDD (WDC) | `/dev/sda` | 4.5 T | **not mounted** | Present in the machine, unused in the current layout |

Current free space (approx): `/` 601 G free of 937 G; `/mnt/ssd2` 1.3 T free of 1.9 T (about 456 G used).

`/mnt/ssd2` is in fstab with `defaults,nofail`. Shortcut from Documents: `~/Documents/ssd` -> `/mnt/ssd2`.

LM Studio models: `~/.lmstudio/models` -> `/mnt/ssd2/lms`.

---

## 7. Ubuntu `Documents/` structure (two levels)

Code that is not huge lives on SSD 1 under `/home/david/Documents`.

```
/home/david/Documents/
  dev/
    ai/                      # gemma-4, nemotron-content-safety
    task-manager/
    wallapop_dev/            # chat-moderation
  work/
    glasic/
      glasic-admin-app/
  projects/
    knowledge-base/
    music/
      aimpromptu/            # this project (git: github.com:DavidAmat/aimpromptu)
      vexflow-v2/            # @aimpromptu/grid-notation, must sit beside aimpromptu
      muscriptor/            # MuScriptor's own repository, for reference and its tools
  utils/
    zsh-autosuggestions/
    zsh-syntax-highlighting/
  migration/
  ssd -> /mnt/ssd2
```

This tree is smaller than the Mac `Documents/` tree. Heavy Wallapop datasets, Hugging Face caches, Ollama blobs, and Docker data are on SSD 2.

---

## 8. Ubuntu SSD 2 (`/mnt/ssd2`) structure

SSD 2 is the bulk disk. Approximate sizes:

| Path | Size | Purpose |
| --- | --- | --- |
| `/mnt/ssd2/docker` | live Docker data-root (root-owned; `docker system df` is the right way to measure it) | Images, containers, volumes, build cache |
| `/mnt/ssd2/docker_bk` | ~116 G | Old Docker data backup |
| `/mnt/ssd2/hf` | ~84 G | Hugging Face cache and model checkouts. `hf/data/hub` holds the MuScriptor weights (5.5 GB for `large`), which the AImpromptu backend container mounts |
| `/mnt/ssd2/aimpromptu` | ~0.2 G | AImpromptu's backend container home: the ByteDance checkpoint and the torch cache |
| `/mnt/ssd2/ollama` | ~73 G | Ollama blobs/manifests |
| `/mnt/ssd2/image-generation` | ~44 G | ComfyUI and its HF cache |
| `/mnt/ssd2/lms` | ~34 G | LM Studio models |
| `/mnt/ssd2/wallapop` | ~32 G | Wallapop image-moderation datasets and code |
| `/mnt/ssd2/MIGRATOR_HP` | ~29 G | Migration leftovers from a previous machine |
| `/mnt/ssd2/llamacpp` | ~12 G | GGUF models (example: gpt-oss-20b) |
| `/mnt/ssd2/whisper` | ~6 G | faster-whisper model + whisper.cpp |
| `/mnt/ssd2/codebases` | ~1 G | Wallapop/subhydra source checkouts |
| `/mnt/ssd2/minikube` | ~0.8 G | Minikube cache |
| `/mnt/ssd2/glasic` | ~0.7 G | Glasic MySQL data / migrations |
| `/mnt/ssd2/glasic_toy` | ~0.2 G | Smaller Glasic MySQL toy instance |
| `/mnt/ssd2/local-kb` | ~0.1 G | Local knowledge-base data, models, runtime |

High-level tree (3–4 levels, Docker internals omitted):

```
/mnt/ssd2/
  docker/                    # live Docker data-root (see section 9)
  docker_bk/                 # backup of a previous Docker graph
  hf/
    data/hub/                # huggingface hub cache
    Llama-3.2-1B/
    Llama-3.2-3B-Instruct/
  ollama/
    blobs/
    manifests/registry.ollama.ai/library/
  lms/
    lmstudio-community/
    orcarouter/
  image-generation/
    ComfyUI/
    hf-cache/
  llamacpp/                  # GGUF files
  whisper/
    models--Systran--faster-whisper-large-v3/
    whisper.cpp/
  wallapop/
    image-moderation/        # datasets, notebooks, src, venv
  codebases/
    subhydra/
      core-chat/
      cx-llm-common/
      kb_brain/
      llm-client/
      nlp-pipeline/
      nlp-research/
      overhydra-playground/
      overhydra-ui-kit/
      subhydra-chat/
      subhydra-ui-kit/
  glasic/
    migrations/
    mysql/                   # erp_dev, erp_prod, metabase, ...
    tables/
  glasic_toy/
    migrations/
    mysql/
  local-kb/
    backups/ data/ export/ input/ models/ runtime/
  minikube/
  MIGRATOR_HP/               # historical home/dotfile dump
```

`df -h / /mnt/ssd2` before large pulls.

---

## 9. Docker: Ubuntu by default, Colima only when the Mac must mount files

### Why this split exists

The Mac has 16 GB RAM and a 228 Gi internal disk. Docker images in this environment are large. On Ubuntu, `docker system df` currently reports about:

- **56 images**, **170.8 GB**
- **19 containers**, ~0.7 GB
- **22 volumes**, **34 GB**
- **434 build-cache entries**, **117.5 GB**

Large images include `vllm/vllm-openai` (~38.5 GB), `nemotron-batch` (~38.5 GB), Glasic frontend/backend/web images, a full local Supabase stack, Metabase, Qdrant, and CUDA bases.

Those layers belong on Ubuntu SSD 2, not on the Mac.

### Default path (Mac CLI -> Ubuntu daemon)

On the Mac, `~/.zshrc` sets:

```bash
export DOCKER_HOST="tcp://192.168.0.112:2375"
```

Docker contexts:

| Context | Endpoint | Use |
| --- | --- | --- |
| `default` (active) | `tcp://192.168.0.112:2375` | Remote daemon on Ubuntu |
| `colima` | `unix:///Users/david/.colima/default/docker.sock` | Local daemon in a Colima VM |

`docker` / `docker compose` on the Mac therefore create images and containers **on Ubuntu**. Storage root on Ubuntu:

```json
{
  "data-root": "/mnt/ssd2/docker",
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
}
```

NVIDIA runtime is also registered in that daemon.json. GPU containers belong on Ubuntu.

Port 2375 is unauthenticated TCP. It is acceptable on this trusted LAN. It must never be exposed to the internet.

**Bind-mount rule for this mode:** the daemon sees Ubuntu filesystems. A compose file that mounts `./supabase` from the Mac will not see those files. Use Ubuntu paths, or use Colima.

### Colima path (local Docker on the Mac)

Use Colima when a container must read or write files that exist only on the Mac. The working example is **Squadeat + Supabase**: the local `supabase/` folder (migrations and seed data) must be mounted into the Supabase containers, so the daemon has to run on the Mac.

Colima state lives on DevSSD (`~/.colima` -> `/Volumes/DevSSD/.colima`). It is **not running** unless started.

Helper aliases in `~/.zshrc`:

```bash
alias colima_start="colima start --runtime docker --memory 10 --cpu 8 --disk 100"
alias colima_stop="colima stop"
```

The persisted Colima profile currently uses 4 CPU, 8 GB RAM, 60 GB disk, `aarch64`, Docker runtime. It already mounts:

```yaml
mounts:
  - location: /Volumes/DevSSD/Documents/projects/squadeat
    writable: true
```

Run against Colima without changing the global `DOCKER_HOST`:

```bash
colima start          # if it is stopped
docker --context colima ps
docker --context colima compose up
```

After Colima work, leave the default context / `DOCKER_HOST` pointing at Ubuntu so later `docker build` / `docker pull` do not fill the Mac.

---

## 10. SSH keys and git identity (freelancer / multi-client)

David is a freelancer. Each client may require a different GitHub (or Bitbucket) account. Agents must pick the SSH host alias that matches the client, not the default `github.com` key.

Clone form:

```bash
git clone git@<ssh-host-alias>:<org>/<repo>.git
```

Then set `user.email` / `user.name` in that repo to the matching identity.

### Mac (`~/.ssh/`)

| Host alias | Real host | Key | Identity |
| --- | --- | --- | --- |
| `github.com` (default) | github.com | `id_personal_m4` | personal (`daolondrizdaolondriz@gmail.com`) |
| `github-personal` | github.com | `id_personal_m4` | same personal key, explicit alias |
| `github.com-glasic` | github.com | `id_glasic` | Glasic Lab (`info@glasiclab.com`) |
| `github.com-squadeat` | github.com | `id_squadeat` | Squadeat (`admin@squadeat.com`) |
| `ubuntu` | 192.168.0.112 | `id_ubuntu` | Mac -> Ubuntu login |
| `glasic-ec2-paris` | 35.181.242.235 | `glasic-key-paris.pem` | Glasic AWS (Paris) |
| `glasic-ec2-tech` | 35.181.242.235 | `glasic-tech-v3-keys.pem` | Glasic AWS tech |
| `glasic-v2` | 15.188.222.229 | key under `Documents/work/glasic/...` | Glasic v2 |

Present on disk but **not** referenced in Mac `~/.ssh/config`: `id_nh` (comment `github-nh`, Nova Hiring). Confirm with the user before using it.

Examples:

```bash
# personal
git clone git@github.com:USER/REPO.git
git clone git@github-personal:USER/REPO.git

# Glasic
git clone git@github.com-glasic:ORG/REPO.git

# Squadeat
git clone git@github.com-squadeat:ORG/REPO.git
```

### Ubuntu (`/home/david/.ssh/`)

| Host alias | Real host | Key | Identity |
| --- | --- | --- | --- |
| `github.com` / `github-personal` | github.com | `~/.ssh/personal` | personal |
| `github-glovo` | github.com | `id_glovo` | Glovo (`david.amat@glovoapp.com`) |
| `github-glasiclab` | github.com | `id_glasiclab` | Glasic Lab |
| `github-redangreenai` | github.com | `redangreenai` | redangreenai |
| `bitbucket-revolut` | bitbucket.org | `id_revo` | Revolut / Bitbucket |
| `hf.co` | hf.co | `id_hf_ubuntu` | Hugging Face git |
| `hostinger` | 92.112.194.187 | `hostinger` | Hostinger (user `root`) |
| `fitfy` | 13.49.8.254 | pem on Desktop | Fitfy EC2 |
| `glasic-ec2` | 54.215.84.157 | pem in glasic-admin-app | Glasic AWS |
| `glasic-ec2-paris` | 35.181.242.235 | pem in glasic-admin-app | Glasic AWS Paris |

If the user says the current project is for company B, look up the matching `github.com-companyb` (or Ubuntu `github-companyb`) alias and its `IdentityFile` before `git clone` or `git push`.

---

## 11. How agents should work in this setup

1. Assume the session is on the **Mac** unless the prompt says otherwise. For AImpromptu, assume **Ubuntu** (section 12).
2. For GPU, large training, embeddings, Docker image builds, or multi-hour jobs: give Ubuntu commands (`ssh ubuntu '...'`) or run them only when already on that host.
3. Default `docker` on the Mac is the **Ubuntu** daemon. Images land in `/mnt/ssd2/docker`.
4. Use `docker --context colima` only when Mac files must be bind-mounted (Supabase-local, similar cases). Start Colima first if it is stopped.
5. Store bulky Mac files under a DevSSD-backed `~/Documents/` symlink (`dev`, `work`, `projects`, `repos`, `utils`, `storage`, `media`). Do not write large caches to the internal 228 Gi volume.
6. On Ubuntu, default code is under `/home/david/Documents/...`. Models, Docker, and datasets belong on `/mnt/ssd2`.
7. Select the SSH key / git host alias that matches the client. Do not push a client repo with the personal GitHub key.
8. Keep secrets on the machine that needs them. Do not copy `.env` files between Mac and Ubuntu unless asked.
9. Confirm `pwd` and which machine you are on before destructive or long commands.
10. Prefer a short smoke test. Leave long GPU runs for the user to monitor in an Ubuntu terminal.

---

## 12. AImpromptu: everything on Ubuntu, the browser on the Mac

Implementation 08 moved AImpromptu from the Mac to Ubuntu, because its transcription model (MuScriptor `large`, 1.4 billion parameters) needs the RTX 4090. The Mac stays the machine the user looks at the app from.

### 12.1 Who runs what

| What | Where |
| --- | --- |
| The repositories `aimpromptu` and `vexflow-v2` (side by side), and `muscriptor` | Ubuntu, `/home/david/Documents/projects/music/` |
| The IDE session (Cursor) and the AI agent | Ubuntu |
| The backend and the frontend | Ubuntu, in two Docker containers (`compose.yaml` at the repository root) |
| The piece data (`aitu-backend/data/`, gitignored) | Ubuntu. The Mac's copy, `/Volumes/DevSSD/Documents/projects/music/aimpromptu`, is the state of 2026-09-28 and is no longer updated |
| The browser | The Mac, through the tunnel |
| Headless screenshots and browser checks by the agent | Ubuntu (Playwright's Chromium in `~/.cache/ms-playwright`) |

### 12.2 Start the app (on Ubuntu)

```bash
cd ~/Documents/projects/music/aimpromptu
make up        # builds the images if needed, starts both containers, waits until they answer
make logs      # follow both
make down      # stop both
```

The backend container reserves the GPU and loads MuScriptor `large` at start (about 3.5 GB of GPU memory). `HF_TOKEN` (the Hugging Face token of the account that accepted the MuScriptor licence) is exported in `~/.zshrc`, and Compose reads it from the shell. Both containers publish their ports on `127.0.0.1` only: 5173 (the page) and 8765 (the backend, for `curl` on Ubuntu).

### 12.3 Open the app (on the Mac)

```bash
ssh -N -L 5173:localhost:5173 ubuntu
# or, from the Mac's copy of the repository:
scripts/tunnel-from-mac.sh
```

Then open `http://localhost:5173` in the browser of the Mac. One port is enough: the page's own server (Vite) passes `/api` to the backend, including the audio files and the progress stream. The tunnel stays open until Ctrl-C, and it closes when the Mac sleeps; run it again after.

When an agent gives the user a URL of the app, it gives this tunnel command with it.

### 12.4 Things to know

- **A lost GPU in the container.** After the host's service manager reloads (for example after a system update), a running container can lose its GPU: `GET /matrix/engine` says "No CUDA GPUs are available" and a transcription ends at once with no notes. `docker compose up -d --force-recreate backend` gives it back.
- **Ubuntu has no access to the Mac.** Remote Login is on for the Mac, but Ubuntu has no key or `Host mac` entry for it. Phase 0 of implementation 08 wrote the steps (`context/implementations/01-mvp/08-new-algorithm-notes-detection-muscriptor/08-implementation-phase-0.md`), and they are optional: nothing in the project needs files from the Mac now.
- **Disk.** The backend image is 10.4 GB (almost all of it PyTorch with its CUDA libraries) and the frontend image 1 GB; both live in Docker's data root on `/mnt/ssd2/docker`.
- **Commands and troubleshooting** for the containers are in `context/04-local-development.md`.
