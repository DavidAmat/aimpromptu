# 02: Phase 8 report: copy and paste, and From scratch

Plan: [`02-plan.md`](02-plan.md) sections 4 (rule 2), 8.5, 10.3, 11.2, 11.8 and 12, and section 20,
Phase 8. Checklist: [`02-checklist.md`](02-checklist.md). Branch `feat/phase-8`, made from `master`
at `4731842` (Phase 7 merged and pushed at the start of this session, after the user's check;
`vexflow-v2` `plan-resume` pushed with its five commits, package 0.43.0). Done 2026-10-09 on the
Ubuntu machine. Checked by the user in the browser on 2026-10-15 and merged into `master`.

# 1. Summary

| Story | Result |
|---|---|
| 8.1 Copy and paste | **Copy** (range toolbox, note toolbox, ⌘C, and a marked stretch of a read-only version) keeps a reference: the part and a stretch in milliseconds. **Paste** (floating bar, ⌘V) puts it in at the cursor, or over the marked stretch, in one backend write (`POST /time/{uuid}/paste`): the notes, every kind of mark (with the key, the clefs and the speed it had, and the target's back after it), and the audio as ranges of the stored files (no byte copied); everything after moves. The page's unsaved sheet travels with it and comes back saved. One undo step; undo and redo put a snapshot back (`POST …/versions/{n}/restore`), exactly. The source is read with the rights table (any part the user may read), the target written (a library version answers `403`). The note under rule 2 in `wall-clock-rewrite.md` |
| 8.2 From scratch | **New project → From scratch**: "Untitled project", an empty `notes.pmn`, opened on its Sheet step with no step tabs; the empty sheet offers **Record a passage** and **Paste the copied passage**; the steps appear once a passage brings audio. The audio of a part of several entries is checked at every join, sample by sample (`scripts/check_joins.py`), and the browser plays it at the length of the piece |
| 8.3 Documentation | `context/backend/editing.md`, `editing-and-compose.md` (section 9 new), `endpoints.md`, `paths-and-data.md`, `07-database.md`, `pieces-and-revisions.md`, `projects.md` (section 5 new), `pages.md`, `annotations.md`, `annotations-stretches.md`, `annotations-notes.md`, `components.md`, `aitu-frontend/README.md`, `wall-clock-rewrite.md`; the plan's "as built in Phase 8" notes |

Checks at the end (section 7): backend 1,115 tests on the CPU (the GPU was held by another
project), 1,111 passed, the 3 known CPU failures, 1 skip; every frontend check passes, the new
`check:paste` too (29 checks).

# 2. Story 8.1: copy and paste

## 2.1 The clipboard

`state/passageClipboard.ts`: `{"type": "aimpromptu/passage", "part", "project", "title", "fromMs",
"toMs"}`, kept in `localStorage` (it outlives moving to another project and reaches every tab,
`useSyncExternalStore` with the `storage` event). ⌘C also writes it as JSON text into the system
clipboard in the `copy` event, and ⌘V reads it in the `paste` event: the app is plain HTTP on the
home network, where `navigator.clipboard` does not exist, but the two events still carry the
clipboard. A keydown fallback pastes the app's own copy when the browser sends no `paste` event
(nothing editable focused). The plan named `project` and `layer`; the routes only need the part
(it names its project, and `locate` its layer), so `project` is informative and `layer` is not
stored: the read check reads the layer of the part when it pastes.

## 2.2 The paste (`editing/paste.py`)

`read_passage(part, fromMs, toMs)` snaps the stretch to whole columns of the source's sheet and
reads, without writing: the notes whose onset column is inside it (taken off the page or not), cut
where it ends, counted from its start, ids dropped; the marks of the stretch (`marks.extract`,
ranges clipped); the ranges of stored files it plays (`audio_timeline.passage_pieces`, across cuts
and several files).

`paste(part, passage, at_ms, replace_to_ms, sheet)` works everything out first, then keeps the part
(`history.snapshot_current`) and writes:

| | What |
|---|---|
| Over a stretch | `_remove_events` (notes of the stretch out by onset column, later notes earlier, a note sounding into it cut), `_cut_transitions` (`marks.cut_out`; a key, clef or speed change inside moves to the start so the music after reads as before), `audio_timeline.remove` (its audio becomes cuts) |
| Notes | `compose.insert_events` with placement `insert`: the Insert of Epic 13, unchanged |
| Marks | `marks.shift(straddle="tear")`, then `marks.put_in`; then `_transitions`: the key, each hand's clef and the speed in force where the copy starts are written at the insertion point, and the target's again where the passage ends when music follows. A key pasted at column 0 is the sheet's key; a clef cannot be stored at column 0 (package limit, Phase 7) |
| Audio | `audio_with`: the pieces into the target's timeline (`insert_with_origins`), with stored silence where the passage plays longer than its audio or the moment is past the end of the audio; the files named `"<title> m:ss–m:ss"` (kind `passage`) and `Silence`. `apply_audio` writes the timeline and `project.json`, gives the target the source's 16 kHz copy when it has one (no second decode), and forgets the derived audio |
| Revisions | The audio revision goes up and the notes are written with it (`save_edit(before=header with audio_revision)`), so the Notes step stays current; `hands_changed` so the hands follow when complete; the sheet saved for the new hands revision when it was current |

A failure after the snapshot puts the snapshot back. A target with no music takes the source's
sheet settings (`_first_sheet`). A target with audio and no notes answers `409`.

**Not in the plan, decided here.** (1) A range of the target across the insertion point **tears**
(it ends there and goes on after the passage) rather than widening as a composed passage does: the
pasted music is not part of the target's octave bracket or spacing. A lyrics piece and a trill only
end, so their words or held note are not printed twice. (2) The **speed** in force (what a gap is
worth) is carried like the key, when the two differ by more than 2 %, so a passage from a slower
song keeps its figures. (3) **The page's unsaved edits are saved by the paste.** The marks have to
move in the sheet the reader sees, and moving them only on the page (as Transpose does with its key)
would leave the saved sheet's marks on the wrong music if the reader left without saving; so the
page sends its sheet and the backend saves it moved.

## 2.3 The timeline with ranges of files (`storage/bundle.py`, `audio/timeline.py`)

Phase 5 made the timeline the files of the Audio step laid end to end (the axis) with cuts as gaps.
A pasted passage is a range of another file in the middle of that axis, so `timeline.json` gained
`ranges`: for each entry of `sources`, the range of its file it stands for, or `null` for the whole
file (absent when every entry is whole, so older files read unchanged). `Timeline.items()` gives
`(hash, from, to)` per entry, `axis()` their lengths, `joined` says when the part's original is the
entries joined. `segments_for_axis` and `_cuts_of_axis` read the ranges; `audio/sources.py` makes
`normalized.wav` and the played FLAC from each entry's range; `audio/store.py` keeps the ranges
through reorder and remove; `audio/compact.py` writes an entry that is a range as a new file on
**Save to library**; the export and import carry them. A file a passage lands inside comes twice in
`sources`, which Phase 5 already allowed.

## 2.4 Undo and redo

`history.snapshot_current` now also keeps `source.json` (the part's entry of `project.json`, so the
files keep their names), and `history.restore(part, n)` keeps the current state as the next
snapshot, copies `v<n>` back (`copyfile`: a new modification time, Phase 6 learning), deletes a file
the snapshot did not have, and forgets the derived audio. `POST /time/{uuid}/versions/{n}/restore`
answers `{keptVersion, sheet}`. On the page, `useEditHistory.commit(label, next, effects)` (new) makes
the paste one step; its undo restores `beforeVersion` and remembers `keptVersion` for the redo, and
both read the saved sheet back as the page's "saved" state. Measured on copies: undo gives the notes
and the files back exactly, redo the pasted ones, and the backend test compares `notes.pmn`,
`sheet.json` and `timeline.json` byte for byte.

## 2.5 The page

**Paste** sits beside Record on the floating bar; its tooltip is `Paste “<title>” 0:07 – 0:08 at the
cursor` or `… over the marked frames`, ⌘V. **Copy** is an icon in the title bar of the range
toolbox and of the note toolbox (the frames from the first picked onset to the end of the longest
note), ⌘C. A version of My library is read only, but a stretch can be marked on it and a small
*Frames* panel offers **Copy this stretch**: a version is a source of a paste. A short line says
"Copied 0:07 – 0:08" or "Pasted 1.0 s". After a paste the ladder and the sheet are read again
(`reloadAt`, which does not start the edits again), the cursor is put back at the start of the
passage and brought on screen, and the step status is refreshed (the tabs' dots).

## 2.6 Defects found on the way

- **The browser played the old audio after a paste.** The player's address
  (`/audio/{id}/file`) does not change when the audio does, and Chromium kept the media file for
  that address despite `no-cache`: `check:paste` measured 233.35 s for a piece of 234.35 s. The
  sheet's player now takes a `version` (the page's reload count), and the Audio and Notes steps add
  the audio revision (`audioApi.fileUrl(uuid, normalized, revision)`). This was already true of a
  passage put in by Record; nobody had measured it.
- **Record wrote the whole part again at 16 kHz.** A passage put in by the Record panel replaced
  the part's audio with `normalized.wav` grown by the take: the quality of every other file was
  lost, and on a part with cuts the take landed at the wrong second (`normalized.wav` still holds
  the frames cut away). It now goes into the timeline like a pasted passage (`session._place_audio`
  through `paste.audio_with`; an append writes over trailing audio by cutting it first).
- **An insertion left five kinds of mark behind.** `compose.shift_marks` did not move the clef
  changes, the beam joins, the spacings, the even spacings or the staff gaps. One list of every mark
  (`editing/marks.py`) now serves the insert, the paste, the cut and the copy.
- **`project.json` wrote `lyrics: null` and `lyricsPool: null` on every part** (Phase 7), against its
  documentation ("absent until saved") and `test_bundle.py`. `write_project` leaves them out.

# 3. Story 8.2: From scratch, and the joins

`POST /projects` with `scratch: true` makes the project with its part's source `composed`, an
empty `notes.pmn` and `frameMs` 40. `pieces/status.py` calls a part **scratch** when its source is
`composed` and it has no audio: Source and Audio `missing`, the Audio tab closed ("Record or paste a
passage first."), `resume` `sheet`, and `scratch: true` in the answer. Limited to `composed` parts so
the many tests that write notes for a part with no audio read as before. The project page hides the
step tabs while `scratch`; the sheet's empty state ("Nothing to write yet.") offers **Record a
passage** (the Record panel of Phase 2 until Phase 9) and **Paste the copied passage** (its tooltip
names it). A header with no title reads "Untitled project". The first paste takes the source's key
and figures; the steps then appear, all ready.

**Every join** (Task 8.2.2). `aitu-backend/scripts/check_joins.py <partId>` compares each entry of
the part's `normalized.wav` with its own 16 kHz copy, and each entry of the played FLAC with its own
file decoded at the same rate and channels, away from the 5 ms fades, and the lengths with the
entries. Two things the first runs showed, and were the check's, not the audio's: the played file is
at 48 kHz when one file is (it was read at 44.1 kHz), and a decoded MP3 goes past full scale where the
16-bit file stores full scale, per channel (compared per channel after clipping). Measured on a copy
of Cara de cul (three files, a 12 s passage of Elefants pasted at 0:30): 3 joins, the engine's audio
equal to the sample, the played audio within 0.000015 (half a step of 16-bit audio). `check:paste`
runs it on its own copies: the Elefants copy with a passage of Superestrella (4 joins) and the
scratch project (1 join). The page's player loads the joined audio at the length of the piece.

# 4. Speed

- A paste of 12 s into a 4-minute part: about 0.1 s on the backend (the request, from `curl`).
- The joined audio is written on the next play (`ensure_listen`): decoding the files of a 4-minute
  part and writing the FLAC takes a few seconds once; `check_joins.py` does that and both
  comparisons in 3.6 s.
- `bench:sheet` and `time:flow`: section 7.

# 5. Tests

| File | Tests | What |
|---|---|---|
| `test_paste.py` (new) | 17 | The timeline: a passage into the middle of a file with a cut, a cut across the insertion point split, a stretch taken out as cuts, silence past the end, the ranges through segments and cuts. The paste: notes (in, moved, new ids), marks (fingering moved and arrived, key at both edges, bracket and words clipped), the files and their names, the Sheet and Notes steps current; the audio at every join on `normalized.wav` and on the played FLAC (by pitch: 220 Hz and 440 Hz tones); undo and redo byte for byte; a paste over a stretch (notes out, marks moved, audio as cuts); the page's unsaved sheet saved with the key at column 0; whole columns; an empty stretch refused; From scratch (status, the first paste, the steps); Save to library writes the ranges as files; export and import keep them; a recorded passage after a paste keeps the pasted audio and the Notes step current |
| `test_rights.py` | 1 new | From one's own vault, own library and the Public Library: 200; from another user's vault or library: 404; from a library shared with one: 200; into a version of one's library: 403; into another user's work: 404 |
| `test_bundle.py` | changed | A snapshot holds `source.json` too |

# 6. Rule 2

The note is under rule 2 in [`wall-clock-rewrite.md`](../01-mvp/01-epics-master-plan/plan/wall-clock-rewrite.md):
what changed (Q-3), the three edits that change the length and the one operation they use, and why
the rule still holds for a reader (no mark is left on music that moved). `editing-and-compose.md`
section 7 says `compose.py` and `paste.py` are the only modules that change a length.

# 7. The checks

| Check | Result |
|---|---|
| Backend, full run **on the CPU** (another project held 11 GB of the GPU) | 1,115 tests: 1,111 passed, 1 skipped (the real-model test), 3 failed: the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas` and the two Transkun tests that fail only without a GPU. Phase 7: 1,095 tests |
| `black`, `flake8` on the new and changed modules; `mypy` on `editing/`, `audio/`, `bundle.py`, `status.py`, the routes | clean, except three `mypy` errors in `api/time_score.py` lines this phase did not touch (the peaks, from 2026-08-08) |
| `tsc -b`, `npm run lint` | clean |
| `check:render`, `check:history`, `check:note-names`, `check:geometry`, `check:cuts`, `check:notes` | 60, all, 15, all, all, all passed |
| `check:paste` (new), signed in | 29 checks passed, no console error, nothing left behind |
| `check:projects`, `check:library`, `check:transpose`, `check:lyrics`, `--only clefs`, signed in | every check passed, no console error, nothing left behind. `check:projects` first failed on its own expectation that **From scratch** is disabled; the expectation now says it is offered |
| `check:flow`, signed in, with the live transcription | every check passed, no console error |
| `bench:sheet`, median of a hand move | Elefants 217 ms, Superestrella tutorial 268 ms, The Other Side 489 ms (Phase 7: 214 to 221, 273 to 286, 521 to 532) |
| `time:flow`, the first piano sheet | 0.6 s, 0.9 s, 0.5 s (Phase 7: the same); notes saved 26.4 s, 51.0 s, 21.4 s |
| `make db-check` on the real `.database/` | 40 projects, no problem, after every script |
| `scripts/docs/check-links.py` | passes |

The browser scripts signed in with `AITU_MASTER_PASSWORD` of `.env`, and worked on copies only.

# 8. The 13 checks of the 09 guidelines

Run on the floating bar's Paste, the Copy of both toolboxes, the read-only *Frames* panel, the blank
sheet of From scratch, the **New project** menu and the short notices, with the screenshots of
[`screenshots/phase-8/`](screenshots/phase-8/), taken by `check-paste.mjs` on its copies.

| # | Check | Result |
|---|---|---|
| 1 | One sentence | Copy: keep this stretch to put it somewhere else. Paste: put the copied stretch here. From scratch: start a sheet with nothing on it |
| 2 | Every sentence a label, control or fact | "Nothing to write yet." (existing) and the two buttons; "Copied 0:07 – 0:08" and "Pasted 1.0 s" are status, gone after 2 s |
| 3 | Words above the first content | The blank project: "Untitled project", then the two buttons |
| 4 | Very wide | Paste is one icon among the bar's; the empty state's two buttons sit together in the middle |
| 5 | Narrow (390 px, shot 09) | 0 px of sideways scroll; the bar wraps Save onto a second row, as before |
| 6 | Longest, shortest, none | A long source title is in the Paste tooltip only (the blank sheet's button says "Paste the copied passage"); nothing copied: Paste disabled, "Copy a passage first"; on the blank sheet the Paste button is absent |
| 7 | Buttons say what happens | "Copy this stretch", "Copy the frames of these notes", "Paste “…” 0:07 – 0:08 at the cursor" / "over the marked frames", "Paste the copied passage", "From scratch — A blank sheet: record or paste" |
| 8 | Helper lines | None added |
| 9 | Loading, empty, partial, error | The sheet's place is kept with its spinner while it is read again; a refused paste is the floating bar's message in the backend's words ("Transcribe this project first…"); the Paste button is busy while it writes |
| 10 | Tab through it | The Copy icons and Paste are buttons in the tab order; ⌘C and ⌘V |
| 11 | Internal names | None: no "part", "timeline", "range", "snapshot", "version" on screen. The Source step calls a pasted file "Pasted" |
| 12 | First-time user | "Copy", "Paste", "From scratch", "Untitled project" |
| 13 | Anti-patterns | No lecture on the blank sheet; no warning that a paste moves what follows (it is undoable, and the sheet shows it) |

| Shot | Page |
|---|---|
| 01 | A stretch of the source marked, the range toolbox's Copy and its tooltip |
| 02 | The target with the cursor placed, Paste's tooltip |
| 03 | The target after Paste: the passage at the cursor with its own key, clefs and bracket, "Pasted 1.0 s" |
| 04 | After undo |
| 05 | ⌘V over a marked stretch |
| 06 | New project: From scratch |
| 07 | The blank sheet: Record a passage, Paste the copied passage |
| 08 | The blank project after Paste: the steps appear |
| 09 | 390 px: the sheet and the bar |
| 10, 11 | Dark: the sheet with Paste's tooltip; the New project menu |

# 9. Documentation

- Context: `backend/editing.md` (paste, the take into the timeline, every mark moves),
  `frontend/projects.md` (section 5, Copy and paste, and From scratch; the New project table),
  `frontend/pages.md`, `frontend/annotations.md` (the bar, the table of edits written onto the
  recording, the length rule), `annotations-stretches.md`, `annotations-notes.md`,
  `07-database.md`, `backend/pieces-and-revisions.md` (`scratch`), `wall-clock-rewrite.md` (rule 2).
- Detail: `editing-and-compose.md` (sections 5 to 9), `endpoints.md` (the two routes, `POST
  /projects` with `scratch`, the status's `scratch`), `paths-and-data.md` (`ranges`, the kinds of
  file, `source.json`, the restore), `components.md` (the new modules), `aitu-frontend/README.md`.
- The plan: "as built in Phase 8" notes in sections 8.5, 10.3, 11.2, 11.8 and 12.

# 10. Q-7 and Q-8, for the user

Unchanged since Phase 6 (its report, section 5): Q-7, offline downloads per project, recommended to
leave for the production version; Q-8, live notes from the video reader, recommended to keep one job
with its stages (the Phase 5 report, section 4.5). Asked again in this walkthrough. Nothing built in
Phase 8 depends on either.

# 11. Open points

- **Record (the panel of Epic 13) is still not undoable**, and placing a passage still starts the
  sheet's history again: Phase 9 replaces the panel and puts it on the same snapshots as a paste.
- **No version of My library has a saved sheet yet** (the 30 migrated songs are at the Notes step),
  so the read-only *Frames* panel with **Copy this stretch** could not be opened on real data; a
  paste from a library version was checked through the API on real data, and the panel in the
  build only.
- **The Copy button does not fill the system clipboard** (only ⌘C does): the browser allows it only
  over HTTPS. The app's own clipboard is what Paste and ⌘V use, so nothing depends on it.
- **A clef cannot be stored at column 0** (package limit): a passage pasted at the very start keeps
  the target's clefs there.
- **Copy of the whole sheet** (a whole project as a passage) is From other projects, Phase 10.

# 12. Learnings for later phases

- **A media file is kept by its address.** After any write that changes a part's audio, the player
  must ask at a new address (a revision in the query); `Cache-Control: no-cache` was not enough in
  Chromium.
- **A check of audio must compare like with like**: the same rate, the same channels, and full
  scale clipped per channel, or it reports the decoder rather than the join.
- **One list of every mark.** A length change that names the kinds of mark it moves forgets the
  next kind; `editing/marks.py` is the list, and a new mark is added there.
- **Work everything out before the snapshot**, then write; a failure after it restores it. The
  stored file of silence is the only thing written before.
- **A page edit that must move with a backend write travels in the request.** The paste carries
  the page's sheet; the alternative (moving marks on the page only) leaves the saved sheet wrong if
  the reader leaves without saving.
- **The browser's scroll moves what a script clicks**: bring an element into view before reading
  its box (`scrollIntoViewIfNeeded`), above all after the page itself scrolls to the cursor.
