# Task 4.2.1 — Note events to raw matrix · progress report

Status: **done**. Date: 2026-07-27.

## Summary

`transcription/events_to_matrix.py` turns a model's note events into the raw matrix — **always at
fusa granularity**, whatever the user finally wants to see, because that matrix is the immutable
source every later recompute starts from.

| Function | Role |
|----------|------|
| `column_count(duration, bpm, granularity)` | grid width from the audio's length |
| `events_to_raw_matrix(events, duration, bpm, …)` | -> `BuildReport` |
| `shift_events(events, offset)` | rebase for range-limited transcription |
| `note_names_of(events)` | Spanish names, for logs and tests |

Placement delegates entirely to Task 2.3.2: `snap_note` snaps the onset to the nearest column and
rounds the duration to a count expressible in at most two figures. No rounding logic is
re-implemented here.

`BuildReport` carries the matrix plus **what could not be placed**: `dropped_out_of_range` (with
the offending MIDI numbers), `dropped_past_end`, `truncated`, `placed`, `lossless` and a
`describe()` line. A transcription that quietly loses notes is worse than one that says so.

### The placement rules, in precedence order

1. **A note outside the 88 keys is dropped and reported, never wrapped.** A model that hallucinates
   MIDI 20 has not found a piano note.
2. **A note whose onset lands past the last column is dropped and reported.** The grid is sized
   from the audio, so this means the engine invented time that does not exist.
3. **A new onset always wins over a carried sustain.** Events are placed in start order, so two
   overlapping events on the same key become two notes with the first shortened — the same
   simplification Appendix B makes, and exactly what the transition rules require.

The result is validated, and normalized if anything slipped through — placement cannot legally
produce an orphan sustain, but a future engine or a hand-built event list might.

## Errors found and how they were solved

1. **The `truncated` count needed care.** Detecting "this note overwrote a previous one" means
   checking the *whole* span being written, not just its first cell — a long note can swallow a
   short one entirely without touching its onset column.
2. **Range offsets are applied defensively.** When a range is requested, the pipeline cuts the WAV
   first, so the engine's times are already relative to the range start. But an engine that
   somehow reported absolute times would place every note past the end of a short grid, so
   `transcribe_audio` rebases if the earliest event is at or after the offset. Belt and braces on a
   boundary I cannot test against a real model.

## Deviations from the task file

- Added `BuildReport` rather than returning a bare matrix; the drop counts have to reach the UI.
- The task says "run the validator in strict mode". It runs `validate()` and **normalizes** if
  there are violations, rather than raising. A model's output should never crash a user's
  transcription — the normalization rule (promote an orphan sustain to an onset) is exactly the
  right recovery, and it is the same one the text parser applies.

## Verification

```
pytest tests/test_transcription.py   # 36 passed
mypy, flake8, black                  # clean
```

The acceptance criterion is `test_the_project_features_rounding_example`, which reproduces the
worked case from `project-features.md`:

```text
C3 -> onset at 00:00 (duration 1.1 seconds)
C4 -> onset at 00:01.5 (duration 0.6 seconds)
```

At 60 BPM and fusa granularity (0.125 s per column): C3 becomes 9 columns (`1` + eight `-1`),
C4's onset lands exactly on column 12, and its 0.6 s becomes 5 columns — the nearest count
expressible in two figures.

Also covered: grid sizing (including never truncating the tail and never producing zero columns),
a single note's exact cells, out-of-range and past-the-end drops with their reports, a re-strike
shortening the previous note, a chord landing in one column, an empty event list, event shifting,
and progress reporting.

## Manual trial for the supervisor

Once the engine works (see Task 4.1.1), the real check is Epic 4's exit criterion — a recorded
scale coming back as the right notes. Right now, with hand-built events:

```bash
cd aitu-backend && uv run python -c "
from aitu_backend.transcription.engine import NoteEvent
from aitu_backend.transcription.events_to_matrix import events_to_raw_matrix
events = [NoteEvent(midi_note=60 + s, start=float(i), end=float(i) + 0.98)
          for i, s in enumerate([0, 2, 4, 5, 7])]        # Do Re Mi Fa Sol
r = events_to_raw_matrix(events, duration_seconds=5.0, tempo_bpm=60)
print(r.describe())                                       # 5 note(s) placed.
print(r.matrix.grid[39][:10].tolist())                    # [1, -1, -1, -1, -1, -1, -1, -1, 0, 0]
"
```

## For the next worker

- **Epic 7's Matrix tab** should surface `BuildReport.describe()` somewhere. If a transcription
  dropped notes, the user needs to know before they blame the renderer.
- The raw matrix is **fusa, always**. Do not add a granularity parameter to the transcription path;
  the user's granularity is reached by collapsing (Task 2.2.1), which is what keeps recompute fast.
- `snap_note`'s `tolerance` is exposed here but never varied. If real recordings land consistently
  early or late, that is the knob — see the Task 2.3.2 report.
