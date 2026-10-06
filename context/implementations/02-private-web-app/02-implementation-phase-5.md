# 02: Phase 5 report: projects and the Personal Vault

Plan: [`02-plan.md`](02-plan.md) sections 8.3, 8.5, 10.1, 10.2 and 10.5, and section 20, Phase 5.
Checklist: [`02-checklist.md`](02-checklist.md). Branch `feat/phase-5`, made from `master` at
`c40b251` (Phase 4 merged). Done 2026-10-06 and 2026-10-07 on the Ubuntu machine.

# 1. Summary

| Story | Result |
|---|---|
| Before the phase | The user's change (`.database/` and the music library out of the repository) committed as theirs (`5e31b8c`); `07-database.md`, `paths-and-data.md`, the Phase 3 and 4 reports, the plan's Phase 3 line, the checklist, two READMEs and `.gitignore` made to agree with it (`76937fd`). The app restarted with `make up`: the backend now mounts `/mnt/ssd2/aimpromptu/.database` from `.env` |
| 5.1 The projects | `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}`, duplicate, export, import. The step of each project kept in `projects.step` and worked out again only after a part changed. The Projects page on the new list, **New project** as a menu (From source; From scratch and From other projects disabled; Import), the row menu (Open, Duplicate, Export, Rename, Notes Falling, Delete) |
| 5.2 From source | The drop zone takes an audio or a video file; the **Video** choice for every user. **Add audio**: several files end to end in one timeline, cuts across the join. The video as a step of the project (fit the piano, **Read notes** as one job), its files temporary. Q-8 measured |
| 5.3 Export and import | The `.aitu` zip and its round-trip test; a refused import leaves nothing behind |
| 5.4 Documentation | `flow-page.md` became `projects.md`; `pieces-and-revisions.md`, `endpoints.md`, `paths-and-data.md`, `07-database.md`, `08-security.md` and the pages of section 7 |

Checks at the end (section 7): backend 1,073 tests on the GPU, 1 failed (the known one); every
frontend check passes, the new `check:projects` too; `check:flow` with the live transcription;
`bench:sheet` and `time:flow` at the Phase 4 numbers.

# 2. Before the phase: `.database/` outside the repository

The working tree held the user's own change: `AITU_DATABASE_DIR` in `.env` instead of the
`.database` link, the `Makefile` reading it from `.env`, and the music library moved to
`data/music-library` next to the repository. It was committed as the user's change, without the
untracked editor files (`.cursorignore`, `.cursorindexingignore`, `.vscode/`), which are local
settings and stay untracked.

The pages kept their history: the Phase 3 and 4 reports say what was built then (the link) and add
what changed after Phase 4, instead of being rewritten. The backup named in the Phase 3 report was
at the root of the repository and is gone; `make db-backup` now writes into `/mnt/ssd2/aimpromptu/`.

The running backend still mounted the old link path (Docker had resolved it when the container
started). `make up` recreated it with the mount from `.env`, and `make db-check` on the host (which
now reads `AITU_DATABASE_DIR` through the `Makefile`) found 39 projects and no problem.

**One leftover, not changed:** `tests/conftest.py` defaults `AITU_REAL_DATABASE_DIR` to
`<repository>/.database`. Inside the container it is `/database`, so the two tests that read the
real library still run; a native `pytest` without the variable would skip them.

# 3. Story 5.1: the projects

## 3.1 The routes (`api/projects.py`)

`GET /projects?layer=…` (default `vault`), `POST /projects` (an empty project), `POST
/projects/import`, `GET /projects/{id}`, `PATCH /projects/{id}` (rename), `DELETE
/projects/{id}` (`204`), `POST /projects/{id}/duplicate` (since Phase 3), `GET
/projects/{id}/export`. The rights check of Phase 4 covers them through `project_id`; create and
import name no project and need only a session; the list is scoped by owner. The row: id, title,
kind, layer, step, running, parts, source, `hasVideo`, `hasNotes`, basedOn, createdAt, updatedAt.

`bundle.new_bundle_from` makes the rows and the empty folders of a project shaped like another,
with new ids; duplicate and import both use it. `bundle.last_change` is the old `_updated_at` of
`api/audio.py`, per project.

## 3.2 The step of a project (Task 5.1.1)

`piece_status` reads the notes and the sheet of a part: measured on the 39 real projects, 0.9 s for
all of them, 25 to 59 ms each. A list that waits a second is too slow, so the step is stored:

- `bundle.step_changed(part)` sets `projects.step` to `NULL`. It is called by every writer of the
  files that decide the step: `pipeline.save_note_events`, `save_rhythm`, `clear_rhythm`, and
  `bundle.write_timeline`. (No restore writes into a part: the history only snapshots.)
- `GET /projects` works out the step again (`tools.refresh_step`) only for the rows it finds
  `NULL`, and stores it. After a restart nothing is lost: the column is in the database.
- A running job is read from the job queue at each list (`transcribe:<part>`,
  `video-read:<part>`), so the row says "Transcribing" or "Reading" at once; the page asks again
  every 5 s while a row is running.

The step values on the page: `source` reads "New", `audio` of a video project reads "Video".

## 3.3 A project with no audio

`POST /projects` makes a project with no audio and no notes (for From scratch, Phase 8). Its status
was "Source ready, Audio ready", which is false, so `piece_status` now answers Source `missing` and
every later step closed ("Add an audio first") **when a part has neither audio nor notes**. A part
with notes and no audio (the old Compose, `POST /audio/compose`) reads as before; the first version
of the rule applied to every part without audio and broke 18 tests of `test_pieces.py`, whose
fixtures are such parts. One test (`a piece with no notes opens on the audio tab`) described the old
meaning of a part with no audio; it now gives its piece an audio file.

## 3.4 The Projects page (Task 5.1.2)

One request for the list, with the step in it (the old page made one status request per row). The
vault first; then, until Phase 6 gives the Private Library its pages, the 30 songs of the library in
a group **In my library**, so they stay one click away. **New project** opens a menu: **From
source**, **From scratch** and **From other projects** (disabled, "Not available yet": the plan asks
for the three choices, and Phases 8 and 10 build the last two), and **Import** (a `.aitu` file; the
new project opens). The row menu: Open, Duplicate (adds "<title> (copy)" at the top with a short
confirmation), Export (the browser saves the file), Rename, Notes Falling, Delete. The project page's
`⋯` menu gains Export.

# 4. Story 5.2: from source

## 4.1 The Source step (Task 5.2.1)

The drop zone takes an audio or a video file (`.mp4 .mov .m4v .mkv`; `.webm` stays audio). A video
file goes to the new `POST /video/upload` (`video/download.ingest_file`): the audio is extracted
with ffmpeg and ingested like an upload, and the video becomes `tmp/<userId>/<partId>/video/
source.mp4`. The **Video** choice of a YouTube link is shown to every user, and a video, uploaded or
downloaded, opens the project's Video step instead of Lab. On an existing project the step lists the
added files under the first.

## 4.2 Add audio (Task 5.2.2)

The plan's timeline is a list of segments. The whole Audio step (the cuts of implementation 08, the
frame table, `normalized.wav`, the peaks, the transcription) works on **one axis**: the original file,
with cuts as ranges of it. Rewriting all of it for a general list of segments was not needed for
**add audio**, which only appends. So the axis became **the files laid end to end**:

- `timeline.json` gains `sources` (the files of the axis in order; the same file may come twice)
  and each segment `source` (the place of its file in that list). A cut is a range of the axis, as
  before; `bundle.segments_for_axis` splits the kept ranges at each join; `bundle.cuts_of` reads
  them back. Both fields are left out for a part of one file, so every older timeline reads and
  writes unchanged.
- **Why `source` on a segment.** The first version placed a segment on the axis by walking the
  files in order. With the same file twice, `[a 0–50 ms, a 950–1000 ms]` over `a, b, a` reads both
  as cuts inside the first `a` or as one cut across `b`: the test with a repeated file found it.
- A part of several files has no single original, so two derived files stand in for it
  (`audio/sources.py`): `normalized.wav` is each file's 16 kHz copy (`src-<hash>.wav`) padded to
  whole 10 ms frames and joined (so file `i` starts exactly at its frame), and `sources-<key>.flac`
  is the files decoded at 44.1 kHz (48 kHz when one is above it), padded or trimmed to their frames,
  joined. `StoredAudio.original_path` points at the FLAC and `store.original_file()` writes it when
  missing; the piece audio of the cuts and `GET /audio/{id}/file?original=true` use it. Each join
  gets the 5 ms fade of a cut, so it does not click or read as a note.
- `POST /audio/{id}/add` (`ingest.append_file`, `store.append`): stores the file, measures it from its
  16 kHz copy, appends it, raises `audioRevision` (the notes become stale), and records the file in
  `project.json` (`parts[].source.added`, left out when empty). A file ffmpeg cannot read is refused
  and its bytes are deleted again. `replace_original` (a splice) makes the part one file again.
- `GET /audio/{id}/cuts` answers `files` (name, first frame, length); the waveform draws a dashed
  grey line at each join and each file's name, and the overview the lines.

**For Phases 8 and 9.** A pasted passage in the middle of a part is not "files end to end". Those
phases extend `sources` to ranges of files (an entry `{audio, fromMs, toMs}`), which keeps this
axis model; the plan says so in section 8.5.

**A defect found by the screenshots:** after **Add audio** the waveform stayed zoomed on the first
file. The editor was keyed by a counter, so it started again on the old waveform for a moment and
kept that view. It is now keyed by the length of the audio too.

## 4.3 The video as a step (Task 5.2.3)

A project with a video (`hasVideo` on the audio entry and the row) has a **Video** step in place of
Audio (`pages/piece/VideoStep.tsx`), in three moments:

1. **Preparing the video**: the frames are sampled (100 ms) as the step opens, with a thin bar.
2. **Fit the piano**: the calibration editor of Lab on the middle frame, in a new `compact` form (no
   help paragraph, one line "Drag the rectangle onto the piano keys", **Save the piano**, Cancel).
3. **The video with the piano on it** (`FramePlayer` with `PianoOverlay` and the upper line, its
   audio playing), **Fit the piano again**, and **Read notes**.

**Read notes** is one job, `POST /video/{id}/read` (`video/piece.read_and_write`, key
`video-read:<id>`): sample when there are no frames, measure the roll when it was never measured
for this overlay, stitch, read, write the notes (`piece.write`, so the music version moves and the
sheet is cleared, as before). The calibration file records `measuredFor` (the overlay the
measurement was made with, without the roll top and guard band that the measurement itself
writes), so a second **Read notes** without a new fitting does not measure again: in the browser,
66 s the first time and 25.5 s the second on Superestrella's 3:09 video. The progress shows the
stage in words ("Measuring the roll", "Reading the notes", "Writing the notes"); when it ends the
page opens the Notes step. The Notes step of a video project says "Read the notes of the video"
instead of "Transcribe", and is `running` during the job. Errors (no piano fitted: `409`; a speed
that is not stable: the reason, V-06) show on the step.

**The temporary files.** The video stays under `tmp/<userId>/<partId>/video/`, deleted with the
project (tested). Phase 6 deletes it when the project is saved to the Private Library.

What stays in Lab: the detection, the measurements, the score board, and correcting single notes on
the video (the corrections are still applied by **Read notes**). `ROUTES.labVideoOf` is removed.

**The frame player's help line** ("click the picture, then spacebar plays…") was a paragraph under
the video on a project page; the player gained `quiet`, used by the Video step. Lab keeps it.

## 4.4 Q-8, measured

`aitu-backend/scripts/bench_video_read.py` runs **Read notes** on a temporary copy of a video
project (duplicate, copy the video folder, read, delete) and prints each stage. On Superestrella's
tutorial video (3:09, 1,892 frames):

| Stage | From | To | What it reads |
|---|---|---|---|
| sample | 0.1 s | 1.8 s | the frames (when there are none) |
| plate | 1.9 s | 6.0 s | the background, from frames across the whole video |
| follow, measure | 6.0 s | 39.1 s | the speed of the roll: every frame |
| stitch | 39.1 s | 59.8 s | the roll, strip by strip, in time order |
| notes, shapes, write | 59.8 s | 61.0 s | the notes of the roll, written: 1,495 notes |

The stitched roll is built in time order, so notes could be sent while it grows (a note is complete
once its top is below the newest strip). But that is the last 22 s; the first 39 s read the whole
video (the background and the speed), and the speed must be measured on the whole video before any
row becomes a time (V-06). Options and recommendation are in the walkthrough and in section 9.

# 5. Story 5.3: the `.aitu` file

`storage/exchange.py`. The export: `export.json` (format `aimpromptu-project`, version 1, when,
from which project), `project.json`, `parts/<id>/notes.pmn|sheet.json|timeline.json` byte for byte,
`audio/<sha256>.<ext>` stored without compression. Nothing derived, temporary or historical. The
file is written to a temporary file and deleted after the answer.

The import makes a new project in the importer's Personal Vault with new ids, the same title and
`origin: {"importedFrom": id}`. It refuses with `422` and leaves nothing (no project row, no folder,
no audio file no project uses): not a zip; no `export.json` of this format; a newer version; more
than 10,000 members or 2 GB; `notes.pmn` not a `.pmn` file; `sheet.json` not a saved reading;
`timeline.json` whose cuts do not read back; an audio file missing or whose SHA-256 is not its name.
Members are read only by the names it expects, so no name in the zip becomes a path.

`test_projects.py` checks export, import and export again give the same part files and the same
audio, on a project with two files, a cut and a saved sheet, and that the imported project has the
same status as the original; five damaged files are each refused and leave nothing.

# 6. Tests

| File | Tests | What |
|---|---|---|
| `test_projects.py` (new) | 22 | the list and its layers; an empty project opens on Source; the step stored and cleared; rename, delete (its audio deleted); duplicate; the axis and its cuts both ways with a repeated file; a cut across a join; add audio (frames, revision, stale notes, the joined `normalized.wav` on whole frames, the FLAC original); an unreadable file refused and not kept; a splice makes one file again; the round trip; five refused imports; the export name; another user's project; a video file uploaded (ffmpeg makes one), its Notes step, `409` before fitting, its video deleted with the project; add audio needs a first file; the source lists the added file |
| `test_video_step.py` (new) | 5 | **Read notes** measures once per overlay and again after a new fitting; samples first when there are no frames; needs the piano fitted; stops on an unstable speed; the Notes step of a video part |
| `test_pieces.py` | changed | the piece with no notes gets an audio file (section 3.3) |

# 7. The checks

| Check | Result |
|---|---|
| Backend, full run on the GPU | 1,073 tests: 1,072 passed, 1 failed, the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas` |
| `black`, `flake8`, `mypy` on the changed modules | clean |
| `tsc -b`, `npm run lint`, `npm run build` | clean; the build has the chunk-size warning of Phase 0 |
| `check:render`, `check:history`, `check:note-names`, `check:geometry`, `check:cuts`, `check:notes` | 60, all, 15, all, all, all passed |
| `check:projects` (new), signed in | every check passed (20), no console error; nothing it made is left |
| `check:flow`, signed in, with the live transcription | every check passed, no console error (again after the last change, without the transcription) |
| `bench:sheet`, median of a hand move | Elefants 212 ms, Superestrella tutorial 270 ms, The Other Side 516 ms (Phase 3: 215, 268, 492) |
| `time:flow`, the first piano sheet | 0.6 s, 0.9 s, 0.5 s (Phase 4: 0.6, 0.9, 0.5); notes saved 26.9 s, 51.0 s, 20.9 s |
| `make db-check` on the real `.database/` | 39 projects, no problem, after every script |
| `scripts/docs/check-links.py` | passes |

The YouTube piece of `time:flow` first timed out after 300 s: its download job started and never
made a project, with no error in the log. The same download through the API right after took a few
seconds, and `time:flow --only youtube` then passed (3.4 s in). It was YouTube or yt-dlp on that
attempt, not the app; the project the API call made was deleted.

The browser scripts signed in with the master user's password, which the user put in `.env`.

# 8. The 13 checks of the 09 guidelines

Run on the pages this phase made or touched, with the screenshots of
[`screenshots/phase-5/`](screenshots/phase-5/). The video screens were taken on a temporary copy of
Superestrella's tutorial project with its video (deleted after); 01 to 07 are `check:projects`' own
projects.

| # | Check | Result |
|---|---|---|
| 1 | One sentence | Projects: open or start my work. Video step: fit the piano and read the notes of the video |
| 2 | Every sentence a label, control or fact | Fixed: the frame player's help paragraph under the video (now off on the Video step). "Not available yet" on two menu items is a fact |
| 3 | Words above the first content | Projects: "Projects", "New project"; Video: none but the button |
| 4 | Very wide | Rows keep their columns; the primary button stays beside the title |
| 5 | Narrow (390 px, shots 14, 15) | 0 px of overflow. Fixed: the title read "Proj…", because an empty spacer took half of the room beside it (`PageHeader`, every page) |
| 6 | Longest, shortest, none | Long titles truncate with the full title on hover; an untitled project reads "Untitled project"; a file name on the waveform is cut with "…" to its part |
| 7 | Buttons say what happens | "New project", "From source", "Import", "Duplicate", "Export", "Delete project", "Add audio at the end", "Save the piano", "Fit the piano again", "Read notes" |
| 8 | Helper lines | The menu's secondary lines say what each choice takes ("An audio, a video or a YouTube link", "A .aitu file") |
| 9 | Loading, empty, partial, error | Projects: skeleton rows, "No projects yet" with **New project**, an error with **Try again**; Video: "Loading the video…", "Preparing the video" with a bar, the stage while reading, a failed read as an error line |
| 10 | Tab through it | The New project menu and the row menus are menus; the hidden file inputs have labels |
| 11 | Internal names | None on screen: no "sha", "bundle", "timeline", "job" |
| 12 | First-time user | "Add audio at the end", "Fit the piano again" are the user's words |
| 13 | Anti-patterns | No lecture left on the Video step; no dead menu item without a reason |

| Shot | Page |
|---|---|
| 01 | The New project menu |
| 02, 03 | **Add audio**: two files end to end with their names; the Source step listing the added file |
| 04 to 06 | The row menu; a duplicate added; the delete confirmation |
| 07 | A video file just uploaded: fit the piano |
| 08, 09 | Projects with **In my library** |
| 10 to 13 | The Video step of a real video; fitting again; reading (the stage); the Notes step with 1,495 notes |
| 14, 15 | 390 px: Projects, the New project menu |
| 16 to 18 | Dark: Projects, the Video step, the Source step |

# 9. Open points

- **Q-8, for the user** (walkthrough): keep the reading as one job with its stages (recommended), or
  stream the notes during the stitch (first notes after about 40 s on a 3-minute video), or measure
  the speed on the first seconds only (first notes after a few seconds, against V-06).
- **The music library group on the Projects page** goes when Phase 6 builds My library.
- **The video's temporary files** are deleted on save to the library: Phase 6.
- **`sources` as ranges of files** for paste and Recording in Sheet: Phases 8 and 9 (section 4.2).
- **Q-7 and the rest of Phase 6** are unchanged.

# 10. Learnings for later phases

- **A list that computes a state per row needs it stored.** Keep a copy in the table, cleared by the
  writers and worked out again lazily, rather than computing it on every list.
- **A key that names a file is not an identity when the file can come twice**: keep the position.
- **Key an editor by the data it starts from**, not by a counter of reloads: it remounts before the
  new data arrives.
- **Look at narrow screenshots**: a spacer that splits the free room with a growing title hides
  half of the title.
- **A Lab component on a user page brings Lab's help text**: give it a quiet form.
- **`docker compose exec` runs in another process**: the job queue of the app is not visible from
  it; follow a job through the API.
- **The browser scripts sign in from `.env`** while `AITU_MASTER_PASSWORD` there is the current
  password; otherwise set `AITU_CHECK_PASSWORD`.
