> Context: [context/backend/time-model.md](../../../context/backend/time-model.md) ·
> [context/frontend/annotations.md](../../../context/frontend/annotations.md)

# `rhythm.json` — the reader's own decisions

Everything else about a score is derived. The columns come from the recorded notes, the figures come
from the ladder, the beams come from the figures. This file holds the only things that are **not**
derived, because a person chose them and nothing in the recording implies them.

Model: `aitu-backend/src/aitu_backend/schemas/rhythm.py`, class `SavedRhythm`.
Stored at `data/audio/<uuid>/matrices/rhythm.json`.
Routes: `GET`, `PUT` and `DELETE /time/{uuid}/rhythm`.

**One per piece.** A second reading replaces the first, because a rhythm is a decision rather than a
version, and the thing a reader wants back is the last one they were happy with.

Losing this file does not change the music. It costs a person their reading of the piece, which they
then have to do again from the plot — and that is the whole reason it is stored.

---

## 1. One thing that is deliberately *not* in here

**Which hand plays a note.** That is a fact about the playing rather than about this page: it
survives a change of column length, it decides the printed length of its neighbours, and everything
downstream is derived from it. So it is written onto the note event and the matrix is built with it
(`time_pipeline.pin_hands`). See [`events-to-sheet.md`](events-to-sheet.md#the-readers-correction-wins).

Octave brackets **are** in here, as of 2026-09-13 — see `ottavas` below. Until then they were the
one thing the page sent and the backend threw away: the model had no field for them, Pydantic
ignores extras by default, and so every bracket was dropped on save without an error and a reload
showed a page with none. Nothing failed and nothing said so, which is why it lasted a month.
`tests/test_saved_rhythm.py` now pins the round trip.

---

## 2. The frame length is part of the reading

`frameMs`, stored beside everything else.

A rhythm named at 40 ms is a set of column numbers, and the same column numbers mean different
moments at 20 ms. Storing the frame length beside them is what lets a reload know whether the
numbers it is holding still refer to what they referred to.

---

## 3. Fields

### Top level

| Field | JSON | Type | Meaning |
|---|---|---|---|
| `schema_version` | `schemaVersion` | `string` | `"1.0"` |
| `hand` | `hand` | `string` | Which hand's gaps the plot was read from. Default `right`. |
| `frame_ms` | `frameMs` | `float > 0` | The column length the numbers below were written at. |
| `key_signature` | `keySignature` | `string?` | The piece's key, as a major key: `C`, `Bb`, `F#`. |
| `anchor_figure` | `anchorFigure` | `FigureName` | The pile the reader named. Default `negra`. |
| `anchor_ms` | `anchorMs` | `float > 0` | What they said it lasts. |
| `annotation_scale` | `annotationScale` | `0.3 < f ≤ 2.0` | How large marks over and under the staff are drawn. |
| `saved_at` | `savedAt` | datetime | |

`hand` is not part of the sheet, but it is what the reader was looking at, and returning them to the
other hand's plot would be a small surprise every time.

`keySignature` is part of the reading rather than of the recording: the recorded notes say which
keys were pressed and nothing about whether a black key is an F sharp or a G flat, so nobody but the
reader can answer it. Absent means C, which is what readings saved before the field existed were
drawn in.

`annotationScale` is per piece rather than per app, because one piece can be dense enough that
fingering crowds it and another airy enough that the same numbers are hard to read.

### `keyChanges: KeyChange[]`

| Field | JSON | Type |
|---|---|---|
| `from_column` | `fromColumn` | `int ≥ 0` |
| `key_signature` | `keySignature` | `string` |

A **transition, not a range**: at any column exactly one signature is sounding, so two edits cannot
disagree about what a reader is looking at. Giving a passage its own key writes two of these, one
where it starts and one where the piece returns to what it was.

Empty for a piece written in one key from beginning to end, which is the common case.

### `speedChanges: SpeedChange[]`

| Field | JSON | Type |
|---|---|---|
| `start_frame` | `startFrame` | `int ≥ 0` |
| `anchor_ms` | `anchorMs` | `float > 0` |

Where the piece changes speed, and what a gap is worth from there on. Keyed by column, which is
absolute wall clock, so a boundary never moves when anything else about the reading changes (D-19).

### `overrides: FigureOverride[]`, `beamBreaks: BeamBreak[]`

Defined in `schemas/time_matrix.py` and described in
[`time-matrix.md`](time-matrix.md#26-figureoverride). A renamed note (D-17) and a note the reader
asked to start a new beam (D-34). Both change one glyph or one grouping and nothing else.

### `hiddenNotes: HiddenNote[]`

| Field | JSON | Type |
|---|---|---|
| `start_frame` | `startFrame` | `int ≥ 0` |
| `row` | `row` | `0…87` |

A note the reader took off the page — usually one the transcriber invented out of a pedal blur.

**Addressed without a hand.** The two hands can never strike the same key in the same frame — a
matrix that does is rejected — so `(startFrame, row)` already names one note, and leaving the hand
out is what lets the address survive the note being moved to the other staff.

The note is still in the matrix after the reader stops drawing it. The hidden set is held beside the
matrix and folded in on the way to the drawing, so undoing it restores the note exactly. `save()`
also writes hidden notes through to the recording, so the roll, the falling view and the sheet agree
about what is there.

### `fingers: Fingering[]`

| Field | JSON | Type |
|---|---|---|
| `hand` | `hand` | `"right" \| "left"` |
| `start_frame` | `startFrame` | `int ≥ 0` |
| `row` | `row` | `0…87` |
| `finger` | `finger` | `1…5` |

Keyed by the staff the note is **drawn** on, so a fingering moves with a note the reader sent across.
Several on one chord print stacked in ascending order, which is how fingering is written.

### `trills: Trill[]`

| Field | JSON | Type |
|---|---|---|
| `hand` | `hand` | `"right" \| "left"` |
| `start_frame` | `startFrame` | `int ≥ 0` |
| `end_frame` | `endFrame` | `int >` start — one past the run's last onset |
| `row` | `row` | `0…87` |

A stretch printed as one held note with `tr` over it. The alternations are all still in
`events.json`, playback still sounds every one of them (D-29), and removing the mark prints them
again — what the mark changes is only which noteheads are drawn.

`row` is the note that **stays**: the lower of the two, because `tr` means "alternate with the note
above". It is stored rather than re-derived, so accepting a suggestion and then editing the notes
underneath cannot silently move the mark to a different pitch.

### `graceNotes: GraceNote[]`

| Field | JSON | Type |
|---|---|---|
| `hand` | `hand` | `"right" \| "left"` |
| `start_frame` | `startFrame` | `int ≥ 0` |
| `target_row` | `targetRow` | `0…87` — the note it leans on |
| `row` | `row` | `0…87` — the grace note's own pitch |
| `kind` | `kind` | `"acciaccatura"` \| `"appoggiatura"` |

A mark and **not an event**. It is not in `events.json`, it takes no column, nothing plays it, and
no figure anywhere is measured differently because of it — which is exactly why it can be added and
removed freely.

`row` and `targetRow` are separate because the mark hangs off a note it is not: the target says
where to stand, `row` says what to draw.

An **acciaccatura** is crushed, as fast as possible, and prints with a slash through its stem. An
**appoggiatura** leans, taking its time from the note it precedes, and prints without one.

### `lyrics: Lyric[]`

| Field | JSON | Type |
|---|---|---|
| `from_column` | `fromColumn` | `int ≥ 0` |
| `to_column` | `toColumn` | `int >` from — **exclusive** |
| `text` | `text` | non-empty string |

A line of words written under the staff, across a stretch of columns.

**Hand-independent**: words belong to the piece rather than to a staff, and they are drawn under the
lower staff whichever hand is singing them.

A lyric never widens the layout, because the spacing of the page comes from the notes and never from
an annotation (D-22, D-23). A line over a long rest keeps its start and stays there.

### `ottavas: Ottava[] | null`

| Field | JSON | Type |
|---|---|---|
| `kind` | `kind` | `"8va"`, `"8vb"`, `"15ma"`, `"15mb"` |
| `hand` | `hand` | `"right" \| "left"` |
| `from_column` | `fromColumn` | `int ≥ 0` |
| `to_column` | `toColumn` | `int >` from — **exclusive** |

A stretch written an octave or two from where it sounds. A reading of the page and nothing else: the
pitch is untouched, playback is untouched, and removing the bracket prints the same notes back where
they were. What it changes is how far from the staff the noteheads are drawn, which is the
difference between a passage a player can read and a pile of ledger lines.

Asked for, never inferred. The page used to suggest a bracket wherever a hand ran far outside its
own staff, and that was wrong often enough to be noise, so a page nobody has touched carries none.

Per hand, because the two hands leave their staves independently.

**`null` and `[]` mean different things**, which is why this field is optional where the others are
not. `null` is a reading that was never asked the question — saved before brackets were stored — and
the page may offer its own answer. `[]` is a reader who was asked and said none, and the page must
leave it alone.

`8va` and `15ma` are written above the staff, `8vb` and `15mb` below it. An unknown kind is a `422`.

### `cueRanges: CueRange[]`

| Field | JSON | Type |
|---|---|---|
| `hand` | `hand` | `"right"`, `"left"`, or `"single"` for both staves |
| `from_column` | `fromColumn` | `int ≥ 0` |
| `to_column` | `toColumn` | `int >` from — **exclusive** |

A stretch printed smaller than the rest of the page. **Asked for, never inferred.** A florid run in
one hand set at full size crowds the other hand off the system; set smaller it takes less width and
reads as decoration, which is what it is.

The narrowing is allowed to move the notes **inside** the mark and nothing outside it, which is the
same locality D-21 gives a ladder change.

---

## 4. What clears it

`DELETE /time/{uuid}/rhythm` — what **Remove all** calls. It clears every editorial decision and
forgets the reading saved with the piece, so a reload does not bring it back.

One of those decisions reaches into the recording: hidden notes. So Remove all **puts those notes
back on the recording before dropping the list** — clearing the list alone would leave the notes
gone with nothing on screen remembering them.

Transcribing the piece again also clears it, on purpose: a saved reading is a set of column numbers
over the notes that were there before, and a new transcription is a different set of notes.

---

## 5. Marks and edits

A replacement splice (Epic 11) **drops** marks anchored inside the window it replaces, and
`GET …/confirmation` counts them by kind before the button is pressed. An insertion (Epic 13)
**moves** every mark at or after the insertion point by the same number of columns, in the same
write as the notes.

A range whose start is before an insertion and whose end is after it keeps its start and moves its
end, so it still covers exactly the notes it covered before. Detail in
[`editing-and-compose.md`](editing-and-compose.md).

---

## 6. Where to look deeper

- [`time-matrix.md`](time-matrix.md) — `FigureOverride` and `BeamBreak`, shared with the payload
- [`endpoints.md`](endpoints.md#4-time--the-wall-clock-score) — the three rhythm routes
- [`editing-and-compose.md`](editing-and-compose.md) — what happens to marks across an edit
- [`../frontend/components.md`](../frontend/components.md) — the toolboxes that write all of this
