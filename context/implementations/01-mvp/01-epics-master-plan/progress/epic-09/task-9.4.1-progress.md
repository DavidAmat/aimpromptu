# Task 9.4.1 — Key signatures and naturals · progress

Status: **done** on 2026-07-27. `notation/spelling.py` plus the tab's key panel.

## The problem this task actually solved

The matrix is sharps-only by construction: row 49 is `La#-4` whatever the piece is in. Printing that
literally puts an accidental on a note the key signature already covers — every Bb in Sib mayor would
carry a `#`. So spelling had to become a search, not a lookup.

For one sounding pitch there are up to three letters that can name it. Each is scored:

| Spelling | Cost |
|----------|------|
| covered by the key signature (no glyph) | 0 |
| needs one glyph (`#`, `b` or a natural) | 2 |
| needs a double accidental | 6 |

Small tie-breakers prefer the key's own direction. That single table does three of the four subtasks
at once:

- **9.4.1.1 initial key** — the score's key is the scoring context; `Fa` in Sol mayor prints `f/4`
  with an explicit natural, `Fa#` prints `f#/4` with no glyph.
- **9.4.1.4 naturals over doubles** — a double costs three times a natural, so no pitch in any of the
  fifteen keys ever needs one. A test asserts exactly that, across all 88 keys × 15 keys.
- **the E mayor case the doc calls out** — A# stays A# in Mi mayor (cost 2.1) rather than becoming Bb
  (2.15), because the key is sharp-leaning. The intentional tension survives.

Accidentals are also measure-scoped (`MeasureAccidentals`): a glyph holds until the barline, and
cancelling it needs an explicit natural. Without that the page repeats every sharp.

## 9.4.1.2 — Passage key changes

Stored as `Annotations.keyChanges` (column -> key), which already existed in `schemas/metadata.py`.
The builder resolves the key in force per measure, emits `keySignature` on the measure where it
changes, resets the accidental state there, and **respells** everything after it — the same key
prints A# before the change and Bb after.

A change starts at the measure its frame falls in, not mid-measure, because a key signature drawn
mid-bar is not readable.

The UI is `KeySignaturePanel`: pick a frame, pick a key, add. Changes show as removable chips.

## 9.4.1.3 — Per-measure suggestion

Every measure carries `suggestedKeySignature` (the key that would draw the fewest glyphs, computed
over **both** hands together — a key belongs to the piece, not a staff) and `accidentalCount` (what
it actually draws today). Ties keep the simpler candidate, so a passage that costs nothing in C is
never "improved" into Do# mayor.

**It is never auto-applied.** The panel lists only the measures where the suggestion disagrees *and*
accidentals are actually being drawn, as clickable chips. That is the doc's requirement almost
verbatim: intentional accidentals must survive, so the algorithm proposes and the user disposes.

## Errors found

The first cost function treated a natural and a double the same, and produced `f##` where an obvious
`g` existed. Raising the double penalty to 6 fixed it; the all-keys × all-pitches test now guards it.

Octave numbering needed care: `Cb4` and `B#3` are a semitone apart but in different octaves, so the
octave comes from the **natural letter's** pitch (`(midi - alteration) // 12 - 1`), not from the
sounding one.

## Manual trial

[`user_review/epic-09-notation.md`](../user_review/epic-09-notation.md) step 9.5 — set the key to
Sib mayor and watch the A#s become Bbs with no accidental; then add a passage key change and check
the respelling starts at the right barline.

## For the next worker

- Only the fifteen **major** keys are supported (`CANDIDATE_KEYS`). Minor keys share signatures with
  their relative majors, so nothing breaks musically, but the dropdown says "G" where a musician
  might expect "Mi menor".
- `suggest_key` takes a plain list of MIDI numbers, so it can be reused for a whole-piece suggestion
  or a selection, not just a measure.
