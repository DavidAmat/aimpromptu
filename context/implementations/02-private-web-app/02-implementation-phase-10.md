# 02: Phase 10 report: From other projects, and the playlists

Plan: [`02-plan.md`](02-plan.md) sections 6.3, 8.4, 10.4 and 14, and section 20, Phase 10. Checklist:
[`02-checklist.md`](02-checklist.md). Branch `feat/phase-10`, made from `master` at `24b246d` (Phase
9 merged and pushed, after the user's check). Built 2026-10-15 on the Ubuntu machine. Checked by the
user in the browser on 2026-10-15 and merged into `master`. Q-7 and Q-8
are answered (Phase 9 report, section 10); Q-5 and Q-6 belong to Phase 12. `vexflow-v2` did not
change.

# 1. Summary

| Story | Result |
|---|---|
| 10.1 From other projects | `/projects/compose`: a picker over the projects with notes of Projects and My library, the chosen project's sheet read only, **Add this stretch** (a marked stretch) or **Add the whole sheet**, the passages listed in order with **Sequential** / **Subheader** (and its **Title**) between two, dragged or moved by `⋯`, kept in the browser until saved. **Save as song** and **Save as integrated playlist** ask a title and make the project (`POST /projects/compose`): one part per run of sequential passages, a new part at each subheader, each passage a paste of Phase 8 at the end of its part |
| 10.2 Integrated playlist | A project of more than one part lists its parts beside its Sheet step (`PartsPanel`): a click opens that part (every step follows it), the sheet is titled by the subheader; **Rename**, drag or Move up/down, **Join with “…”** (a paste at the end of the part before); **Start a new part here** in the range toolbox splits a part (a paste of the rest into a new part, then the new `paste.cut`) |
| 10.3 Songs playlist | `/playlists` and **My library → Playlists**: the songs playlists and the integrated playlists of the library, **New playlist**; one playlist's songs with their version and stretch, reordered by dragging, another version, the whole song, removed, **Add a song**; **Make a playlist of N** from songs ticked on Songs; **Add to a playlist** from a version's `⋯` and from a stretch of its read-only sheet |
| 10.4 Documentation | `context/frontend/playlists.md` (new), `projects.md`, `pages.md`, `annotations-stretches.md`, `context/backend/editing.md`, `07-database.md`, `music-library/private-library.md`, `00-index.md`; `editing-and-compose.md` (section 4 new), `endpoints.md` (section 7 and 7.2), `paths-and-data.md`, `components.md` (section 3.2 new), `aitu-frontend/README.md`; the plan's "as built in Phase 10" notes |

Checks at the end (section 7): backend 1,093 tests on the CPU (the GPU was held by another project),
the 3 known CPU failures, 1 skip; every frontend check passes, the new `check:compose` too (24
checks).

# 2. Story 10.1: From other projects

## 2.1 The design, and where it differs from the plan

The plan named the page `/projects/:id/compose`, so a project would exist while passages are
chosen. **Built instead: `/projects/compose`, and the chosen passages are kept in the browser**
(`state/composeDraft.ts`, `localStorage`, like the clipboard of Phase 8) until **Save** makes the
project. The list holds references only (a part and a stretch), as the clipboard does, so it costs
nothing and needs no hidden project, no new kind of project and no migration; a reload or a visit to
another page keeps it; nothing is left in Projects when the reader gives up. The cost: the list is
of one browser, not of the user's other devices.

**Save as song and Save as integrated playlist both keep the subheader joins as parts.** The app
context lets the reader choose Sequential or Subheader before choosing how to save, and a song with
subheaders ("Coldplay mashup" with "Clocks", "Fix You") is a fair reading of it. So the two buttons
differ only in `kind`, which Play mode (Phase 11) reads to offer the parts as sub-songs, and which
the Playlists page lists. A one-part project has no subheader.

## 2.2 The backend (`editing/parts.py`, `POST /projects/compose`)

`assemble` groups the passages (a new group at each `subheader` join), makes the project with one
empty part and adds one per further group (`bundle.add_part`, new), names the parts (the subheader
typed, or the source's title), records `origin: {"composedFrom": [...]}`, then pastes each passage
at the end of its part: `paste.paste(part, paste.read_passage(source, from, to), at_ms=whole_ms(part))`.
`whole_ms` (new) is the length of the notes or the audio, whichever is longer, rounded up to whole
columns, so a whole part is a stretch that holds every note and the next passage starts after its
last column. The snapshots the pastes kept are deleted at the end (a new project has no earlier
state, as a duplicate). Any failure deletes the project. The route checks the read right of every
source (`require_part`), so another user's part answers `404`.

So each passage arrives as a paste does: its notes with new ids and their hands, every mark of the
stretch, the key, each hand's clef and the speed in force where it starts (the next passage's key
change is written where it lands), and ranges of the stored audio files (no byte copied). Because
the notes have their hands and the sheet is saved for them, every part opens on a ready Sheet step.

**A Phase 8 defect** showed here: a paste into an empty part took the source's base speed
(`anchorMs`), not the speed in force where the copy starts. A stretch after a speed change of its
song printed its figures wrong. `paste._transitions` now gives an empty target the passage's speed.

## 2.3 The page (`pages/compose/ComposePage.tsx`)

The header: back to Projects, **Save as integrated playlist**, **Save as song** (disabled with no
passage). The picker: `GET /projects?layer=vault&layer=private` with notes, a version named "<song>
(<version>)", the layer as status, a filter. The source: its name, a **Part** select for a project
of several parts, **Choose another project**, **Add the whole sheet**, and `SheetPage` read only
with `stretchAction` (new: a button beside **Copy this stretch** in the read-only *Frames* panel).
A project with no sheet yet says "This project has no piano sheet yet: it can only be added whole."
and offers **Add the whole project**. The list: `RailRow`s (moved from the page of a passage to
`src/ui/` and given a number, a `⋯` and a drag handle, `useRowDrag`) with `JoinControl` between two.
**Save** opens one field, **Title** (the passages' titles at first), then the project's Sheet step.

# 3. Story 10.2: the parts of a project

`bundle.add_part`, `remove_part` and `reorder_parts` keep `project.json`, the `parts` rows (their
`position` is unique per project, so they are renumbered in two passes) and the folders in step.
**The id of the project is always one of its parts**, because the step routes and the links take
it: `remove_part` refuses it, and a join keeps it (when the lower part carries it, the upper part's
music is pasted at its start instead of the lower part's at the end of the upper).

| Change | How |
|---|---|
| Rename | `parts[].subheader` |
| Reorder | `PUT /projects/{id}/parts` |
| Join | `paste.paste(upper, read_passage(lower, 0, whole))` at the end, then `remove_part(lower)` (its folders, history, row, the passages open on it, the audio no project uses) |
| Split | `add_part` after it, `paste.paste(new, read_passage(part, at, whole, sheet))` at 0, then `paste.cut(part, at, whole, sheet)` |

`paste.cut` (new) is the paste's write that takes a stretch out, the opposite of a paste: the notes
by onset column (those after move earlier), the marks (`marks.cut_out`; a key, clef or speed change
inside moves to its start when music follows), the audio as cuts, the part kept as a snapshot first,
so `POST …/versions/{n}/restore` undoes it to the byte (a test). It is in `paste.py` because only
`compose.py` and `paste.py` change a length.

**The Sheet step shows one part at a time**, with the parts on its left (`PartsPanel`), titled by
its subheader. The plan asked to draw the parts one after the other with each subheader between
them. Each part has its own toolboxes, undo history, saved sheet and player; drawing several
editable sheets on one page would multiply them and leave undo unclear across parts. The continuous
drawing belongs to Play mode, whose plan already has a continuous page (Phase 11). Section 9 asks
the user.

**Start a new part here** sits in the range toolbox's title bar (not at frame 0), on every project
of the vault, so a song can be split too; the panel then appears. The page's sheet, unsaved edits
included, travels with the split and is saved. Joins and splits are not steps of the sheet's undo
(they change two parts); a split is taken back by a join and the other way round.

**A defect older than this phase** showed on the first split: the first half of a part opened with
every figure twice as long ("corchea = 435 ms" where its song reads 220 ms). The sheet page measured
the highest pile of gaps again each time it opened (`GET /time/{uuid}/default-reading`) and never
read back the length the saved sheet keeps (`anchorMs`). On a whole song the two agree; after a
paste, a cut or a split the notes are others, the pile can move, and every figure is renamed, while
the backend's paste reads the speed of a sheet from the saved length. The page now draws from the
saved length (`SheetEdits.savedAnchorMs`, from `editsFromSaved`; `null`, the measured pile, for a
sheet never saved). Checked in the browser on a copy of Elefants split at 0:15: 220 ms on both
halves, no unsaved dot; every sheet check passes again (section 7).

# 4. Story 10.3: songs playlists

`library/playlists.py` and `api/playlists.py` use the tables of revision `0001` (`playlists`,
`playlist_items`), so no migration. An item is a song of the owner's library, the version chosen
(`project_id`; the song's first when `NULL`) and an optional stretch. Every route checks the owner
(`404` for another user's playlist, song or version), as the library routes do. A deleted version
sets `project_id` to `NULL` (the item then shows the first version); a deleted song sets `song_id` to
`NULL`, and the item is dropped when the playlist is next read.

The pages: **Playlists** (`PlaylistsPage`, a `DataTable` of the songs playlists and of the library's
integrated playlists, whose row opens their song), one playlist (`PlaylistPage`: rows dragged by a
handle, each a `ListRow` with the song and its artists, the version, the stretch or "Whole"; `⋯`:
Open, **Use “<version>”**, **The whole song**, Move up/down, **Remove from the playlist**; **Add a
song**; Rename, Delete). **Make a playlist of N** on Songs (`DataTable` gained row checkboxes),
**Add to a playlist** in a version's `⋯` and in the *Frames* panel of a version's read-only sheet
(`AddToPlaylistDialog`: a playlist, or a new one). **Play** waits for Play mode.

# 5. Speed

Measured through the API on copies (the GPU shared with another project; none of this uses it):

- `POST /projects/compose` of three passages (20 s of Elefants, the whole of Superestrella's tutorial
  3:10, the whole of Elefants 3:55; two parts): 111 ms.
- A join of those two parts (7:25 in one part): 84 ms. A split at 1:00: 101 ms. `GET …/parts`: 15 ms.
- The joined audio of a part is written on its first play, as for a paste (Phase 8 report, section 4).

# 6. Tests

| File | Tests | What |
|---|---|---|
| `test_parts.py` (new) | 7 | A project from other projects: one part per subheader, titled by the source and the subheader; each passage's notes, key (Bb, then C where the second song starts), fingering where it lands; the audio by pitch (440 Hz, then 220 Hz from 2 s); no audio copied; the sources unchanged; `composedFrom`; no history; every Sheet step ready. A song of one part has no subheader. A source with nothing in it refuses the whole and leaves nothing; a missing part is `404`. Rename, reorder (the rows' positions), join (the project's part kept, the other's folder and row gone), split (notes and audio of each half, both sheets ready), the refusals. A version of the library refuses (`403`). The project's part cannot be removed. `paste.cut` and its undo to the byte |
| `test_playlists.py` (new) | 3 | A playlist from two songs (first versions, every version offered), another version, a stretch, the whole song, a version of another song refused, a backwards stretch refused, reorder and rename, add, remove, delete (the songs kept); a deleted version falls back to the first, a deleted song leaves; a title and the library's songs required |
| `test_rights.py` | 2 new | From other projects reads every source with its row (another user's part `404`); a playlist is its owner's (another user's song `404`, another user's playlist `404`, lists their own) |

# 7. The checks

| Check | Result |
|---|---|
| Backend, full run **on the CPU** (another project held 15 GB of the GPU) | 1,093 tests: 1,088 passed, 1 skipped (the real-model test), 4 failed: the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas`, the two Transkun tests that fail only without a GPU, and `test_every_piece_of_the_library_round_trips_through_the_sparse_form`, which lists the real `.database/` when it loads and lost a copy that a browser check deleted during the run; alone it passes (34 of 34 in `test_pmn.py`). Phase 9: 1,081 tests |
| `black`, `flake8`, `mypy` on the new and changed modules | clean |
| `tsc -b`, `npm run lint`, `npm run build` | clean; the chunk-size warning of Phase 0 |
| `check:render`, `check:history`, `check:note-names`, `check:geometry`, `check:cuts`, `check:notes` | 60, all, 15, all, all, all passed |
| `check:compose` (new), signed in | 24 checks passed, no console error, nothing left behind (projects, songs, playlists) |
| `check:projects`, `check:library`, `check:transpose`, `check:lyrics`, `check:paste`, `check:passage`, `--only clefs`, signed in, after the fix of the saved figure length | 26, 27, 18, 39, 29, 38 and 3 checks passed, no console error, nothing left behind |
| `check:flow`, signed in, with the live transcription | 82 checks passed, no console error |
| `bench:sheet`, median of a hand move (another project loaded the machine, load average 3.4) | Elefants 222 to 229 ms, Superestrella tutorial 275 to 280 ms, The Other Side 525 to 616 ms (Phase 9: 215, 266, 494). Nothing this phase changed is on that path |
| `time:flow`, the first piano sheet | 0.8 s, 1.0 s, 0.5 s (Phase 9: 0.6, 1.0, 0.5); notes saved 27.9 s, 51.5 s, 21.4 s |
| `make db-check` on the real `.database/` | 42 projects, no problem, after every script |
| `scripts/docs/check-links.py` | passes |

`check:projects` expected **From other projects** to be disabled; it now expects it offered. Two
runs (`--only clefs`, and the library piece of `time:flow`) stopped on `ERR_NETWORK_CHANGED`: the
machine's network changed under the browser; run again, both passed. `check:paste` once timed out
waiting for a sheet while the full backend run held the CPU; alone it passed.

The browser scripts signed in with `AITU_MASTER_PASSWORD` of `.env` and worked on copies only. The
playlist part of `check:compose` saves a copy to My library under a song of its own ("check-compose
song") and deletes the song, its version and the playlist at the end.

# 8. The 13 checks of the 09 guidelines

Run on the page of From other projects (the picker, a source, the list, the save dialog), the parts
panel and **Start a new part here**, Playlists, one playlist, **Make a playlist** and **Add to a
playlist**, with the screenshots of [`screenshots/phase-10/`](screenshots/phase-10/), taken by
`check-compose.mjs` on its copies.

| # | Check | Result |
|---|---|---|
| 1 | One sentence | From other projects: make a project of passages of other projects. The parts: see and change the parts of a project. Playlists: list songs of the library to play one after the other |
| 2 | Every sentence a label, control or fact | "This project has no piano sheet yet: it can only be added whole." (only when it applies: it changes what can be added); "No project has notes yet.", "No playlists yet.", "No songs yet.", "Added to “…”." |
| 3 | Words above the first content | "From other projects", then the filter; a playlist: its title |
| 4 | Very wide | The picker is held to 760 px, so its layer column stays beside the titles (the first picture showed it at the far edge); the sheet takes the rest of the width beside the list |
| 5 | Narrow (390 px, shots 11 and 12) | 0 px of sideways scroll. The header's two save buttons pushed past the edge (30 px); a page header's actions now wrap, on every page |
| 6 | Longest, shortest, none | A long title is cut with "…" (full on hover) in the list, the picker and the parts; no passage: no list, the save buttons disabled; one part: no panel; a part with no subheader: "Part 2"; no stretch: "Whole" |
| 7 | Buttons say what happens | "Add this stretch", "Add the whole sheet", "Choose another project", "Save as song", "Save as integrated playlist", "Join with “Coda”", "Start a new part here", "Make a playlist of 2", "Add to a playlist", "Use “hard”", "The whole song", "Remove from the playlist", "Delete playlist" |
| 8 | Helper lines | None. **Sequential** and **Subheader** explain themselves in their tooltips ("Plays on from the passage before", "Starts a new part, with a title"), as do the playlist kinds |
| 9 | Loading, empty, partial, error | Skeletons hold the lists; a refused save, join or split is one line in the backend's words, the list and the dialog kept |
| 10 | Tab through it | Every control is a button, a field, a select, a checkbox or a menu; dragging has Move up / Move down beside it |
| 11 | Internal names | None: no "part id", "compose", "draft", "item" on screen. "Part" and "Subheader" are the user's words (the app context) |
| 12 | First-time user | "From other projects", "Passages", "Sequential", "Subheader", "Playlists", "Whole" |
| 13 | Anti-patterns | No lecture; one empty state per page; the save buttons sit at the right of the title, the add buttons beside what they add to |

| Shot | Page |
|---|---|
| 01 | The picker of From other projects |
| 02 | A stretch marked on a read-only sheet: **Add this stretch** |
| 03 | Three passages, Sequential and a Subheader titled "Coda" |
| 04 | **Save as integrated playlist** |
| 05 | The integrated playlist's first part, its parts on the left |
| 06 | **Start a new part here** in the range toolbox |
| 07 | After the split |
| 08 | **Make a playlist** from Songs |
| 09 | One playlist |
| 10 | Playlists |
| 11, 12 | 390 px: the picker; the parts |
| 13 | Dark: the parts |

# 9. Decisions for the user

**The parts on the Sheet step** (section 3): one part at a time with the panel, or every part drawn
one after the other on the one page (a larger change; each part's tools would have to be told apart).
Recommended: keep one at a time, and draw the parts together in Play mode's continuous page (Phase
11).

**Answered 2026-10-15:** the user found the phase good as built, so the Sheet step keeps one part at a
time; Phase 11 draws the parts one after the other in Play mode's continuous page.

# 10. Open points

- **Joins and splits are not on the sheet's undo.** Each is taken back by the other.
- **The list of From other projects is of one browser.**
- **The Public Library is not in the picker** until Phase 13.
- **A songs playlist's stretch is chosen only when it is added** (from a stretch of the version's
  sheet); a row offers **The whole song**, not a new stretch.
- **The subheader of a part from a split is empty** ("Part 2" on the panel) until renamed.

# 11. Learnings for later phases

- **A list chosen before something exists can live in the browser** when it is references only: no
  hidden record, no migration, nothing to clean up when the reader gives up.
- **Wait for the answer of a write, not for its first visible effect**: a split adds its part row
  before it pastes into it, so a check that polled the parts read the notes too early.
- **A shared control that two checks would find by the same name** (a toggle and a field both called
  "Subheader") is a sign the field's label is unclear: the field became **Title**.
- **A browser check that dies on `ERR_NETWORK_CHANGED` met the machine, not the app**: run it again.
  Do not run the browser checks while the backend tests run on the CPU: the timeouts are tight.
- **Lay out a page header's actions to wrap**: two long buttons pushed a page sideways at 390 px.
- **What a page measures once must be read back, not measured again**: a value derived from the
  notes (the pile of gaps) drifts as soon as an edit changes the notes; keep the decision that was
  saved.
