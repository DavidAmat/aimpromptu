# Epic 13 — Composing live · progress

Status: **done** on 2026-09-13. Task 13.1.1, all four subtasks.

Epic 13 is the one place in the product a length change is allowed, so the whole of this report is
about the two halves of that permission. The piece **does** get longer, by exactly the passage —
and everything the insertion pushed later moves by exactly the same number of columns, notes and
editorial marks together, in one write. A fingering is never left pointing at a note that is no
longer under it.

Everything else is Epic 11 with the window taken out, exactly as the epic index said it would be:
the session folder, the recorder, the review dialog, the range cut, the transcription job, the peak
plot and the passage sheet are all the ones Task 11.1.1 built. Nothing in the Re-record path was
changed to make room for this.

## 13.1.1.1 — An empty piece

`POST /audio/compose` with a name and a column length. It writes an empty `events.json`
(`durationSeconds: 0`) and a `frameMs` on the audio metadata, and nothing else — no audio file at
all; the first accepted passage is what creates one. There is no BPM and no granularity to choose,
because neither exists.

On the front, **Compose** is a fourth source on Upload / Input, beside upload, record and audio
library. It is the only entry point with no recording behind it, because it has no music behind it
either, so it takes the page on its own — everything to the right of that page is about a
recording.

One change outside Epic 13 was needed to make an empty piece drawable: `_hands` clamps the drawing
duration to at least one column. An empty piece is `durationSeconds: 0`, and every path below
`events_to_time_matrix` rejects a zero duration. One empty column is enough for a pair of staves,
and a column is a property of the view and not of the music, so this is a view-side clamp and
`events.json` still says zero. `/peaks`, `/score`, `/trills` and `/rhythm` all answer correctly on
an empty piece; the peak plot is simply empty until there is playing to measure.

## 13.1.1.2 — The passage stage

`ComposePassagePanel`, opened from an **Add a passage** card on the Piano Sheet tab. On a piece with
nothing in it the card is already unfolded, because on such a piece it is the only thing to do; on a
piece that already has music it is folded until asked, because the plot is what a reader came for.

Play, cut the recording the way Input does, read that stretch, look at the passage **on its own**
with its own peak plot, play it again as often as you like. Nothing is written to the piece until
**Put it in the piece**, and **Throw this passage away** deletes the session folder and nothing
else.

The preview draws the passage alone rather than in place. While composing there is no window to fit
into and so nothing to compare against: what the reader is deciding is whether this is the passage
they meant to play, and the piece it is going into answers a different question, on the sheet, after
it is accepted.

## 13.1.1.3 — Placing it

`editing/compose.py`. Three placements, one session model — the session's `placement` is what
decides which operation accept performs, and `replace` is Task 11.1.1 untouched.

- **Append** — after the last note, at a silence in seconds. Moves nothing. An empty piece starts at
  zero whatever the gap is, because a gap is the distance between two passages and there is no first
  passage to be distant from. Notes the reader has taken off the page do not count as the last note.
  Appending into trailing silence never shortens a piece.
- **Insert at a moment** — everything from that column on moves later by the passage's length. Notes
  and marks in the same write; the confirmation says how many of each and by how many columns before
  the button is pressed.
- **Replace** — `editing/splice.py`, unchanged.

Three decisions worth recording.

**1. A passage occupies a whole number of columns.** Its length is rounded *up* to the next frame
before anything is written. That is what makes an insertion exact rather than nearly exact: every
column after the insertion point moves by the same integer, so `round(onset_ms / frameMs)` (D-02)
lands on the column a mark was shifted to instead of one either side of it depending on where in the
piece it was. The cost is at most one frame of silence at the join — 40 ms.

**2. Membership is by column, not by onset in seconds.** This is the one place Epic 13 deliberately
departs from the replacement splice, and it was found on a real engine run, not in theory. Marks are
addressed by column, so a mark in the insertion column moves. A note whose onset is a few
milliseconds *before* the moment but which rounds into that same column would not, under an onset
test — and would be left stranded inside the passage the reader had just opened, visibly in the
middle of their new music, with its fingering gone on ahead without it. Deciding both by the column
is what makes "everything from here on moves by the same number of columns" true rather than nearly
true. Verified on the live server: after an insert, every column at or after the insertion column
landed on old + shift, and the fingering moved by the same shift.

**3. A range across the moment widens rather than tears.** A lyric line or a cue-size stretch whose
start is before the insertion and whose end is after it keeps its start and moves its end, so it
still covers exactly the notes it covered before. A mark is counted once however many of its columns
moved.

A note that started before the moment and still sounds across it is **cut there**. It was not played
against the passage now arriving, and letting it ring over the new material would be inventing a
sustain nobody played. Sustain is measurement (D-06); what is printed comes from D-14 and does not
change.

## 13.1.1.4 — Speed

Original / 2× / 4× slower. There is no **Fit to the window** while composing and asking for one is a
409: there is no window to fit to, so the factor is the whole answer. Play at half speed, choose 2×
slower, and the passage occupies half the time it took to play.

**A take's sustain can outrun the recording, and the passage must not.** Also found on a real engine
run, not in theory: a four-second take of pedalled playing came back with a note "ending" at 9.8 s,
and the passage measured from its last release was 9.76 s from four seconds of playing. With a
window that never matters, because the window decides the length; while composing the take decides
it. So a composed session's trim is bounded by the recording after its first onset — the same
four-second take now gives a 3.92 s passage. A shorter trim the reader asked for in the review
dialog is left alone.

## The audio

The recording grows with the piece. `audio_splice.insert_wav` is the twin of `splice_wav`: it opens
the recording at the moment and writes the stretched take into the gap, padding silence up to an
append and pushing the tail later on an insert, so the audio moves by exactly what the notes moved
by. A piece with no recording yet gets one here. Accept snapshots into `history/vN/` and advances
the version, the same as Epic 11, and a failed audio splice marks the stretch as not matching the
sheet rather than failing the edit.

## Tests

`aitu-backend/tests/test_compose_live.py`, 34 passing: the empty piece and its drawing, where a
passage lands, the two splices, the mark shift and its counting, the session lifecycle, moving a
passage without losing the take, the insertion-column boundary, the outrunning sustain, the audio
growing, and the epic's exit criteria end to end through the API.

`762 → 764 passed` across the backend. One failure,
`test_time_score_payload.py::test_the_worked_example_at_00_46_prints_three_equal_corcheas`, is
**pre-existing on a clean checkout of HEAD** and unrelated to this work — confirmed by stashing
everything and running it again. mypy is at its baseline 19 errors, none in these files; flake8 and
black clean; the frontend typechecks, lints and builds.

## Manual trial, done

Not simulated — the real ByteDance engine, through HTTP, on the running app.

1. `POST /audio/compose` → an empty piece, drawn as empty staves.
2. Appended a four-second take at original speed: a 3.92 s passage at 0.00, 27 notes, audio spliced.
3. Appended a five-second take at **half speed** with a one-second silence: 2.36 s at 4.92. The
   piece read as one sheet, 47 notes over 7.24 s, `normalized.wav` 7.28 s, matching `events.json`.
   **This is the epic's exit criterion.**
4. Saved a fingering and a lyric, then inserted a passage in the middle: 32 notes and 2 marks moved
   98 columns, the fingering 150 → 248 and the lyric 140–170 → 238–268, the piece 7.28 → 11.20 s.
5. Repeated at 4× slower and checked every column: every note at or after the insertion column
   landed on old + 30, and the fingering moved by the same 30.

The trial piece is still in the dev data as **"Epic 13 trial"** — open it on Piano Sheet to see it.

## For the next worker

- `editing/compose.py` is the only module allowed to change a piece's length. If something else
  needs to, that is a new decision, not a reuse of this one.
- The quantise-up rule is load-bearing, not tidiness. Remove it and mark shifting stops being exact.
- The take bound (`_available_take_seconds`) exists because engines report sustain past the end of
  the audio. Epic 11's **Fit to the window** measures the same way and has the same exposure, but a
  window caps it, so it was left alone rather than changed under a shipped feature.
- Ottavas are shifted by nothing here for the same reason as in Task 11.1.1: they are not in backend
  `SavedRhythm`. An insert on a piece with brackets will leave them where they were. If ottavas move
  into `SavedRhythm`, add them to `compose.shift_marks`.
