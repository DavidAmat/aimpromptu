# 02: Phase 6 report: the Private Library

Plan: [`02-plan.md`](02-plan.md) sections 8.5, 9.3, 10.2, 10.6, 15.1 and 15.2, and section 20, Phase
6. Checklist: [`02-checklist.md`](02-checklist.md). Branch `feat/phase-6`, made from `master` at
`561da32` (Phase 5 merged at the start of this session; the first pushes of `master` failed with a
GitHub server error, and a later one went through). Done 2026-10-07 on the Ubuntu machine. The
overview of the library is new: [`../../music-library/private-library.md`](../../music-library/private-library.md).

# 1. Summary

| Story | Result |
|---|---|
| 6.1 Saving | **Save to library** on a project whose Sheet step is ready: Artist, Song, Version name. The project moves from the vault to the library with the same ids; each audio file it uses only in part is written again with only the kept ranges (FLAC), the cuts disappear and nothing heard or read moves; the old file is deleted once no project uses it; the video, the edit sessions and the history of the parts are deleted |
| 6.2 The pages | My library: **Songs** (table, filter), **one song** with its versions (Open, Edit, Duplicate, Export, Rename, History, Delete), **Artists** (table, filter), **one artist** with its names (Add a name, Make default, Rename, Remove, Merge into another artist). A version opens **read only** on the project page, with **Edit**. Edit makes a copy in Projects that says **Editing**; its Save to library **replaces the version** (the earlier state kept in a history that can be restored) or saves a **new version**; Discard changes deletes the copy |
| 6.3 Documentation | `context/music-library/` started (`README.md`, `private-library.md`); `projects.md`, `pages.md`, `endpoints.md`, `paths-and-data.md`, `07-database.md`, `08-security.md`, `api.md`, `components.md`, the indexes, the plan's "as built" notes |

Checks at the end (section 6): backend 1,091 tests on the GPU, 1 failed (the known one); every
frontend check passes, the new `check:library` too, on a copy of Elefants.

# 2. Story 6.1: saving

## 2.1 The flow (`library/flow.py`, `POST /projects/{id}/library`)

1. **Checks.** The project is in the asker's vault; every part's Sheet step is `ready`; no
   transcription or video reading is running on a part. Otherwise `409` with the reason in words.
   The song is resolved first (an existing one by id; or the owner's song with that title and that
   artist; or none yet), and the version name is checked unique in the song (ignoring case), so a
   refusal changes nothing.
2. **The audio** (`audio/compact.py`, below) is written for every part, before anything moves.
3. **The move.** `users/<id>/vault/<projectId>/` is renamed to `users/<id>/library/<projectId>/`,
   `projects.layer` becomes `private`, and the cache of `storage/locate.py` forgets the project.
4. **Apply** the new audio to each part, delete the temporary files (`tmp/<userId>/<partId>/`,
   `staging/`, `history/<projectId>/parts/`), sync `audio_refs`, delete the replaced files.
5. **The rows**: the song (made with its artist when new; a new artist name makes a new artist)
   and a `private_versions` row.

**Why the part history goes on save.** Its timelines name the original audio, and `audio_refs`
counts the files a history names, so keeping it would keep every original and Q-3 would save no
disk. The app context calls the vault "work in progress": once saved, its intermediate states are
not kept. The history of the *library* project (each Replace) is kept.

## 2.2 The audio written again (Q-3, `audio/compact.py`)

The notes are in the time of the joined audio (the kept ranges end to end). So the new file must
be exactly those ranges end to end, and nothing else moves:

- **The new file** is the old one decoded at its own rate and channels, the kept frames joined with
  the 5 ms fade of a cut at each join, FLAC: what `piece-r<N>.flac` has always been
  (`piece_audio.write_joined`, the old private `_write_listen` made public).
- **Its 16 kHz copy** is the old 16 kHz copy with the same frames joined (`join_kept`), put in the
  cache as `normalized.wav` (one file) or `src-<hash>.wav` (several), so the engine's audio is the
  one the notes were made from, to the sample.
- **Its length** in frames is the number of kept frames, written into the timeline as it is (not
  measured again), so a later file of the part starts exactly where it did on the joined axis.
- **`audioRevision` does not change.** The audio of the piece did not change, so the notes, the
  hands and the sheet stay current. The cuts read back as none.
- **File by file.** A part of several files keeps its files, their order and their names
  (`parts[].source.files` takes the new hashes); a file used whole is not touched; a file cut away
  completely leaves the list.
- `prepare` writes the new files and changes nothing in the part; a failure (ffmpeg) deletes what it
  wrote and leaves the project as it was. `apply` then points the part at them.

Measured on real data by `check:library`: a copy of Elefants with two cuts had 23,335 kept frames
(233 s) before and 23,335 frames after, its notes' onsets equal one by one, and the project it was
copied from kept its file and its cuts (its file is still used, so it was not deleted).

## 2.3 The rights (`auth/rights.py`)

The one line Phase 4 announced: the owner of a Private Library project now has **read** access, so
every write route answers `403` (the cuts, the notes, the sheet, a rename, a delete). The changes go
through `POST /projects/{id}/edit` (a read for the rights check: it copies into the user's own
vault) and `POST /projects/{copy}/library`, and the `/library` routes; each checks the owner itself.
A user a library is shared with (Phase 14) can duplicate a version but not edit it (`409`).

# 3. Story 6.2: the pages

## 3.1 A version opens read only

The plan's tree says "Song → Versions → Project → Play | Edit". Play mode is Phase 11, so without
something more a version could not be seen before editing it. A version therefore opens on the
project page itself, **read only** (`readOnly` in the page's context, from `AudioItem.layer`):

| Step | What a version shows | What is gone |
|---|---|---|
| Header | "<song> (<version>)", the back arrow to the song, **Edit** | Save to library |
| Source | The files in order | The drag handles, the file menus, Add audio |
| Audio | The waveform, play, the zooms | Cut, restore, undo, redo, Add audio, Save, Transcribe; a migrated song with a video shows its audio, not the Video step |
| Notes, Hands | The roll in `view` mode with playback, Follow, the hand filter | Every edit gesture, undo, redo, delete, Predict hands, To right / To left, Save |
| Sheet | The sheet, Play, Print | The toolboxes (a selection opens nothing), Record, undo, redo, Save, the `⋯` |

The read-only mode is decided by the page from the backend's answer, and the backend refuses the
writes anyway (`403`), so a page that missed one control could not change a version.

## 3.2 Edit, Replace, New version, History

- **Edit** (`flow.open_edit`) duplicates the version into the vault with `basedOn` and
  `origin: {"editOf": id}`, or answers the copy already open: one copy per version, so the song can
  say **Editing** and **Edit** always leads to the same work.
- **Replace** (`flow._replace`) writes the copy's audio again (2.2), keeps the version's current state
  as `history/<projectId>/v<N>/`, and writes the copy's `project.json` fields and parts' files into
  the library project, which **keeps its id and its parts' ids** (by position), so the version row
  and any link to it stay valid. The cache of each part and the hand split cache are cleared (the
  copied `notes.pmn` gets a new time, so a split cached by time is never served for it). The copy is
  deleted.
- **New version** moves the copy into the library like a first save and clears its `basedOn`.
- **History** lists the earlier states; **Restore** keeps the current state first, then writes the
  chosen one back the same way.
- Deleting a version deletes its project and its whole history; an edit copy of it becomes an
  ordinary project.

## 3.3 The other pages

- **Songs** and **Artists** are `DataTable`s (records compared on the same fields, guideline 6)
  with a **Filter** field above them; a row opens the song or the artist.
- **One song**: the artists as links, the versions as `ListRow`s. **One artist**: its names and its
  songs. Merging moves every name of one artist to another, which keeps its default name; the app
  context asks to let names converge on one artist id.
- **Projects**: the **In my library** group of Phase 5 is gone; an edit copy says **Editing** (its
  tooltip names the version and the song), its menu adds **Open the song**, its Delete reads
  **Discard changes**.
- **Search** (`⌘K`) finds the songs of My library (title and artist) and the projects (title).
- The sidebar gains **My library**: **Songs**, **Artists**.

**Names are compared in Python, not in SQL.** SQLite's `lower()` folds only ASCII letters, so "Él"
would not have found "él"; `library/rows.py` compares names ignoring case and repeated spaces in
Python (`casefold`).

# 4. Tests

| File | Tests | What |
|---|---|---|
| `test_library.py` (new) | 13 | Save moves the project and makes the song, the artist and the version; it waits for a saved sheet (`409`); the same title and artist (any case) give one song with two versions, a taken name is refused, another artist gives another song; the audio written again (one file: a FLAC of 500 kept frames, no cut, the same revision, the original deleted, `normalized.wav` equal to the joined old one, the notes and the Sheet step unchanged); several files (the first kept, the second written again, the names kept, the joined `normalized.wav`); the temporary files go; a version is read only and Edit answers the same copy; Replace keeps the ids, the history restores; Save as a new version; delete a version and a song; rename a song and a version, the artists of a song; an artist's names and a merge; another user sees nothing |
| `test_rights.py` | changed | Row 2: the owner reads a library project and writes it only through an edit copy; a user it is shared with cannot edit it |

# 5. Q-7 and Q-8, for the user

- **Q-7, offline downloads per project.** Raised in the walkthrough with the recommendation of the
  plan: leave it for the production version. On one home server the Private Library is on the same
  disk as the app, so a download would only help a device away from home, which needs the browser
  to keep the files (a PWA with a service worker and storage limits per browser). Nothing in Phase
  6 depends on the answer.
- **Q-8, live notes from the video reader.** Still open from Phase 5 (its report, section 4.5): keep
  one job with its stages (recommended), stream the notes during the stitch, or measure the speed on
  the first seconds only. Asked again in this walkthrough.

# 6. The checks

| Check | Result |
|---|---|
| Backend, full run on the GPU (`make test-backend`) | 1,091 tests: 1,090 passed, 1 failed, the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas` (Phase 5: 1,078; the 13 of `test_library.py`) |
| `black`, `flake8`, `mypy` on the new and changed modules | clean |
| `tsc -b`, `npm run lint`, `npm run build` | clean; the build has the chunk-size warning of Phase 0 |
| `check:render`, `check:history`, `check:note-names`, `check:geometry`, `check:cuts`, `check:notes` | 60, all, 15, all, all, all passed |
| `check:projects`, signed in | every check passed, no console error (its list check now reads the vault only) |
| `check:library` (new), signed in | 27 checks passed, no console error, nothing left behind |
| `check:flow`, signed in, with the live transcription | every check passed, no console error |
| `time:flow`, the first piano sheet | 0.6 s, 0.9 s, 0.5 s (Phase 5: 0.6, 0.9, 0.5); notes saved 26.9 s, 50.5 s, 20.8 s. Its second piece is a copy of a library song (`POST /projects/{id}/duplicate` is a read), which still works with the library read only |
| `bench:sheet`, median of a hand move | Elefants 221 ms, Superestrella tutorial 279 ms, The Other Side 475 ms (Phase 5: 212, 270, 516) |
| `make db-check` on the real `.database/` | 40 projects (10 in the vault, 30 in the library; the user added one since Phase 5), no problem, after every script |
| `scripts/docs/check-links.py` | passes |

# 7. The 13 checks of the 09 guidelines

Run on the pages this phase made or touched, with the screenshots of
[`screenshots/phase-6/`](screenshots/phase-6/), all taken by `check:library` on its own song
"check-library song" (a copy of Elefants), deleted after.

| # | Check | Result |
|---|---|---|
| 1 | One sentence | Songs: find a song of my library. A song: open, edit or manage its versions. Artists: manage who sings what and under which names. Save to library: file this project under a song |
| 2 | Every sentence a label, control or fact | Two consequence lines only where a choice needs them: the Replace line ("What it is now stays in its history") and the merge line under the field |
| 3 | Words above the first content | Songs: "Songs", "Filter". A song: the title and the artists line |
| 4 | Very wide | Tables keep their content width; the version rows keep the time and the `⋯` beside each other |
| 5 | Narrow (390 px, shots 12, 13) | 0 px of page overflow; the Songs table scrolls inside its own box |
| 6 | Longest, shortest, none | Titles and artists truncate with the full text on hover; a song with no artist reads "–" in the table and "No artist" on its page; a song with no versions reads "No versions" |
| 7 | Buttons say what happens | "Save to library", "Replace the version", "Edit", "Continue editing", "Discard changes", "Restore", "Add a name", "Make default", "Merge", "Delete version", "Delete song" |
| 8 | Helper lines | "Enter adds a name" under the artists field (the field takes several names, which a first-time user would not guess) |
| 9 | Loading, empty, partial, error | Skeleton rows; "No songs yet. Save a project to the library to add one." with **Open Projects**; "No song or artist matches …" with **Clear the filter**; refusals in the backend's words (a taken version name) |
| 10 | Tab through it | The dialogs, the tables' rows, the menus; Enter saves a rename and the save dialog |
| 11 | Internal names | None: no "vault", "layer", "basedOn", "private_versions", "compact" on screen |
| 12 | First-time user | "My library", "Songs", "Artists", "Version name", "Editing", "History" |
| 13 | Anti-patterns | No lecture: the read-only version says nothing about being read only; its one button, **Edit**, says what to do |

| Shot | Page |
|---|---|
| 01 | Save to library on a project with its sheet saved |
| 02 | The song it opens |
| 03, 04 | The version read only: the Sheet (Play, Print), the Hands (play, follow, the filter) |
| 05 | Projects with an edit copy saying Editing |
| 06 | Save to library on an edit copy: Replace "original" |
| 07 | The history of a version |
| 08 | The song with two versions |
| 09 | Songs filtered |
| 10, 11 | Artists; one artist with two names, after Make default |
| 12, 13 | 390 px: Songs, a song |
| 14 | Dark: a song |

# 8. Documentation

- New: [`../../music-library/README.md`](../../music-library/README.md) and
  [`../../music-library/private-library.md`](../../music-library/private-library.md).
- Updated: `frontend/projects.md` (the header's actions, read-only versions, Save to library, the
  edit copies on Projects), `frontend/pages.md`, `frontend/README.md`, `07-database.md`,
  `08-security.md`, `backend/api.md`, `00-index.md`, `00-documentation-instructions.md`,
  `00-project-complete-overview.md`, `03-services-overview.md`; `endpoints.md` (§7 and the new §7.1),
  `paths-and-data.md` (§3 the audio written again, the new §4.7, the tables), `components.md` (the
  new §1.1, the project page, the API client, the checks), `aitu-frontend/README.md`,
  `aitu-backend/README.md`.
- The plan: "as built in Phase 6" notes in sections 8.5, 9.3, 10.1, 10.2 and 10.6; Q-7 raised.

# 9. Open points

- **Q-7** and **Q-8**: the walkthrough asks both.
- **The 30 migrated songs** were put in the library by the Phase 3 migration, not by a save: their
  cuts are still ranges, and none has saved hands (they are at the Notes step). Their audio is
  written again the first time each is replaced. Nothing needs to happen now.
- **Suggestions from the Public Library** in the save dialog wait for Phase 13.
- **Playlists**, **Shared** and **Play** of My library are Phases 10, 14 and 11.

# 10. Learnings for later phases

- **A file copied with its time can collide with a cache keyed by time.** `shutil.copy2` keeps the
  source's modification time; the hand split cache is keyed by the notes file's time. Copy with
  `copyfile` (a new time) and forget the cache of the part.
- **SQLite's `lower()` is ASCII only.** Compare user names in Python when accents matter.
- **Read only is decided twice**: the page hides the changes, and the backend refuses them, so a
  missed control cannot write.
- **Vite keeps a deleted module in its graph** after a file is split in two: the next page load asks
  for the old file and gets 404. `docker compose restart frontend` clears it.
- **A screenshot right after a click catches a fading dialog or menu**: wait about 350 ms.
