# Task 9.1.1 — VexFlow score format · progress

Status: **done** on 2026-07-27. Backend only; the tab that consumes it is Task 9.2.1.

## Delivered

| File | What it holds |
|------|---------------|
| `schemas/notation.py` | `ScoreDocument` and everything under it, plus `NotationSettings` |
| `notation/spelling.py` | Key tables, pitch spelling, measure-scoped accidental memory |
| `notation/durations.py` | Column spans -> VexFlow figures, measure geometry |
| `notation/score_builder.py` | The builder: runs -> timeline -> barlines -> figures -> engraving |
| `notation/artifacts.py` | Artifact ids, matrix resolution, settings storage, pre-generation |
| `api/notation.py` | The five endpoints (was five `501` placeholders) |

The pipeline per hand: read onset groups; let each note/chord fill the span to the next onset; unify
all chord members to that duration; keep only leading/trailing visible rests; cut the timeline at
the measure grid; give each piece the longest legal figure that fits; then spell, stem and beam it.

### Format decisions worth knowing

**Everything is a matrix column.** No pixel, no rendered position, anywhere in the document. That is
what lets the same document survive a resize, a re-wrap and a re-render.

**The frontend gets glyphs, not rules.** `accidentals` is the actual glyph to draw (or `null`),
decided against the key signature *and* what was already drawn earlier in the measure. Stem
directions and beam group ids travel the same way. The compatibility `tieToNext` flag is always
false under the no-tie policy. The renderer contains no music logic —
which is what `project-features.md` "Backend ease the task for Frontend" asks for.

**The last measure is completed to a barline.** The last note/chord expands to one legal figure when
possible. Only its small unwritable remainder becomes a visible trailing rest.

**Two artifact kinds, one id.** A working artifact is its audio uuid; a saved playground version is
`playground:<artist>:<track>:<vN_gX>`. `notation/artifacts.py` resolves both, so the picker, the
annotation save and the cut-measure edit all take the same parameter.

**Saving a version pre-generates its `score.json`.** `repository.save_version` calls
`artifacts.pregenerate` (local import; the notation package reads the repository back). Failures are
swallowed on purpose: a matrix that cannot be engraved yet must not break saving it. `refresh=true`
rebuilds.

## Errors found and how they were solved

**The frontend spelled everything with sharps.** `matrixToNotation.ts` mapped row -> note name
through a sharps-only table, so Sib mayor printed A# on every Bb and leaned on
`Accidental.applyAccidentals` to sort it out. Spelling is now a scored search over every letter that
can name the pitch (`notation/spelling.py`), which is also what makes "naturals over doubles" fall
out for free — a double costs 6, a natural 2.

**The beam-break rule was too eager.** Read literally, "a note whose previous and following notes are
both higher" also fires on the Mi of a Do-Sol-Mi-Sol Alberti figure, chopping the accompaniment into
pairs. The doc's own words are *the lowest note of the pattern*, so a break now also requires the note
to be no higher than anything within `ARPEGGIO_WINDOW` (3) either side. Do-Sol-Mi-Sol-Do-Sol-Mi-Sol
now breaks only at each Do, as a human would write it.

**No ties are emitted, including at barlines.** Inside a measure an odd interior remainder becomes
an invisible timing spacer, never a rest glyph or repeated note. An odd trailing remainder may be a
visible rest. When a span crosses a barline, its first fragment fills to the barline and the next
measure starts with a rest until the next onset. All cases are pinned by tests.

## Changes made along the way

- `ScoreDocument` echoes back the `annotations` it was built with. Without it the tab could not edit
  one annotation without silently dropping the rest. No plan change — an addition to the format the
  task file left open.
- `GET /notation/{artifact}` takes `tempoBpm`/`granularity`/`singleHand`/`refresh`. The task file only
  specified "returns the score document"; a working artifact has no stored BPM, so it has to be told.

## Manual trial

Covered by [`user_review/epic-09-notation.md`](../user_review/epic-09-notation.md) steps 9.1–9.2.
Golden files in `aitu-backend/tests/golden/notation/` are the machine-checked half; regenerate them
deliberately with `AITU_UPDATE_GOLDEN=1 pytest` and read the diff.

## For the next worker

- Chords are deliberately **single-voice**: simultaneous notes share the onset-to-next-onset
  duration even when recorded releases differ. This removes partial chord ties/rests and keeps the
  printed chord light.
- `notation/artifacts.py` writes a `notation.json` sidecar next to the matrices for working
  artifacts, and both `notation.json` and the version's `metadata.json` for saved versions.
- Annotation kinds `tuplet`, `trill`, `acciaccatura`, `appoggiatura` pass through the format
  untouched — Story 9.7 fills them in.
