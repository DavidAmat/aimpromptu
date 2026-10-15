> Context: [context/backend/editing.md](../../../context/backend/editing.md)

# Range editing, composing live, and copy and paste

Two features, one session model. **Re-record** replaces a marked stretch of a piece that already
exists; **Compose** builds a piece one passage at a time out of nothing. They share the recorder,
the trim, the transcription job, the peak plot and the passage sheet, and they differ in exactly one
thing: whether the piece is allowed to get longer. **Copy and paste** (implementation 02, Phase 8,
section 9 below) is a third way in: a stretch of any part the user may read, put into a part in one
write, with the length rule of Compose.

Modules: `aitu-backend/src/aitu_backend/editing/`. Routes under `/audio/{uuid}/edits` — see
[`endpoints.md`](endpoints.md#5-audiouuidedits--staged-editing-and-composing).

---

## 1. The rule that shapes all of it

**A re-recorded passage is written back into exactly the window it replaces.**

You mark three seconds of the sheet, you may play the passage as slowly as you like — six seconds,
twelve seconds — and the take is scaled back into those same three seconds on accept.

The column count therefore never changes, and that single property buys everything else: the
recording still lines up with the page, the playhead still lands where it did, and every passage
boundary, key change, override, beam break and fingering **after** the edited window keeps working
without renumbering. It is the same property D-21 gives a ladder change — correcting the end of a
piece must never make a reader re-read the beginning.

The underlying operation is a plain splice of a span of columns and it does not care about length:
fewer columns and more columns are both possible. **Range editing does not offer them, deliberately.**

Where a length change is the point — appending a new passage to a piece being composed — it belongs
to `compose.py`, which is allowed to move everything after the insertion point because there is
nothing there yet, or because moving it is precisely what was asked for.

---

## 2. The session

`editing/session.py` and `storage/staging.py`. A disposable folder under
`<projectId>/staging/<session-uuid>/` in the project bundle (under `.database/`) holds the take and the decisions about it. **Nothing
outside that folder changes until accept**, and cancel deletes the folder and that is the whole of
it.

`SessionRecord.placement` is what decides which operation accept performs:

| Placement | Epic | The piece's length |
|---|---|---|
| `replace` | 11 | Never changes. The window is given at the start and frozen. |
| `append` | 13 | Grows by the passage. |
| `insert` | 13 | Grows by the passage; everything from the moment on moves later. |

For `replace` the window is known from the beginning. For `append` and `insert` the session is given
a **moment** instead, and its window is the passage itself — which is not known until the take has
been played and transcribed, and is recomputed whenever the take or the speed changes
(`_refresh_passage`).

### The window is both columns and seconds

`EditWindow` stores `startFrame`/`endFrame` **and** `startSeconds`/`endSeconds`, with the
`frameMs` they were computed at. Columns are what the reader clicked; seconds are what the splice
uses. Whichever pair arrives, the other is computed once and then **frozen** — recomputing it later
at a different frame length would move the window under the reader.

---

## 3. The flow

```
POST …/edits              open the session
POST …/edits/{s}/take     store the untrimmed recording
POST …/edits/{s}/transcribe   run the model on the take AS PLAYED
POST …/edits/{s}/preview  scale it into the window and draw that stretch alone
GET  …/edits/{s}/confirmation   what accepting would change
POST …/edits/{s}/accept   splice, snapshot, advance the version
```

Each step is its own route, so a reader can stop at any of them and nothing is committed.

**Transcription runs on the take as it was played, never on stretched audio.** A time-stretched
recording is a different sound: the model would be reading an artefact of the stretch rather than
the playing. So the take is transcribed at its own speed and the resulting *times* are scaled
afterwards, which is arithmetic and cannot introduce anything.

### Playing along

`GET …/edits/{s}/window` serves the original window, optionally slowed with pitch preserved
(`audio_splice.stretch_by_rate`, an ffmpeg `atempo` chain). `useClickTrack` on the frontend adds a
metronome at `clickIntervalMs` — clicks every X milliseconds, which is allowed as a **sound in the
player's ears**; nothing derived from it is stored, and there is still no BPM anywhere (D-01).

---

## 4. The replacement splice

`editing/splice.py`.

### Membership is by onset

```python
start_seconds <= event.start < end_seconds
```

A note that started **earlier** and is still sounding across the boundary is left alone. It was
played against the music before the window, and cutting it would change a passage the reader did not
mark.

### Scaling

`factor_for_slowdown` gives the map from take time to window time:

- Original, 2× or 4× slower use the chosen ratio directly (`1/1`, `1/2`, `1/4`).
- **Fit to the window** measures the factor from the take: `window_seconds / take_seconds`. A take
  with no sounding notes cannot be fitted and raises.

`scale_take` then offsets and compresses every event into the window, cuts anything still sounding
at the end, and **drops notes shorter than one frame after scaling** (D-05).

### Marks inside the window

`count_marks_in_window` and `drop_marks_in_window`. A figure override, beam break, hidden note or
fingering anchored **inside** the replaced window is dropped: the note it was about is not there any
more. `GET …/confirmation` reports the counts by kind **before** the button is pressed, because a
fingering that has silently gone looks exactly like one that was never there.

Marks outside the window are untouched, and that is the whole point of the length rule.

### Accept

`splice_events` returns the new event list, what was removed and what arrived.
`editing/history.py` copies the **previous** `notes.pmn`, `sheet.json` and `timeline.json` into
`.database/history/<projectId>/parts/<partId>/v<N>/` and advances `music-version.json`, then
`audio_splice.splice_wav` writes the stretched take into the recording at the same offset.

Since implementation 02, Phase 3 the spliced recording does not overwrite the stored audio. It is a
new file of the audio store (`.database/audio/<sha256>.wav`, `store.replace_original`), and the
part's `timeline.json` points at it. The previous file stays in the store, so a history snapshot
never holds a copy of the audio. The same is true when a composed passage makes the recording longer.

If the audio splice fails, the window is recorded in `audio-mismatches.json` rather than failing the
edit: the notes were written correctly and only the sound is behind, so saying so is more useful
than rolling back a correct result.

---

## 5. Composing: append and insert

`editing/compose.py`.

### An empty piece

`create_empty_piece` — `POST /audio/compose` — writes an empty `notes.pmn` with
`durationMs: 0` and a `frameMs` in `project.json`, and **no audio file at all**. The first
accepted passage is what creates a recording.

There is no BPM and no granularity to choose, because neither exists.

One accommodation was needed to make an empty piece drawable: the drawing duration is clamped to at
least one column, because every path below `events_to_time_matrix` rejects a zero duration. One
empty column is enough for a pair of staves, and a column is a property of the view rather than of
the music, so `notes.pmn` still says zero.

### A passage occupies a whole number of columns

`quantise_up` rounds a passage's length **up** to the next frame before anything is written.

This is load-bearing, not tidiness. It is what makes an insertion exact rather than nearly exact:
every column after the insertion point moves by the same integer, so `round(onset_ms / frameMs)`
(D-02) lands on the column a mark was shifted to, instead of one either side of it depending on
where in the piece it was. The cost is at most one frame of silence at the join — 40 ms.

### Append

`append_anchor` places the passage after the last note, with a silence given in seconds. An empty
piece starts at zero whatever the gap is, because a gap is the distance between two passages and
there is no first passage to be distant from. Notes the reader has taken off the page do not count
as the last note. Appending into trailing silence never shortens a piece.

### Insert

`insert_events` moves everything from the insertion column on later by the passage's length, and
`shift_marks` moves every mark with it, **in the same write**.

**Membership is by column, not by onset in seconds.** This is the one place composing deliberately
departs from the replacement splice, and it was found on a real engine run rather than in theory.
Marks are addressed by column, so a mark in the insertion column moves. A note whose onset is a few
milliseconds *before* the moment but which rounds into that same column would not, under an onset
test — and would be stranded inside the passage the reader had just opened, visibly in the middle of
their new music, with its fingering gone on ahead without it. Deciding both by the column is what
makes "everything from here on moves by the same number of columns" true rather than nearly true.

**A range across the moment widens rather than tears.** A lyric line or a cue-size stretch whose
start is before the insertion and whose end is after it keeps its start and moves its end, so it
still covers exactly the notes it covered before. A mark is counted once however many of its columns
moved.

**A note sounding across the moment is cut there.** It was not played against the passage now
arriving, and letting it ring over the new material would be inventing a sustain nobody played.
Sustain is measurement (D-06); what is printed comes from D-14 and does not change.

### Speed while composing

Original, 2× or 4× slower. There is **no Fit to the window**, and asking for one is a `409`: there
is no window to fit to, so the factor is the whole answer. Play at half speed, choose 2× slower, and
the passage occupies half the time it took to play.

### A take's sustain can outrun the recording

Found on a real engine run: a four-second take of pedalled playing came back with a note "ending" at
9.8 s, and a passage measured from its last release was 9.76 s from four seconds of playing.

With a window that never matters, because the window decides the length. While composing, the take
decides it. So a composed session's trim is bounded by the recording after its first onset
(`_available_take_seconds`) — the same four-second take now gives a 3.92 s passage. A shorter trim
the reader asked for is left alone.

Epic 11's **Fit to the window** measures the same way and has the same exposure, but a window caps
it, so it was left alone rather than changed under a shipped feature.

### The audio grows with the piece

The stretched take is stored as a new file of the audio store and put into the part's **audio
timeline** at the moment (`session._place_audio`, through `paste.audio_with` and
`paste.apply_audio`, the same two functions a paste uses): an **insert** pushes the audio after the
moment later; an **append** is written over whatever trailing audio was there (that stretch becomes
a cut first). A moment past the end of the audio is reached with a stored file of silence. So the
audio moves by exactly what the notes moved by, and a piece with no recording yet gets one here.
The audio revision goes up, and the notes' header follows it, so the Notes step stays current.

*Until implementation 02, Phase 8* the whole part was written again as one 16 kHz mono WAV
(`audio_splice.insert_wav` on `normalized.wav`, then `store.replace_original`). That lost the
quality of every file already there, a pasted passage among them, and on a part with cuts it put
the take at the wrong place (`normalized.wav` still holds the frames cut away). `insert_wav` is
kept, unused by the app, with its tests.

---

## 6. Every mark moves

`compose.shift_marks` moves every mark at or after the moment through `editing/marks.py`, the one
list of the marks of `sheet.json` (`POINTS`: key, clef and speed changes, figures set by hand, beam
breaks and joins, notes taken off the page, fingering, grace notes, staff gaps; `RANGES`: trills,
lyrics, cue size, octave brackets, spacings, even spacings). A range straddling the moment widens
rather than tears. Before Phase 8 the clef changes, the beam joins, the spacings and the staff gaps
were left where they were.

One case is deliberate: a rhythm whose `ottavas` is `null` stays `null`. An insertion moves columns;
it does not answer a question the reader was never put. See
[`rhythm-and-annotations.md`](rhythm-and-annotations.md#ottavas-ottava--null).

This is new as of 2026-09-13. Before it, brackets were not in `SavedRhythm` at all — the page sent
them and Pydantic dropped them — so an insertion had nothing to move and a reload had nothing to
show.

---

## 7. Rules to keep

- `editing/compose.py` and `editing/paste.py` are the **only** modules allowed to change a piece's
  length (rule 2 as changed by implementation 02, Q-3; the note under rule 2 in
  `wall-clock-rewrite.md`). Phase 9 adds the total promotion of a re-recorded passage, through the
  same functions. Anything else that needs to is a new decision.
- A new kind of mark in `sheet.json` is added to `editing/marks.py`, or no length change moves it.
- The quantise-up rule is load-bearing. Remove it and mark shifting stops being exact.
- Membership is by onset for a replace and by column for an insert, and both are deliberate. They
  are not an inconsistency to tidy up.

---

## 8. Tests

- `tests/test_range_edit.py` — the window, the scaling, the dropped marks, the session lifecycle
- `tests/test_compose_live.py` — 34 tests: the empty piece and its drawing, where a passage lands,
  the two splices, the mark shift and its counting, moving a passage without losing the take, the
  insertion-column boundary, the outrunning sustain, the audio growing, and the exit criteria end to
  end through the API
- `tests/test_paste.py` — 17 tests (Phase 8): the timeline put into and cut (a file split around a
  passage, cuts moved and split, silence past the end, the ranges kept by a reorder); a paste's
  notes, marks, key at both edges and audio; the audio at every join on the engine's copy and on
  the joined file; undo and redo to the byte; a paste over a marked stretch; the page's unsaved
  sheet saved by the paste; whole columns; From scratch; Save to library and export of a pasted
  project; a recorded passage after a paste
- `tests/test_rights.py` — the source of a paste is read and its target written, row by row

---

## 9. Copy and paste

`editing/paste.py`, `editing/marks.py`, `audio/timeline.py` (implementation 02, plan section 12).
Routes: `POST /time/{uuid}/paste` and `POST /time/{uuid}/versions/{n}/restore`
([`endpoints.md`](endpoints.md)).

**The clipboard is a reference.** `{"type": "aimpromptu/passage", "part", "project", "title",
"fromMs", "toMs"}`, kept by the page (`state/passageClipboard.ts`). The backend reads the passage
when it is pasted (`read_passage`), after checking the user may read the source part (a `404`
otherwise, as for any project they may not read). The stretch is snapped to whole columns of the
source's sheet.

**What a paste writes**, all of it worked out before anything is written:

| | How |
|---|---|
| Notes | The source's notes whose onset column is inside the stretch (taken off the page or not), cut where the stretch ends, moved to the insertion point, with new ids; then `compose.insert_events` (placement `insert`): every target note from the insertion column on moves by the passage's length, a note sounding across it is cut there |
| Marks | `marks.shift(..., straddle="tear")` on the target's sheet (the page's sheet when it sent one, unsaved edits included): a range across the insertion point ends there and goes on after the passage (a lyrics piece and a trill only end); then the source's marks of the stretch (`marks.extract`, clipped to it) are put in (`marks.put_in`). The key, each hand's clef and the speed (`anchorMs`, when they differ by more than 2 %) in force where the copy starts are written at the insertion point, and what the target had there is written again where the passage ends when music follows (a key at column 0 is the sheet's key; no clef change can be stored at column 0) |
| Audio | `audio_timeline.passage_pieces` gives the ranges of stored files the stretch plays (across cuts and files); `paste.audio_with` puts them into the target's timeline at the insertion point (`insert_with_origins`: a file the moment falls inside is split in two, every cut after it moves, a cut across it is split), with a stored file of silence where the passage plays longer than its audio or the moment is past the end of the audio. The names of the files follow (`"<title> m:ss–m:ss"`, kind `passage`; `Silence`, kind `silence`) |
| Revisions | The audio revision goes up; the notes are written with that revision, so the Notes step stays current; the hands follow when every note has one; the sheet is saved for the new hands revision when it was current (the page that pastes draws the result) |

**Over a marked stretch** (`replaceToMs`): its notes are taken out (the notes after move earlier),
its marks are cut out (`marks.cut_out`; a key or clef change inside moves to its start), and its
audio becomes cuts (`audio_timeline.remove`), which the Audio step can restore. Then the passage
goes in at its start.

**A target with no music** (From scratch, or a project with no notes and no audio) takes the
source's sheet settings (key, figures, spacing) with none of its marks outside the passage, and its
own title lines. A target with audio and no notes is refused (`409`, "Transcribe this project
first").

**Undo and redo.** `history.snapshot_current` keeps the target (notes, sheet, timeline, and the
part's entry of `project.json` as `source.json`) before the first write; the answer's
`beforeVersion` names it. `history.restore(part, n)` keeps the current state as the next snapshot
and puts `v<n>` back (`copyfile`, so the notes get a new time and the hand split cache cannot serve
the old split), then forgets the derived audio. Its answer's `keptVersion` is the redo. A failure
in the middle of a paste restores the snapshot.

**The joined audio** of a part whose entries are ranges is made as for several files
(`audio/sources.py`): each entry's range of its 16 kHz copy, and of its decoded file, joined with the
5 ms fade of a cut at each join. `aitu-backend/scripts/check_joins.py <partId>` compares every entry
of both with its own file, sample by sample away from the fades (`npm run check:paste` runs it).

## 10. Where to look deeper

- [`endpoints.md`](endpoints.md#5-audiouuidedits--staged-editing-and-composing) — the routes
- [`paths-and-data.md`](paths-and-data.md#44-stagingsessionid-disposable-sessions) — the session folder
- [`rhythm-and-annotations.md`](rhythm-and-annotations.md) — the marks that are dropped or moved
- [`../frontend/components.md`](../frontend/components.md) — `RangeRerecordPanel` and `ComposePassagePanel`,
  the Paste of the sheet page
- [`paths-and-data.md`](paths-and-data.md#22-timelinejson-the-audio-timeline) — the timeline and its ranges
