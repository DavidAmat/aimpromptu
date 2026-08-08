# PRD — Time-based piano matrix and figure-as-label rendering

Status: **agreed, not started.** Decisions are frozen in [`decisions.md`](decisions.md).

---

## 1. The problem

Today a matrix column does two jobs at once:

- it is the **horizontal position** of a note on the page, and
- it is the **rhythmic value** of that note.

Because it is both, the column width has to come from a tempo, and the tempo is a number the user
types in. Three things follow, and all three are observed in production data:

**Errors accumulate.** If one note rounds up by a column, every note after it in the measure
shifts. A local mistake becomes a structural one.

**A grid that cannot express the music produces garbage deterministically.** Measured on
*Mr Blue Sky — segment 00:05.00–05:10.37*: the right hand splits each beat **63 % / 37 %** (a
shuffle), so the two halves of a beat land at **1.48** and **2.51** semicorchea columns — as close
to a coin toss as arithmetic allows. **38 %** of that section's notes sit in that coin-toss zone.
The worked example at 00:46 (F5 → E5 → C5, three equal corcheas on the printed sheet) comes out of
the app as **semicorchea → corchea con puntillo → semicorchea**. Not one of the three is right, and
it is not noise — it is the same wrong answer every time the figure appears.

**Nothing about this is fixable by a finer grid.** The raw semifusa grid holds the pair perfectly
(10 and 6 units of 16 per beat). A 5 : 3 split of a beat has no representation on any power-of-two
subdivision, at any resolution.

Full evidence: [`../../../poc-onset-duration-distribution/RESULTS.md`](../../../poc-onset-duration-distribution/RESULTS.md).

## 2. The change in one sentence

> Split "where the note sits" from "what figure the note is drawn as" into two independent numbers:
> position comes from **measured wall-clock time**, the figure comes from a **user-chosen ladder of
> millisecond values**.

Everything else in this document falls out of that.

## 3. What the product becomes

AImpromptu stops trying to produce an exactly-correct engraved score and produces a **readable
representation of a performance**: accurate onsets, approximate and deliberately tidy durations, no
ties, no rest glyphs, no bar lines. The intended reader is a pianist who already knows the piece and
wants a clean visual guide — not a sight-reader receiving it cold.

This is a deliberate narrowing. It is also strictly more informative than what exists now: real
times plus a fitted ladder is a superset of a quantised score, so a metrical score can always be
derived later. The reverse is impossible.

## 4. How it works

### 4.1 The matrix becomes a clock

A frame is a fixed number of milliseconds — **40 ms by default**, recorded in the matrix metadata.
No BPM anywhere. Column *n* is always `n × 40 ms` after the start, in every piece, forever. Column
numbers stop moving when anything else changes. (D-01, D-02, D-30)

The unsnapped float timestamps from the transcription are kept and remain the source of truth for
every measurement. (D-03)

### 4.2 Measurement runs on raw times, never on the grid

This is not a preference, it is a correctness requirement. Rounding onsets to 40 ms before measuring
**splits every peak in two**: a real 337 ms gap becomes 8 *or* 9 frames depending on where the two
notes happen to fall, so it appears as 320 ms ~57 % of the time and 360 ms the rest. The single
clearest signal in the data — one spike holding half of all gaps — would arrive as two half-height
spikes. Same for 211 → 200/240 and 125 → 120/160. (D-07)

The same argument applies to chord grouping: notes 39 ms apart can straddle a frame boundary, so
grouping must happen on raw times *before* snapping, and the whole group snaps together. (D-04)

### 4.3 The user names the ladder

The app shows the distribution of gaps between consecutive onsets, with clickable peaks. The user
clicks one and says what it is — "this 337 ms peak is the negra". Every other peak is then labelled
by proportion, immediately, so the user can see whether the choice makes sense before committing.
(D-09, D-10)

The app never guesses. Interval statistics fix the ladder only up to a rational factor — a beat and
twice that beat explain the same gaps equally well, and on this piece's second half two candidates
scored within 0.1 % of each other. That ambiguity is unresolvable from timings, so it is a question,
not an inference.

### 4.4 Figures are labels

A gap maps to the nearest figure **by proportion, not by milliseconds** (D-11). With negra = 320,
a 120 ms gap is exactly 40 ms from both 160 and 80 — a coin toss in absolute terms, but 25 % vs 50 %
in proportional terms, so corchea wins cleanly and always.

Vocabulary is deliberately small: no ties, no ligatures, dots only on negra and blanca (D-12, D-13).
That restriction is not only cosmetic — with dotted corcheas banned, the swing pair 211 / 125 both
land on *corchea*, which is exactly what the printed sheet shows. Allowing the dot would pull 211 to
a dotted corchea and reproduce the ragged mix this refactor exists to remove.

Getting a figure wrong now moves nothing. The frame is the same width either way. Which also means
the figure's *only* remaining job is to be read — so per-note override (D-17) and whole-ladder
re-pointing ("figure shift", D-18) are first-class features, not escape hatches.

### 4.5 Passages

A passage carries its own ladder. Its header prints `negra = 320 ms` and the equivalent BPM.
Passage boundaries are drawn **by hand** in v1 (D-19). Automatic segmentation is deferred on
purpose: a wrong hand-drawn boundary spoils one section, a wrong automatic one scatters tempo
changes across the piece and makes the sheet unreadable for the player.

### 4.6 Layout

One single `time → x` map, built from **both hands' onsets merged**, shared by every staff and every
ruler (D-22). This removes the whole "which hand is limiting this region" question — it falls out.
Silence is compressed to a small padding per frame group (D-23), near-simultaneous onsets share one
x across both hands (D-24), and a note with no counterpart on the other hand is placed by its time
fraction between its neighbours (D-25).

Frame groups are the clickable unit; frame measures are where the dashed lines go (D-27). There are
no bar lines and no time signature (D-28).

### 4.7 Playback never lies

Every player plays the original recorded onset times. Nothing inferred is ever heard. (D-29)

## 5. Success criteria

1. On *Mr Blue Sky* segment A, the F5–E5–C5 at 00:46 prints as **three equal corcheas**.
2. Changing the ladder for one passage moves **nothing** outside that passage — verified by diffing
   the rendered x positions.
3. Re-running the pipeline on the same audio twice produces **byte-identical** column indices, with
   no tempo input at all.
4. Playback stays aligned with the source audio for the full length of a five-minute piece.
5. Every existing stored artifact either migrates or is explicitly marked as needing re-derivation —
   nothing is silently reinterpreted.
6. A held left-hand note under a fast right-hand run still renders as one long note on the left
   staff, correctly aligned with the run above it.

## 6. Explicitly out of scope

| Not doing | Why |
|---|---|
| Automatic passage / tempo segmentation | D-19. Deferred to a later iteration; the PoC code exists and can be bolted on as a *suggestion* |
| Ties and ligatures | D-13. They are most of what makes the current output ugly |
| Rest glyphs | D-16. Silence reads from the dashed lines |
| Bar lines, time signatures, metre | D-28. There is no meter in this model |
| Triplet notation | Not needed — the shuffle prints correctly as equal corcheas without it |
| Exact release-time notation | D-14 is deliberate: printed length is onset-to-next-onset, per hand |
| Live-input tempo tracking | The ladder is set by hand; a live performer's drift is a later problem |

## 7. Known costs, accepted

- **A held note inside one hand gets cut short** when that hand plays anything else (D-14).
  Deliberate: the alternative fills the page with ties, rests and inner voices, which is the ugliness
  being removed.
- **Fast sections are measured less precisely than slow ones.** At 40 ms frames, a 115 ms gap is under
  three frames, so ±20 ms of snapping is a sixth of the note. Slow passages will look excellent,
  fast ones noticeably rougher. Mitigation is the per-passage ladder: the user re-points a fast
  section so its notes become corcheas rather than fusas.
- **40 ms is coarser than today's raw grid** (21 ms at 178 BPM). The hand splitter and the chord
  logic see less. Mitigated by D-04 (group on raw times before snapping) and by keeping the raw
  events on disk.
- **`Granularity` disappears from the storage layer**, which touches folder naming and every stored
  path. That is the single largest migration risk; Phase 4 owns it.

## 8. Where to look deeper

- [`decisions.md`](decisions.md) — the numbered decisions every task cites
- [`contract.md`](contract.md) — the backend ↔ renderer interface
- [`plan.md`](plan.md) — phases, tasks, dependencies
- [`../../music/notation-logic/01-matrix-notation-logic.md`](../../music/notation-logic/01-matrix-notation-logic.md) — the model being replaced
