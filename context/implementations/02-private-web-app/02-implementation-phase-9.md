# 02: Phase 9 report: Recording in Sheet

Plan: [`02-plan.md`](02-plan.md) sections 11.8 and 13, and section 20, Phase 9. Checklist:
[`02-checklist.md`](02-checklist.md). Branch `feat/phase-9`, made from `master` at `ab28550` (Phase 8
merged and pushed, after the user's check). Done 2026-10-15 on the Ubuntu machine. The drawing
package `vexflow-v2` moved to 0.44.0 (section 6).

# 1. Summary

| Story | Result |
|---|---|
| 9.1 The page | `/projects/:id/passages/:passageId`: **Current** (a copy of the marked frames, read only, with its own play button) and **Proposal** (a take, drawn by the whole sheet page with its toolboxes and undo). Takes are recorded in the browser (with the passage played along, slowed to the speed, from a chosen microphone) or added from a file; **Write the proposal** keeps the chosen stretch of the take and runs the transcription, the hand split and a first sheet **in the passage's key and figure**, as one GPU job |
| 9.2 Promote | The speed (×0.25 to ×4) and the window (as long as the Current, dragged by a grip; **Fit** finds the speed at which the take fills it). **Fit to the window** with **Keep the original audio** or **Use my recording** keeps the song's length; **Replace the whole passage** changes it and says by how much. One write through the Phase 8 paste; the sheet opens with the promotion as its last step, so undo and redo work on it. The staged session is generalised as hidden projects of the vault; the two old panels and the session layer are removed |
| 9.3 Documentation | `context/backend/editing.md` and `documentation/.../editing-and-compose.md` rewritten; `context/frontend/recording-in-sheet.md` (new), `projects.md`, `annotations.md`, `annotations-stretches.md`, `pages.md`, `07-database.md`, `endpoints.md`, `paths-and-data.md`, `components.md`, `aitu-frontend/README.md`, the overviews; the plan's "as built in Phase 9" notes; the package's `04-editing.md` |

Checks at the end (section 8): backend 1,081 tests on the CPU, 1,077 passed, the 3 known CPU failures,
1 skip; the package 522 tests; every frontend check passes, the new `check:passage` too.

# 2. The design, and why it differs from the plan's wording

The plan said "the staged session of `editing/` generalised from one window of one audio to a
passage of a part". The session kept a take in a `staging/` folder and had its own transcription,
preview, peak plot and splice. Generalising it would have meant writing a second sheet for the
Proposal, a second hand split and a second length rule.

**What was built instead: the passage and each take are projects of the Personal Vault, hidden
from every list** (`projects.kind = 'passage'`, Alembic `0002`). The passage's one part is the
**Current**, made by a paste of the stretch into an empty part (`paste.paste`), so it has the
stretch's notes, marks, key and clefs and plays ranges of the song's stored files. A take is one more
project of one part. Because both are ordinary parts:

- every route of a part works on them (`/time`, `/audio`, `/pieces`), so the page draws both with
  `SheetPage` and the Proposal has every toolbox and its own undo, as the app context asks ("We must
  reuse all the components in the UI, the toolbox, and the tools");
- a take's chosen stretch is its cuts (the Audio step's rule), its transcription is
  `pipeline.transcribe_audio` with its live progress, its hands are the normal split;
- the promotion is `paste.paste` with two new options, so it has the paste's length rule, mark
  handling, audio timeline and exact undo (the user's instruction for this phase).

`origin` of the passage's project holds the page's state (`passageOf`, `fromMs`, `toMs`,
`anchorMs`, `anchorFigure`, `takes`, `take`, `speed`, `windowMs`, `sourceRevision`). Hidden projects
go with what they belong to: `bundle.delete_project` deletes the passages of a project's parts and
the takes of a passage first (`bundle.dependents`), and **Save to library** deletes the passages of
the project it saves. `GET /projects` and `bundle.list_parts` (so `GET /audio/`) leave them out. The
same stretch of an unchanged song (its notes, hands, audio revision and saved sheet, hashed) opens
its passage again, so leaving the page with the back arrow loses no take.

**The migration.** `0002_passage_projects.py` widens the check constraint on `projects.kind` with
Alembic's batch mode, which copies the table. `parts` points at `projects` with `ON DELETE CASCADE`,
so it was checked before running on real data: a database at `0001` with a project and a part,
upgraded, kept both (the migration engine runs with foreign keys off; only the app's engine turns
them on). The running backend reloads on every save, so it migrated the real `.database/` as soon as
`HEAD_REVISION` changed; `make db-backup` was taken right after (1.2 GB) and `make db-check` found no
problem (42 projects).

# 3. Story 9.1: the page

## 3.1 The backend (`editing/passages.py`, `api/passages.py`)

| Route | What |
|---|---|
| `POST /passages` `{part, fromMs, toMs}` | Snaps the stretch to whole columns of the song's sheet; `toMs == fromMs` is a new passage (a moment past the end is the end). The user must be able to write the part (a version of the library answers `403`) |
| `GET`, `PATCH`, `DELETE /passages/{id}` | The passage and its takes (`state` `recorded`, `reading`, `ready`; `jobId`; the kept stretch; `audioRevision`); the take on show, the speed (×0.25 to ×4, else `409`) and the window; discard |
| `POST …/takes` | A take from an upload (`store.save_original`, `ingest.finalize`), titled `Take N` |
| `POST …/takes/{take}/read` | The job of **Write the proposal** (key `take:<id>`, GPU queue) |
| `POST …/promotion`, `POST …/promote` | Section 4 |

The path parameter is named `project_id`, so the existing rights dependency checks the passage like
any project. A take of another passage is `404`.

**The condensed steps** (`read_take`): the stretch becomes the take's cuts; `transcribe_audio`;
`inferred_split(keep_saved=False)` and `hands_of_split(guess_unplaced=True)`, written with
`save_edit(hands_changed=True)` so every note has a hand and the Sheet step is ready; then the first
sheet: the song's settings where the passage starts (`paste._first_sheet`, the key there), none of
its marks, `anchorMs` = the passage's × the speed, `ottavas` unset, `handsRevision` current. A song
with no sheet (From scratch) gives the take no sheet: the page's defaults of a first write apply.

**A take is `ready`** when its notes are of the current cuts and every note has a hand. The first
rule also required a saved sheet, which a take of a blank song never has; a test caught it.

## 3.2 The page (`pages/piece/passage/PassagePage.tsx`)

`SheetPage` gained `step.passage` (`PassageView`): `role` `current` (read only, no bar, no title
lines, Space off through `ScorePlayer.keys`, no copy or paste listeners) or `proposal` (the
passage's `anchorMs` × the speed instead of the measured pile, the window and its drag, the
passage's actions on the bar in place of Record, Paste, Print, Save and Remove all, only Key,
Transpose and Layout in the sheet toolbox, saved by itself 1.2 s after a change, the held sheet
reported to the page for the promotion). The rest is described in
[`recording-in-sheet.md`](../../frontend/recording-in-sheet.md).

On the song's sheet: **Record this passage** is an icon of the range toolbox's title bar (the
Re-record tab is gone), **Record a passage at the end** is the bar's record icon, the blank sheet's
**Record a passage** opens a new passage, and Notes Falling's button became **Record this stretch**.
Each saves the sheet first when it has changes (the Current is a copy of the saved sheet).

**The microphone needs a secure page.** `getUserMedia` exists only over HTTPS or at `localhost`, so
from the Mac at `http://ubuntu:5173` **Record** cannot work. It is disabled there with its reason in
the tooltip, and **Add a take from a file** is offered on the empty Proposal and in the recorder.
This held for the old panels too; nobody had tried them from the Mac. Section 10 asks the user.

# 4. Story 9.2: promote

`passages._plan` reads the take's passage with the Proposal's sheet as the page holds it:

| | The take's stretch (ms of the take) | Columns | Audio |
|---|---|---|---|
| Fit, original | `[windowMs, windowMs + length × speed)` | the passage's | `keep_audio`: untouched; refused for another length |
| Fit, recording | the same | the passage's | the take's ranges at ×1; at another speed a new file (below) |
| Whole | the whole kept take | its own, rounded up | the same |

`_song_passage` reads it in the song's time: times divided by the speed; a note of a window that
starts after the window's length left out and its end cut there (the take's stretch snaps to its own
40 ms columns, which divided by the speed do not land on the passage's); `frameMs` divided by the
speed, so the paste rescales the marks' columns by `1 / speed`; and the figure named with the
song's: `anchorMs` = the passage's × `FIGURE_NEGRAS[song] / FIGURE_NEGRAS[proposal]`. A figure
renamed on the Proposal (Transpose → Figures) therefore reaches the song as a speed change at the
passage and the song's own after it (a test).

**The audio at another speed** (`_rendered`): the take's ranges written end to end at their own rate
and channels (`sources.write_ranges`, new), played faster or slower with the pitch kept
(`audio_splice.stretch_by_rate(..., keep_format=True)`, new: it used to write 16 kHz mono, which
Phase 8 had removed from the Record panel for that reason), stored as a WAV and used for exactly the
passage's length. At ×1 no audio byte is copied.

`paste.paste` gained `keep_audio`, `columns`, and `audio_name` / `audio_kind` (the file is called
"Take 2", kind `recording`, on the Source step). **A Phase 8 defect** showed here: a paste that left
a part with one whole file set the part's source kind to `passage`, which the audio metadata does not
accept, so the part could not be read (a whole short file pasted into a blank project would have done
it). `apply_audio` now keeps an upload's word and uses `segment` otherwise.

**The dialog** asks `POST …/promotion` and shows only what changes the decision: "The song gets
4.5 s longer." for a whole take of another length, and "Removed with the passage: 2 fingerings and 1
octave bracket." when the passage carries marks (`marks.dropped`, new: a mark on a column of the
passage, a range wholly inside it; key, clef and speed changes are transitions and not counted).

**Undo after promotion.** `promote` answers `beforeVersion`; the page navigates to the song's sheet
with the result and the song's saved sheet as it was before (read just before promoting). The sheet
page, once its saved reading is in, resets its history to that sheet and commits the promotion over
it (`useEditHistory.commit`), so **Undo: Promote the passage** restores the snapshot and puts the
marks back on the page, and redo restores the promoted one, exactly as a paste.

**The staged session is removed** with its panels: `api/editing.py`, `editing/session.py`,
`preview.py`, `splice.py`, `storage/staging.py`, `schemas/editing.py`, `compose.create_empty_piece`,
`append_anchor`, `passage_bounds`, `shift_marks`, `audio_splice.splice_wav` and `insert_wav`,
`history.add_mismatch`; on the page `RangeRerecordPanel`, `ComposePassagePanel`, `PeakPlot` and
`api/editing.ts`. Their tests went with them (`test_range_edit.py`, `test_compose_live.py`, one test
of `test_paste.py`), except the pure `insert_events` tests and `atempo_chain`, kept in
`test_compose.py`. 5,797 lines removed in all.

# 5. Defects found on the way

- **The player kept the old audio after a promotion.** Its address was `?v=<reloadAt>`, which
  restarts at 0 when the sheet page opens again after the passage page, so the browser served the
  file it kept for that address (a `416` showed it: a range of the old length). The address is now
  the audio revision when the page opened and `reloadAt` (`step.audioRevision`, taken once so a
  refresh of the steps does not load the audio twice). Phase 8's `check:paste` expected the old
  form; it now expects `v=<revision>.<n>`.
- **Writes of the joined audio raced with moves and deletes.** The new address made a race visible
  that older checks passed by luck (their `?v=0` came from the browser's cache): a player writing the
  joined audio of a part of several files while **Save to library** moves the folder (or deletes an
  edit copy) fails on its rename. **Save to library** and **Replace** now hold the part's audio locks
  (`piece_audio.held`, `sources.writing`) during the move and the delete; `GET /audio/{uuid}/file`
  tries once more when a restore forgot the files it was writing from; and a player that goes drops
  its source, because a paused element keeps downloading.
- **The window's grip was under the playhead** at frame 0, so a drag moved the playhead; the grip is
  now in the middle of the window's top edge.
- **A take's sheet was required for `ready`** (section 3.1).

# 6. The drawing package, `vexflow-v2` 0.44.0

`GridNotationRendererOptions.frameWindow` and `onFrameWindowMove`, `renderer.setFrameWindow`,
`getFrameWindow`, `FRAME_WINDOW_COLOUR`, `FRAME_WINDOW_GRIP`: a band over every line the window
reaches (no pointer), a line at each end, a grip on its first line; dragging the grip moves it by the
frame under the pointer, keeping its length inside the sheet; a render draws it again. Tests:
`tests/frame-window.test.ts` (3). 522 tests pass; lint clean; Prettier warns on 14 files that it
warned on before this change. `documentation/04-editing.md` has a section. Not committed in that
repository yet (section 10). The frontend image builds its own copy of the package, so `make up` was
run after each change.

# 7. Tests

| File | Tests | What |
|---|---|---|
| `test_passages.py` (new) | 16 | The Current is a copy of the stretch, hidden from every list; the same stretch of an unchanged song opens the passage again, a changed one does not; deleting the song deletes its passages and takes; discarding leaves the song to the byte; a take read in the passage's key and figure (×2: `anchorMs` 1000), every note with a hand, the Sheet step ready; the window with the original audio (the timeline to the byte, the marks after on their columns, undo to the byte); the window with the recording at ×2 (the notes, the take's 440 Hz at the passage, 220 Hz around it, the same length); the whole take (+1 s, notes and the mark after moved by 25 columns, the audio as long as the notes, undo to the byte); a renamed figure kept as a speed change; a new passage on a blank sheet; a version of the library refused; a take of another passage not found, a speed out of range refused; a passage project in no list; a quiet take raised; a take played on a MIDI piano keeps the keys of its stretch (no transcription), and with no microphone is silent |
| `test_compose.py` (new) | 7 | `insert_events` and `atempo_chain`, kept from the removed files |
| `vexflow-v2/tests/frame-window.test.ts` | 3 | The band, its ends and its grip; the drag (a start that follows the frame, the length kept, stopped at the end of the sheet); drawn again by a render, taken away |
| Removed | 57 | `test_range_edit.py` (20), `test_compose_live.py` (36), one of `test_paste.py`: they drove the removed session |

# 8. The checks

| Check | Result |
|---|---|
| Backend, full run **on the CPU** (another project held the GPU) | 1,081 tests: 1,077 passed, 1 skipped (the real-model test), 3 failed: the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas` and the two Transkun tests that fail only without a GPU. Phase 8: 1,115 tests (57 removed, 23 added) |
| `black`, `flake8`, `mypy` on the new and changed modules | clean (one `E402` in `events_to_matrix.py`, older than this phase) |
| `vexflow-v2`: `npm test`, lint, build | 522 passed (0.43.0: 519); clean |
| `tsc -b`, `npm run lint`, `npm run build` | clean; the chunk-size warning of Phase 0 |
| `check:render`, `check:history`, `check:note-names`, `check:geometry`, `check:cuts`, `check:notes` | 60, all, 15, all, all, all passed |
| `check:passage` (new), signed in | 36 checks passed, no console error, nothing left behind (projects and passages), two clean runs in a row |
| `check:projects`, `check:library`, `check:transpose`, `check:lyrics`, `check:paste`, `--only clefs`, signed in | every check passed (27, 18, 39, 29 and 3), no console error, nothing left behind. `check:paste` now expects the player's address `v=<revision>.<n>` |
| `check:flow`, signed in, with the live transcription | every check passed, no console error |
| `bench:sheet`, median of a hand move | Elefants 215 ms, Superestrella tutorial 266 ms, The Other Side 494 ms (Phase 8: 217, 268, 489) |
| `time:flow`, the first piano sheet | 0.6 s, 1.0 s, 0.5 s (Phase 8: 0.6, 0.9, 0.5); notes saved 26.4 s, 51.0 s, 21.4 s |
| `make db-check` on the real `.database/` | 42 projects, no problem, no hidden project left, after every script |
| `scripts/docs/check-links.py` | passes |

The browser scripts signed in with `AITU_MASTER_PASSWORD` of `.env`, and worked on copies only.
`check:library` now waits for the sheet's audio before **Save to library**, as a reader would (the
read race of section 11).

**Speed** (a copy of Elefants, through the API, the GPU shared with another project): opening a passage of 8 s 27 to 35 ms; adding a take 54 to 67 ms; **Write the proposal** of a 16 s take 2.0 s (transcription, hands and sheet); the facts 8 to 16 ms; a promotion fitted into the window at ×2 (its audio played faster and stored) 180 ms, a whole take at ×1 36 ms.

# 9. The 13 checks of the 09 guidelines

Run on the page of a passage (both sheets, the recorder, the range of a take, the promotion dialog,
a new passage), the range toolbox's new icon and the bar's record button, with the screenshots of
[`screenshots/phase-9/`](screenshots/phase-9/), taken by `check-passage.mjs` on its copies.

| # | Check | Result |
|---|---|---|
| 1 | One sentence | Record the passage again, compare it with what is there, and put the take into the song |
| 2 | Every sentence a label, control or fact | "Record the passage again." (the empty Proposal: what to do), "The song gets 4.5 s longer.", "Removed with the passage: …" (both only when they apply) |
| 3 | Words above the first content | The song's title, "Current · 0:09 – 0:17" |
| 4 | Very wide | The two sheets take the page's width; the take, the speed and Promote sit at the right of their rows, beside what they act on |
| 5 | Narrow (390 px, shot 13) | 0 px of sideways scroll; the empty Proposal's two buttons wrap; the header keeps Promote and `⋯` |
| 6 | Longest, shortest, none | A long title is cut with "…" (full on hover); one take shows its name, several a select; no take: the empty Proposal; a new passage has no Current and no window |
| 7 | Buttons say what happens | "Record this passage", "Record a passage at the end", "Record", "Add a take from a file", "Write the proposal", "Record again", "Fit the whole take into the window", "Choose the stretch of the take", "Promote" (a menu: "Fit to the window", "Replace the whole passage"), "Put it in", "Discard the passage" |
| 8 | Helper lines | None. The microphone's limit is the disabled Record's tooltip |
| 9 | Loading, empty, partial, error | **Write the proposal** shows the job's bar (its stages) and stays busy; a page reloaded during the job follows it; a refusal is one line above the sheets in the backend's words |
| 10 | Tab through it | Every control is a button, a select or a slider (arrows move the speed); the window's grip needs a pointer, **Fit** and the speed reach the same choices |
| 11 | Internal names | None: no "part", "project", "session", "anchor", "timeline" on screen |
| 12 | First-time user | "Current", "Proposal", "Take 2", "×2.00", "Promote" |
| 13 | Anti-patterns | No lecture; the facts of the dialog only when they change the choice |

| Shot | Page |
|---|---|
| 01 | The range toolbox's **Record this passage** and its tooltip |
| 02 | The page of a passage, no take yet |
| 03 | Recording (the recorder, the level) |
| 04 | A take's waveform and the stretch to keep |
| 05 | The Proposal, in the Current's key and figure |
| 06 | **Fit**: ×2.00, the window over the take |
| 07 | The Proposal's sheet toolbox: Key, Transpose, Layout |
| 08 | **Promote → Fit to the window** |
| 09 | The song after the promotion: **Undo: Promote the passage** |
| 10, 11 | **Replace the whole passage**: "The song gets 4.5 s longer.", and the song after |
| 12 | A new passage on a blank sheet: **Put it in** |
| 13, 14 | 390 px; dark |

# 10. Q-7, Q-8, and two questions of this phase

Q-7 (offline downloads) and Q-8 (live notes from the video reader) are unchanged since Phase 6 and
asked again in this walkthrough with the recommendations of the Phase 6 report, section 5, and the
Phase 5 report, section 4.5. Nothing built in Phase 9 depends on either.

Asked too: whether to commit and push `vexflow-v2` 0.44.0 (as for 0.43.0 in Phase 8), and how the
user wants to record from the Mac (section 3.2: `localhost` through the tunnel, a browser flag for
`http://ubuntu:5173`, or HTTPS, which is production work).

# 11. Open points

- **The microphone on `http://ubuntu:5173`** (section 3.2).
- **A read of the joined audio can still meet a move**: **Save to library** pressed within a second
  of opening the sheet, while its player's first request is being answered, can make that request
  fail once (the page is being left anyway). Fixing it needs the file opened before the move; not
  done.
- **The quality of a Proposal is the transcription's.** The check's takes are the passage's own audio
  slowed with `atempo`, which MuScriptor reads worse than a piano played; its hand split put part of
  the melody in the left hand. A real take was not recorded on this machine (no microphone).
- **The window over a take shown at ×1** is drawn in the take's columns; at a speed other than ×1 its
  length is the passage's × the speed, so it grows and shrinks with the speed rather than the notes
  moving under it.
- **Abandoned passages** stay hidden until their song is deleted or saved to the library (they are
  reopened by marking the same stretch while the song is unchanged).

# 12. After the user's first review (2026-10-15)

- **The metronome is removed.** Its clicks came out of the speakers into the take. `useClickTrack` is
  deleted; nothing else used it.
- **The recorder asks for the microphone with the browser's voice processing off** (echo
  cancellation, noise suppression, automatic gain): they are made for speech, and they cut and pump a
  piano. A **Microphone** list (shown when the computer has more than one input, the choice kept in
  this browser) picks the input; until now the system's default was used.
- **A take is raised to a level that reads.** With the automatic gain off, the camera microphone gave
  a take whose waveform was nearly flat. `formats.louder` puts its loudest sample at -1 dB (one gain,
  at most +40 dB, never lowered) and the take is stored as FLAC. Test: a take at 1 % of full scale is
  kept above 80 %.
- **A MIDI piano as a source of a take** (asked by the user, who will test with a piano later). The
  browser's Web MIDI (`audio/useMidiInput.ts`) hears the keys from the moment the sound starts
  recording; **Notes from: Microphone / MIDI piano** in the recorder, **Sound** (a microphone or **No
  sound**), the keys counted while recording. The backend keeps them (`midi.json` of the take) and
  **Write the proposal** passes them to `pipeline.transcribe_audio` as an engine named `midi`, so the
  notes are the keys of the kept stretch with a transcription's header and history. Two choices made
  without the user, easy to change: a note ends when its key comes up (the sustain pedal is not
  read), and the sound is the microphone's, recorded at the same time (none with **No sound**: the
  take is silence as long as its keys). Checked with a simulated MIDI piano in `check:passage` (three
  keys, no sound: the Proposal has exactly those three notes; two keys with the fake microphone) and
  two backend tests. Not checked with a real piano.

# 13. Learnings for later phases

- **A media address must change with the audio, and a page's own counter restarts when it opens
  again.** Put the audio revision in the address, taken when the page opens.
- **A folder that is moved or deleted while a file is written in it** fails the write: hold the
  writer's lock around the move. A paused `Audio` keeps downloading; remove its `src` when it goes.
- **A migration that copies a table** on SQLite deletes what points at it with `ON DELETE CASCADE`
  if foreign keys are on: check on a copy with data first. The running backend reloads and migrates
  the real database on save, so back it up at once.
- **`uvicorn --reload` loads a refactor half done** (a module deleted before its import): change the
  imports in the same step as the deletion.
- **Recording in a headless browser**: Chromium's `--use-fake-ui-for-media-stream
  --use-fake-device-for-media-stream`; a file field is set directly with `setInputFiles`.
- **Reuse a whole page through a role prop** (the Proposal is `SheetPage`) rather than a second view:
  every later tool of the sheet reaches it for free.
