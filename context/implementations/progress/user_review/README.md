# User review guides

One file per epic. Each is a **click-by-click script**: what to open, what to press, what happens
behind the scenes, and what you should see if it worked.

You do not need to read any code to follow these. Where something is worth understanding, there is
a short *"what happens when you click"* box explaining the backend in plain terms.

## Order

Do them in this order — each builds on the last.

| # | Guide | Time | Needs |
|---|-------|------|-------|
| 0 | [00-setup.md](00-setup.md) | 15 min | ffmpeg, uv, node |
| 1 | [epic-01-skeleton.md](epic-01-skeleton.md) | 5 min | — |
| 2 | [epic-03-audio-io.md](epic-03-audio-io.md) | 20 min | a microphone, an mp3 |
| 3 | [epic-04-transcription.md](epic-04-transcription.md) | 20 min | the transcription extra |
| 4 | [epic-06-playground-input.md](epic-06-playground-input.md) | 15 min | everything above |
| 5 | [epic-07-matrix-tab.md](epic-07-matrix-tab.md) | 20 min | a transcribed piece |
| 6 | [epic-02-matrix-core.md](epic-02-matrix-core.md) | 10 min | — (no UI; terminal only) |
| 7 | [epic-05-artifacts.md](epic-05-artifacts.md) | 10 min | — (no UI; terminal only) |

**Guide 5 is the satisfying one** — it is where a transcription finally becomes something you can
look at.

Epics 2 and 5 are backend-only, so their guides are terminal sessions rather than clicks. They are
last because nothing breaks if you skip them — their tests already cover the logic.

## The reference recording

Guide 2 asks you to record **Do Re Mi Fa Sol as slow negras at 60 BPM** — one note per second, no
pedal, letting each note ring its full second. Several later guides reuse that take, because it is
the simplest thing that can be obviously right or obviously wrong. Keep it.

## If something fails

Every guide has a **"If it goes wrong"** section listing the likely causes in order. If none of
them fit, the detailed engineering reports are one folder up in `epic-NN/task-N.M.K-progress.md`.
