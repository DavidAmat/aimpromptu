> Context: [context/backend/editing.md](../../../context/backend/editing.md)

# Range editing and composing live

Two features, one session model. **Re-record** replaces a marked stretch of a piece that already
exists; **Compose** builds a piece one passage at a time out of nothing. They share the recorder,
the trim, the transcription job, the peak plot and the passage sheet, and they differ in exactly one
thing: whether the piece is allowed to get longer.

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
`data/audio/<uuid>/staging/<session-uuid>/` holds the take and the decisions about it. **Nothing
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
`editing/history.py` copies the **previous** `events.json` into `history/v<N>/` and advances
`music-version.json`, then `audio_splice.splice_wav` writes the stretched take into the recording at
the same offset.

If the audio splice fails, the window is recorded in `audio-mismatches.json` rather than failing the
edit: the notes were written correctly and only the sound is behind, so saying so is more useful
than rolling back a correct result.

---

## 5. Composing: append and insert

`editing/compose.py`.

### An empty piece

`create_empty_piece` — `POST /audio/compose` — writes an empty `events.json` with
`durationSeconds: 0` and a `frameMs` on the metadata, and **no audio file at all**. The first
accepted passage is what creates a recording.

There is no BPM and no granularity to choose, because neither exists.

One accommodation was needed to make an empty piece drawable: the drawing duration is clamped to at
least one column, because every path below `events_to_time_matrix` rejects a zero duration. One
empty column is enough for a pair of staves, and a column is a property of the view rather than of
the music, so `events.json` still says zero.

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

`audio_splice.insert_wav` is the twin of `splice_wav`: it opens the recording at the moment and
writes the stretched take into the gap, padding silence up to an append and pushing the tail later
on an insert, so the audio moves by exactly what the notes moved by. A piece with no recording yet
gets one here.

---

## 6. Octave brackets move too

`shift_marks` moves `ottavas` with everything else, and a bracket straddling the moment widens
rather than tears, like any other range.

One case is deliberate: a rhythm whose `ottavas` is `null` stays `null`. An insertion moves columns;
it does not answer a question the reader was never put. See
[`rhythm-and-annotations.md`](rhythm-and-annotations.md#ottavas-ottava--null).

This is new as of 2026-09-13. Before it, brackets were not in `SavedRhythm` at all — the page sent
them and Pydantic dropped them — so an insertion had nothing to move and a reload had nothing to
show.

---

## 7. Rules to keep

- `editing/compose.py` is the **only** module allowed to change a piece's length. If something else
  needs to, that is a new decision, not a reuse of this one.
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

---

## 9. Where to look deeper

- [`endpoints.md`](endpoints.md#5-audiouuidedits--staged-editing-and-composing) — the routes
- [`paths-and-data.md`](paths-and-data.md#4-dataaudiouuidstagingsession--disposable-sessions) — the session folder
- [`rhythm-and-annotations.md`](rhythm-and-annotations.md) — the marks that are dropped or moved
- [`../frontend/components.md`](../frontend/components.md) — `RangeRerecordPanel` and `ComposePassagePanel`
