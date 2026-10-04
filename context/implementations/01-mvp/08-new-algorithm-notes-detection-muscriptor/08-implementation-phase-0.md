# 08 Phase 0: commit and push from the Mac, and the move to Ubuntu

The plan is [`08-plan.md`](08-plan.md) section 12, Phase 0, and section 10.1. The status lookup is
[`08-checklist.md`](08-checklist.md). This report is for the agents of later phases.

# 1. What was done

| Task | Result |
|---|---|
| 0.1.1 ignore rules | Done before the phase, while the plan was written. Checked again: nothing under `pocs/` that is a video, audio, weight or `__pycache__` file is added |
| 0.1.2 broken paths | Fixed. Six code paths and every document link (section 2) |
| 0.1.3 size check | 211 files added, 14.4 MB in all, largest file 0.77 MB (`pocs/poc-piano-overlay/out/blackkeys1.png`). Nothing over 5 MB. The five committed `__pycache__/*.pyc` files of `poc-piano-overlay` are removed, not moved |
| 0.1.4 commit and push | `master` pushed to `git@github.com:DavidAmat/aimpromptu.git`. `vexflow-v2` is clean on `plan-resume` at `f4d2a6f`, the same commit as `origin/plan-resume` |
| 0.2.1 manifest | Section 3 |
| 0.2.2 copy script | `scripts/migrate/push-data-to-ubuntu.sh`, with `manifest.sh` and `data-paths.txt` (section 4) |
| 0.3.1, 0.3.2 handover | In the walkthrough message to the user. The commands are repeated in section 5 |

# 2. The broken paths

The POC folders moved from the root into `pocs/` before this phase. Three kinds of reference broke.

**Code that reads files** (fixed, and checked by resolving each path):

- `aitu-backend/tests/test_matrix_peaks.py:266` and `aitu-backend/tests/test_time_score_payload.py:247`
  read `poc-onset-duration-distribution/data`. Both tests are guarded by `skipif(not POC_DATA.exists())`,
  so after the move they **skipped silently** instead of failing. They now read `pocs/...`.
- `aitu-backend/scripts/seed_frame_examples.py:34` (`SPIKE`).
- `pocs/poc-synthesia-frames/scripts/common.py` and `thumbs.py`: `ROOT = parents[2]` became
  `parents[3]`, and `OUT`/`DATA` now start with `pocs/`.
- `pocs/poc-piano-overlay/scripts/common.py`: `EXAMPLES` used `ROOT.parent`, now `ROOT.parents[1]`.
- `pocs/poc-onset-duration-distribution/scripts/common.py` uses paths relative to itself and needed
  no change.

**Commands in README files**: `cd aitu-backend && uv run python ../poc-.../scripts/...` became
`../pocs/poc-...`, and the Markdown links from `pocs/*/README.md` and `RESULTS.md` to `../context/`
became `../../context/`. A link check over every Markdown file under `pocs/` and `context/` finds no
broken link that contains `poc`.

**Mentions in docstrings and documents** (34 files, a mechanical replacement of `poc-X` by
`pocs/poc-X` where it was not already under `pocs/`). The 08 folder was left out, because its plan and
checklist name the old path on purpose. Historical sentences such as "at the repository root" in the
04 and 05 plans were left as written; only the index line in `context/00-index.md` was reworded.

## 2.1 A failing test that the skip had hidden

With the path fixed, `tests/test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas`
runs again and **fails**: the E5 at 00:46 is printed as a negra instead of a corchea. It fails in
the same way on commit `8122cea` (checked in a temporary worktree where the data is still at the
root), so the move did not cause it. The last commits that touched the payload code
(`937f480` "The left hand is printed in corcheas", and `8122cea`) are the likely origin. It is out of
the scope of 08 and was not changed.

The backend baseline on the Mac after this phase: **906 passed, 1 failed** (that test),
`pytest` in 17 s. Phase 1 should expect the same result on Ubuntu, and must not count that test as a
problem of the move. Black and flake8 pass on the changed backend files.

# 3. The data manifest

These are the gitignored folders a new clone needs. The list is `scripts/migrate/data-paths.txt`.
Numbers are from `scripts/migrate/manifest.sh --summary` on the Mac on 2026-09-28.

| Folder | Files | MB |
|---|---:|---:|
| `aitu-backend/data/audio` (37 pieces) | 7,407 | 1,139.9 |
| `aitu-backend/data/frame-examples/cache` | 24 | 2.2 |
| `context/implementations/04-synthesia-to-notes/examples` | 24 | 77.8 |
| `pocs/poc-synthesia-frames/data/video` | 3,052 | 276.7 |
| `pocs/poc-synthesia-frames/out/calibration` | 21 | 1.8 |
| `pocs/poc-synthesia-frames/out/detectors` | 20 | 5.6 |
| `pocs/poc-synthesia-frames/out/labels` | 36 | 4.8 |
| `pocs/poc-synthesia-frames/out/thumbs` | 21 | 1.1 |
| `pocs/poc-synthesia-frames/out/ui` | 6 | 0.5 |
| `pocs/poc-synthesia-frames/out/zoom` | 15 | 1.4 |
| **Total** | **10,626** | **1,511.7** |

`aitu-backend/data/frame-examples/cache` was not in the plan's table (section 10.1). It is small and
the frame examples page reads it, so it is copied.

Not copied: `_to_delete/` (384 MB, only if the user asks), the ByteDance checkpoint (downloads itself),
`.claude/` and `.run/` (Mac editor settings), and every `node_modules/`, `.venv/` and `dist/`. There is
no `.env` file in the repository, so none is copied (rule 8 of `02b-local-setup.md`).

A per-file manifest (10,626 lines) is not committed. The copy script builds it on both machines and
compares them instead, which is a stronger check than a list written once on the Mac.

# 4. The scripts

`scripts/migrate/` holds three files:

- `data-paths.txt`: the folders of section 3, with comments on what is left out.
- `manifest.sh [--summary] [repo-root]`: one line per file (`bytes TAB path`), or one line per folder
  with the count and the bytes. It uses `find -print0 | sort -z | perl -s`, so it gives the same
  output on macOS and Linux. It can run on the other machine without a copy:
  `ssh ubuntu 'bash -s -- --summary <path>' < scripts/migrate/manifest.sh`.
- `push-data-to-ubuntu.sh <ubuntu-repo-path> [ssh-host]`: checks that the path is a clone (it looks for
  `scripts/migrate/data-paths.txt`, so the clone must include this commit), copies with
  `rsync -a -R --partial --stats`, excluding `.DS_Store` and `__pycache__`, never deletes on Ubuntu,
  then compares the file lists of both sides and prints the count and size per folder. Exit code 2
  means some files are missing or differ, and a second run copies only those.

The Mac's `rsync` is `openrsync` (protocol 29), and Ubuntu has rsync 3.2.7. Only options that both
support are used.

**Tested** on a fake clone in the scratch folder with one real data folder (24 files, 2.2 MB) pushed to
`ubuntu:/tmp/aitu-migrate-test`: the first run copied the 24 files and reported "OK"; the second run
transferred 0 files and reported "OK"; a path without a clone stopped with exit code 1 and a message.
The test folder on Ubuntu was deleted after the test.

# 5. The handover (what the user runs)

The repositories go to `/home/david/Documents/projects/music/` on Ubuntu, which does not exist yet.
Ubuntu's `github.com` SSH alias authenticates as `DavidAmat` and can read both repositories (checked
with `git ls-remote`).

```bash
# On Ubuntu
mkdir -p ~/Documents/projects/music && cd ~/Documents/projects/music
git clone git@github.com:DavidAmat/aimpromptu.git
git clone -b plan-resume git@github.com:DavidAmat/vexflow-v2.git

# On the Mac, from the repository root
scripts/migrate/push-data-to-ubuntu.sh /home/david/Documents/projects/music/aimpromptu
```

Ubuntu to Mac access (optional). Remote Login is already on for the Mac (port 22 answers). The Mac has
no `~/.ssh/authorized_keys` yet, and Ubuntu has no key or `Host` entry for the Mac. The Mac's Wi-Fi
address is `192.168.0.220` (interface `en1`, from DHCP, so it can change; a reservation in the router,
like the one Ubuntu has, would fix it). From the Mac:

```bash
ssh ubuntu 'ssh-keygen -t ed25519 -N "" -C ubuntu-to-mac -f ~/.ssh/id_mac'
ssh ubuntu 'cat ~/.ssh/id_mac.pub' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
ssh ubuntu 'printf "\nHost mac\n  HostName 192.168.0.220\n  User david\n  IdentityFile ~/.ssh/id_mac\n" >> ~/.ssh/config'
ssh ubuntu 'ssh -o StrictHostKeyChecking=accept-new mac hostname'   # prints Davids-Mac-mini
```

The Mac's copy of the repository is at `/Volumes/DevSSD/Documents/projects/music/aimpromptu`.

# 6. Notes for Phase 1

- **The shell on Ubuntu.** `uv` (`~/.local/bin`, version 0.11.3) and Node (`nvm`, v22.19.0) are only on
  the `PATH` of an interactive `zsh`. A plain `ssh ubuntu '<command>'` does not find them. In a Cursor
  terminal on Ubuntu this does not matter; over SSH, use `zsh -ic '<command>'` or the full path.
- **Already present on Ubuntu**, seen from the Mac: `git`, `ffmpeg` (`/usr/bin`), Docker with the
  `nvidia` runtime registered and its root on `/mnt/ssd2/docker`, and the RTX 4090 with driver
  595.58.03 and 24,564 MiB. Task 1.1.1 still checks them from inside a container.
- **The data check** (task 1.1.2) is done by the copy script. To repeat it on Ubuntu alone, run
  `scripts/migrate/manifest.sh --summary` and compare with the table in section 3.
- **The known failing test** of section 2.1 is expected in `make test`.
- **Disk**: `/` has 601 GB free, `/mnt/ssd2` has 1.3 TB free.
