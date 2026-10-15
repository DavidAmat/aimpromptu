> Context: [context/backend/editing.md](../../../context/backend/editing.md)

# Copy and paste, Recording in Sheet, and the parts of a project

Two writes change a transcribed part other than a note edit: a **paste** of a stretch of any part
the user may read (implementation 02, Phase 8), and the **promotion** of a re-recorded passage
(Phase 9). Both go through one function, `paste.paste`, so they share the length rule, the marks,
the audio timeline and the undo. **From other projects** and the joins and splits of the parts of a
project (Phase 10) are pastes too, and a split uses the one write that takes a stretch out,
`paste.cut`.

Modules: `aitu-backend/src/aitu_backend/editing/`. Routes: `POST /time/{uuid}/paste`,
`POST /time/{uuid}/versions/{n}/restore`, `/passages`, `POST /projects/compose` and
`/projects/{id}/parts` ([`endpoints.md`](endpoints.md)).

| Module | Role |
|---|---|
| `paste.py` | `read_passage` (the notes, marks and audio of a stretch), `paste` (one write into a part), `cut` (a stretch taken out, Phase 10), `audio_with` and `apply_audio` (the part's timeline with pieces put in), `part_length_ms`, `whole_ms` |
| `passages.py` | Recording in Sheet: the passage and its takes, the condensed steps, the promotion |
| `parts.py` | From other projects (`assemble`) and the parts of a project (`facts`, `rename`, `join`, `split`), Phase 10 |
| `compose.py` | `insert_events`: every note from a column on moves later by a passage's length; `quantise_up`, `frame_at_or_after` |
| `marks.py` | The one list of the marks of `sheet.json`: `shift`, `cut_out`, `extract`, `put_in`, `count`, `dropped` |
| `history.py` | `snapshot_current`, `restore`: the undo and the redo |
| `audio_splice.py` | `stretch_by_rate`: a take played faster or slower with its pitch kept (`atempo`) |
| `../audio/timeline.py` | `passage_pieces`, `insert_with_origins`, `remove`, `silence`: the timeline changed in the middle |

---

## 1. The length rule

**A passage occupies a whole number of columns.** `paste` rounds its length up to the next frame of
the target's sheet (or takes the `columns` it is given), so every column after the insertion point
moves by the same integer and `round(onset_ms / frameMs)` (D-02) lands on the column a mark was
shifted to. The cost is at most one frame of silence at the join.

**Everything after moves in the same write.** The notes by `compose.insert_events` (placement
`insert`; membership is by column, so a note a few milliseconds before the moment that rounds into
its column moves with it; a note sounding across the moment is cut there); every mark by
`marks.shift(straddle="tear")`. `compose.py` and `paste.py` are the only modules that change a
part's length (rule 2 as changed by Q-3, the note under rule 2 in `wall-clock-rewrite.md`).

---

## 2. Copy and paste

**The clipboard is a reference.** `{"type": "aimpromptu/passage", "part", "project", "title",
"fromMs", "toMs"}`, kept by the page (`state/passageClipboard.ts`). The backend reads the passage
when it is pasted (`read_passage`), after checking the user may read the source part (a `404`
otherwise). The stretch is snapped to whole columns of the source's sheet.

**What a paste writes**, all of it worked out before anything is written:

| | How |
|---|---|
| Notes | The source's notes whose onset column is inside the stretch (taken off the page or not), cut where the stretch ends, moved to the insertion point, with new ids; then `compose.insert_events` |
| Marks | `marks.shift(..., straddle="tear")` on the target's sheet (the page's sheet when it sent one): a range across the insertion point ends there and goes on after the passage (a lyrics piece and a trill only end); then the source's marks of the stretch (`marks.extract`, clipped) are put in (`marks.put_in`), rescaled when the two sheets have another `frameMs`. The key, each hand's clef and the speed (`anchorMs`, when they differ by more than 2 %) in force where the copy starts are written at the insertion point, and what the target had there is written again where the passage ends when music follows (a key at column 0 is the sheet's key; no clef change can be stored at column 0) |
| Audio | `audio_timeline.passage_pieces` gives the ranges of stored files the stretch plays; `audio_with` puts them into the target's timeline at the insertion point (a file the moment falls inside is split in two, every cut after it moves), with a stored file of silence where the passage plays longer than its audio or the moment is past the end of the audio. The files are named `"<title> m:ss–m:ss"` (kind `passage`), or as the caller says (`audio_name`, `audio_kind`: a take is `"Take 2"`, `recording`). A part left with one whole file takes that file's kind when it is an upload's word, `segment` otherwise |
| Revisions | The audio revision goes up; the notes are written with that revision, so the Notes step stays current; the hands follow when every note has one; the sheet is saved for the new hands revision when it was current |

**Over a marked stretch** (`replaceToMs`): its notes are taken out (the notes after move earlier),
its marks are cut out (`marks.cut_out`; a key or clef change inside moves to its start), and its
audio becomes cuts (`audio_timeline.remove`), which the Audio step can restore.

**Two options of a promotion.** `keep_audio` leaves the part's audio as it is (only notes and marks
change); it is refused unless the passage is as long as the stretch it replaces. `columns` is the
passage's length in columns instead of its own rounded up (a take fitted into a window).

**A target with no music** (From scratch) takes the source's sheet settings with none of its marks
outside the passage. A target with audio and no notes is refused (`409`).

---

## 3. Recording in Sheet (`passages.py`, Phase 9)

### 3.1 The passage and its takes

`open_passage(part, fromMs, toMs)` snaps the stretch to whole columns of the part's sheet (a moment,
`toMs == fromMs`, is a new passage there; past the end of the piece is its end) and makes a project
of `kind = 'passage'` in the user's Personal Vault, titled `"<song> m:ss–m:ss"`. Its one part is the
**Current**: `paste.paste` of the stretch into the empty part, so it holds the stretch's notes,
marks, key and clefs and plays ranges of the song's stored files. Its `origin` is the passage's
state (`PassageState`):

| Field | Meaning |
|---|---|
| `passageOf`, `fromMs`, `toMs` | The part and the stretch |
| `anchorMs`, `anchorFigure` | What the song's figure lasts where the stretch starts (`paste.anchor_at`); `anchorMs` is `null` on a song with no sheet |
| `takes`, `take` | The take projects, in order, and the one on show |
| `speed` | How many times as fast the take goes into the song, ×0.25 to ×4 |
| `windowMs` | Where the window starts over the take, in ms of the take as played |

**A take** is one more hidden project of one part (`origin.takeOf` names the passage), titled
`"Take N"`: `add_take` raises the upload so its loudest sample is at -1 dB (`formats.louder`, one
gain for the whole take, at most +40 dB, never lowered; the browser's automatic gain is off), stores
it as FLAC at its own rate and channels (`store.save_original`) and normalizes it (`ingest.finalize`).
A take played on a MIDI piano also carries its keys (`notes`: `MidiNote` `{midiNote, start, end,
velocity}`, seconds from the start of the recording), kept as `parts/<takeId>/midi.json`; with no
recording its audio is silence as long as the keys and a second more. Its state: `recorded` (audio only), `reading` (its job runs, key
`take:<id>`), `ready` (notes of the current cuts, and a hand for every note).

**The condensed steps** (`read_take`, the job of **Write the proposal**, on the GPU queue): the
stretch of the take to keep becomes its cuts (`store.set_cuts`, the Audio step's rule); then
`pipeline.transcribe_audio` (its live notes go to the job's stream), or, for a take played on a MIDI
piano, the same call with `_PlayedNotes` as the engine (`name = "midi"`): the keys whose onset is in
the stretch, in its time, so the notes get a transcription's header and history without the model
(`filters_for("midi")` turns off the filters tuned for ByteDance, as for MuScriptor); then the hand split
(`inferred_split`, every note given a hand, unplaced ones by the quick rule) written by
`save_edit(hands_changed=True)`; then its first sheet (`_first_sheet`): the song's settings where the
stretch starts (key, figure, spacing, `paste._first_sheet`), none of its marks, `anchorMs` = the
passage's times the speed, `ottavas` unset (the page proposes brackets), `handsRevision` current.
On a song with no sheet no sheet is written: the page's defaults of a first write apply.

Every hidden project goes with what it belongs to: `bundle.delete_project` deletes the passages of
a project's parts and the takes of a passage (`bundle.dependents`), and **Save to library** deletes
the passages of the project saved (`flow._drop_temporary`). `bundle.list_parts` and `GET /projects`
leave them out.

### 3.2 The promotion

`_plan` reads the take's passage (`paste.read_passage(take, start, stop, sheet=)`, with the
Proposal's sheet as the page holds it):

| Mode | The take's stretch | `columns` | `replace_to` |
|---|---|---|---|
| `window` | `[windowMs, windowMs + length × speed)` | the passage's own | the passage's end |
| `whole` | the whole kept take | its own, rounded up | the passage's end (none for a moment) |

`_song_passage` reads it in the song's time: every time divided by `speed`, a note of a window that
starts after the window's length left out and its end cut there, `frameMs` divided by `speed` (so
`paste` rescales the marks' columns by `1/speed`), and the sheet's figure named with the song's
(`_in_song_time`: `anchorMs` = the passage's `anchorMs` × the ratio of the two figures' lengths in
negras, `FIGURE_NEGRAS`; the speed changes the same). A figure renamed on the Proposal (Transpose →
Figures) therefore reaches the song as a speed change at the passage, and the song's own after it.

**The audio**: `audio = 'original'` (a window only) passes `keep_audio`. With the recording at ×1
the take's stored ranges go in as they are (no byte copied). At another speed `_rendered` writes
them end to end at their own rate and channels (`sources.write_ranges`), plays them `speed` times as
fast with the pitch kept (`audio_splice.stretch_by_rate(..., keep_format=True)`), and stores the
result as a new WAV, used for exactly the passage's length.

`facts` answers what `promote` would do without writing: the notes out and in, the marks dropped by
kind (`marks.dropped`: a mark on a column of the passage, a range wholly inside it; key, clef and
speed changes are transitions and not counted), the length change and the new length. `promote`
calls `paste.paste(target, ..., at_ms=fromMs, replace_to_ms=toMs, keep_audio, columns,
audio_name=<take's name>, audio_kind="recording")` and deletes the passage with its takes; the
target's snapshot (`beforeVersion`) is the undo.

---

## 4. From other projects, and the parts (`parts.py`, Phase 10)

**`assemble(owner_id, title, kind, passages)`** makes a project of the Personal Vault from passages
of other parts (plan section 10.4). Each `Chosen` is a part, a stretch of it in ms or `None` for the
whole (`whole_ms`: its notes or its audio, whichever is longer, rounded up to whole columns), and
how it joins the one before: `sequential` (the same part) or `subheader` (a new part). It makes the
project (`kind` `song` or `integratedPlaylist`, one empty part, `frameMs` 40), adds a part per
further group (`bundle.add_part`), names each part by its subheader or its first source's title
(none when there is one part), writes `origin: {"composedFrom": [{part, fromMs, toMs, join}]}`, then
for each passage `paste.paste(part, read_passage(...), at_ms=whole_ms(part))`: the paste of section 2
at the end of the part. So a passage brings its notes, its marks, the key, clefs and speed it had
where it starts, and ranges of the stored audio; the first one into an empty part takes its
source's sheet settings, and since Phase 10 the speed in force where the copy starts (an empty part
used to take the source's base speed). The history the pastes kept is deleted at the end (a new
project has no earlier state, as a duplicate). A failure deletes the project.

| Function | What it writes |
|---|---|
| `rename(project, part, subheader)` | `parts[].subheader` (whitespace folded, at most 300 characters; empty is none) |
| `bundle.reorder_parts(project, order)` | The order of `parts` in `project.json` and `parts.position` (two passes: `(project_id, position)` is unique) |
| `join(project, part)` | The part pasted at the end of the one before it, then removed (`bundle.remove_part`: its folders, history, row, open passages, unused audio). When the lower part carries the project's id, the upper one is pasted at its start instead, because **the project's id is always one of its parts** (the step routes take it). The kept part takes the upper one's subheader |
| `split(project, part, at_ms, subheader, sheet)` | `at_ms` snapped to a column of the part's sheet, inside it; a new part after it (`bundle.add_part`); `paste.paste(new, read_passage(part, at, whole, sheet=sheet), at_ms=0)`, then `paste.cut(part, at, whole, sheet=sheet)`. A failure removes the new part |

**`paste.cut(part, from_ms, to_ms, sheet=)`** takes a stretch out: the notes by onset column (those
after move earlier, one sounding into it is cut where it starts), the marks (`marks.cut_out`; a key,
clef or speed change inside moves to its start when music follows, `_cut_transitions`), the audio
(`audio_timeline.remove`: cuts the Audio step can restore). The part is kept as a snapshot first,
so `POST /time/{uuid}/versions/{n}/restore` undoes it exactly; the parts routes do not offer that
undo on the page yet.

## 5. Undo and redo

`history.snapshot_current` keeps the target (notes, sheet, timeline, and the part's entry of
`project.json` as `source.json`) before the first write; the answer's `beforeVersion` names it.
`history.restore(part, n)` keeps the current state as the next snapshot and puts `v<n>` back
(`copyfile`, so the notes get a new time and the hand split cache cannot serve the old split), then
forgets the derived audio. Its answer's `keptVersion` is the redo. A failure in the middle of a
paste restores the snapshot. `GET /audio/{uuid}/file` tries once more when a restore forgot the
derived files it was writing from.

---

## 6. Rules to keep

- `compose.py` and `paste.py` are the **only** modules that change a part's length; a promotion,
  a passage of From other projects, a join and a split go through `paste.paste` and `paste.cut`.
  Anything else that needs to is a new decision.
- The id of a project is always one of its parts: `bundle.remove_part` refuses it, and a join keeps
  it.
- A new kind of mark in `sheet.json` is added to `editing/marks.py`, or no length change moves it.
- The quantise-up rule is load-bearing. Remove it and mark shifting stops being exact.
- A take is played into a song at its own rate and channels (`keep_format`), never at the engine's
  16 kHz mono.
- Work everything out before the snapshot, then write.

---

## 7. Tests

- `tests/test_parts.py` — 7 tests (Phase 10): a project from other projects (one part per subheader,
  the notes, key and fingering of each passage where it lands, the audio by pitch, nothing copied,
  the sources unchanged), one part with no subheader, a failing passage leaves nothing, rename,
  reorder, join (the project's part kept), split, the library refuses, the cut and its undo to the
  byte
- `tests/test_passages.py` — 12 tests (Phase 9): the Current is a copy of the stretch, hidden from
  every list; a take read in the passage's key and figure, with every hand; the window with the
  original audio (the timeline to the byte), the window with the recording at ×2 (the take's pitch
  at the passage, the song's after it, the same length), the whole take (+1 s, the notes and marks
  after moved, the audio as long as the notes); a renamed figure kept as a speed change; a new
  passage on a blank sheet; undo to the byte; deleting the song and discarding the passage; a
  version of the library cannot be re-recorded; a take of another passage is not found
- `tests/test_paste.py` — 16 tests (Phase 8): the timeline put into and cut, a paste's notes, marks,
  key at both edges and audio, every join, undo and redo to the byte, a paste over a marked stretch,
  the page's unsaved sheet, From scratch, Save to library and export of a pasted project
- `tests/test_compose.py` — 7 tests: `insert_events` (append moves nothing, an insert moves every
  note from the column on, a sounding note is cut, a note that rounds into the column moves) and
  `atempo_chain`
- `tests/test_rights.py` — the source of a paste is read and its target written, row by row

---

## 8. Removed in Phase 9

The staged session of Epics 11 and 13 (`editing/session.py`, `preview.py`, `splice.py`,
`storage/staging.py`, `schemas/editing.py`, the routes `/audio/{uuid}/edits` and `POST
/audio/compose`, `compose.create_empty_piece`, `append_anchor`, `passage_bounds`, `shift_marks`,
`audio_splice.splice_wav` and `insert_wav`) and its tests (`test_range_edit.py`,
`test_compose_live.py`). Its two panels were the only callers; the page of a passage replaced them.
What it did differently: a re-record was spliced into `normalized.wav` and the part's audio written
again as one 16 kHz file, and neither it nor a recorded passage could be undone. Git history keeps
it.

---

## 9. Where to look deeper

- [`endpoints.md`](endpoints.md) — the routes
- [`paths-and-data.md`](paths-and-data.md#22-timelinejson-the-audio-timeline) — the timeline and its
  ranges; the hidden projects of a passage
- [`rhythm-and-annotations.md`](rhythm-and-annotations.md) — the marks that are moved
- [`../frontend/components.md`](../frontend/components.md) — the page of a passage, the Paste of the
  sheet page, the page of From other projects and the parts panel
- [`context/frontend/playlists.md`](../../../context/frontend/playlists.md) — From other projects and
  the playlists, for the reader
