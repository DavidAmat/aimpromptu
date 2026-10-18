# AImpromptu (aitu)

**A web app to catalogue songs and make their piano versions.** Bring in a recording (upload it,
record it in the browser, or download it from YouTube) and the app transcribes it with MuScriptor on
the GPU while you watch the notes appear, lets you correct the notes and the hands on a piano roll,
and writes the piano sheet, which you edit, print and play from. A finished piano sheet becomes a
version of a song in **My library**, and can be published to the **Public Library** that every user
shares, after the master user reviews the request. The product, in the user's words:
[context/app/01-app-context.md](context/app/01-app-context.md).

It runs on one machine and is opened from the devices of one home network: no hosted deploy
([context/05-deployment.md](context/05-deployment.md)). Every page asks to sign in. The master user
is made on the first start and makes the other users in **Admin → Users**; each user sees only
their own projects and library, unless an owner shares it. The users, the session, the rights table
and what this setup does not protect are in [context/08-security.md](context/08-security.md).
Everything the app stores is in one folder, `.database/`: a SQLite database, the projects and the
audio files. `make db-backup` copies it while the app runs ([context/07-database.md](context/07-database.md)).

## What makes it different

A note's **position** and a note's **name** are two separate numbers.

Position is measured wall-clock time: a frame is a fixed slice of real time, 40 ms by default. The
rhythmic figure is a name taken from the playing itself: the gaps between notes pile up around a few
lengths, the highest pile is a negra, and every other note takes its name from it. You change that
name in one action, and renaming a note moves nothing.

There is no BPM anywhere in the product.

Why: [context/backend/time-model.md](context/backend/time-model.md).

## Who it's for

- **Musicians** who want a readable page out of their own playing, a library of their piano
  versions, and a clean page to play from.
- **Developers** extending the transcription pipeline, the wall-clock matrix, the music library or
  the notation renderer.

## Services

| Service | Folder | Role |
|---|---|---|
| Backend | `aitu-backend/` | Run MuScriptor on the GPU, store the recorded notes, derive the piano sheet, keep the music library |
| Frontend | `aitu-frontend/` | Every screen, and every pixel of the sheet |
| Renderer | `../vexflow-v2` | `@aimpromptu/grid-notation`, installed from disk |

**Monorepo.** One git repository at the workspace root; `aitu-backend/` and `aitu-frontend/` are
service folders, not separate repos. The renderer is a **sibling checkout** on purpose: it knows
nothing about this app's API. On the Ubuntu machine each service runs in its own development
container (`compose.yaml`), with the repository mounted so edits reload.

## Run it

On the Ubuntu machine, from the repository root:

```bash
make up            # build if needed, start both containers, wait for both
```

Then open `http://ubuntu:5173` from any device at home and sign in as `master` with
`AITU_MASTER_PASSWORD` of `.env`. Every other command (logs, tests, the tunnel, the run without
containers, backup and restore, the checks, troubleshooting) is in one place:
[context/04-local-development.md](context/04-local-development.md).

## Documentation

| Start here | Purpose |
|---|---|
| [context/00-project-complete-overview.md](context/00-project-complete-overview.md) | One-shot orientation — paste this alone to get the whole project |
| [context/00-index.md](context/00-index.md) | Full map of all docs |
| [context/backend/time-model.md](context/backend/time-model.md) | The wall-clock model everything follows from |
| [documentation/README.md](documentation/README.md) | Code-level detail tree |

Subrepo entry points: [aitu-backend/README.md](aitu-backend/README.md) ·
[aitu-frontend/README.md](aitu-frontend/README.md)
