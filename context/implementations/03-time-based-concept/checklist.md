# Time-based concept — checklist

> **CLOSED on 2026-08-10.** This is the final state of the plan, not a live worklist. Nothing here
> is waiting to be picked up. Read [`CLOSURE.md`](CLOSURE.md) first — it says what shipped, what was
> dropped and why, and what replaces this plan.

Status codes (same as `../plan/checklist.md`): `[x]` completed · `[p]` in progress ·
`[b]` blocked (state the blocker) · `[c]` cancelled (state why) · `[ ]` not started.

Task detail: [`plan.md`](plan.md). Decisions: [`decisions.md`](decisions.md). Contract:
[`contract.md`](contract.md).

> **Where it ended.** The new path is the only path. The app has two Playground tabs, **Upload /
> Input** and **Rhythm**, and they carry the whole model: audio → time matrix → hands → peaks → a
> named ladder → figures → a drawn staff, with per-note overrides, per-passage ladders and keys,
> tresillos, reader-placed beam breaks, fingering, hand corrections, manual octave brackets and a
> printed page.
>
> **Phases 0 to 8 are complete.** Phase 9, verification and documentation, is cancelled — see the
> reason on its heading. **P1.7 is cancelled** for the same reason.
>
> **P4.2 removed the old tempo-based path from the backend and the five screens that read it**
> (I-06). A transcription stores one file, `events.json`, and everything else is re-derived per
> request. What that cost is written down in `progress/P4.2-pipeline-rewired.md` §7: there is no
> piano-roll view, no falling-notes view and no grid editor any more.
>
> **The renderer contains no beat.** No `BEATS_PER_FRAME`, no engraved spacing table, no bars, no
> metre, no time signature, no per-frame timestamp array, no 1.x file reader, no tempo callback.
> `@aimpromptu/grid-notation` finished this plan at **0.31.x**; its envelope header is one field,
> `frameMs`.
>
> **The migration has been run** (2026-08-08, with `--apply`). `data/` holds the recording, its
> metadata and `events.json`, and nothing else. The seven files the old pipeline wrote, and a full
> copy of the tree as it was before, are parked in `_to_delete/old-matrices/` for David to remove.
>
> **Everything is committed.** Both `aimpromptu` and `vexflow-v2` are on the branch
> `time-based-concept`, working tree clean.

**On the numbering.** Two different things were called P8. The **shipped features** are P8.1 …
P8.10 below, and they are what the commits mean. The verification phase that `plan.md` calls
Phase 8 is listed here as **Phase 9** so the ids do not collide. `CLOSURE.md` §5 says the same
thing in one paragraph.

---

## [x] Phase 0 — Freeze the contract

Documentation and type stubs only. No behaviour changes.

- [x] P0.1 `[AITU]` Sign off PRD, decisions and contract
- [x] P0.2 `[AITU]` Pydantic models for the new envelope, ladder, passage, score payload
- [x] P0.3 `[GN]` Mirror the same types in `src/matrix/types.ts`, keeping the 1.x types
- [x] P0.4 `[AITU]` `documentation/services/backend/time-matrix.md` stub; add this folder to `context/00-index.md`

## [x] Phase 1 — Backend: the time matrix

Built. P1.5 and P1.6 landed with P4.2, which is where the pipeline was rewired.

- [x] P1.1 `[AITU]` `matrix/time_grid.py` — frame ↔ ms, `frameMs` default 40
- [x] P1.2 `[AITU]` `transcription/grouping.py` — chord grouping on raw times, non-chaining, window = `frameMs`
- [x] P1.3 `[AITU]` `events_to_time_matrix` — snap groups, drop sub-frame notes, keep full sustain
- [x] P1.4 `[AITU]` `PianoMatrix` carries `frame_ms`; `beats_per_column` raises on a time matrix
- [x] P1.5 `[AITU]` Delete `matrix/granularity.py` and the collapsed/clean steps — *done in P4.2*
- [x] P1.6 `[AITU]` Retire `matrix/approximation.py` — *deleted in P4.2*
- [c] P1.7 `[AITU]` Update validator and cleaning for the new cell semantics — **cancelled 2026-08-10.** Never started. The old validator was written for the beats model and was removed with it, so nothing currently checks a transcription's output before it is drawn. David's call: write this when a real piece produces something visibly wrong, with that failing case as the specification, in the next plan. See `CLOSURE.md` §4.
- [x] P1.8 `[AITU]` Tests: determinism, no-BPM, frame-boundary straddle
- [x] P1.9 `[AITU]` Hand split moved before measurement (D-31)

## [x] Phase 2 — Backend: measurement

- [x] P2.1 `[AITU]` `matrix/intervals.py` — gaps from raw times, with the D-07 guard
- [x] P2.2 `[AITU]` `matrix/peaks.py` — KDE + basin peak finding
- [x] P2.3 `[AITU]` `matrix/ladder.py` — build the ladder from a named peak
- [x] P2.4 `[AITU]` `GET /time/{uuid}/peaks` *(routed under `/time`, not `/matrix`)*
- [x] P2.5 `[AITU]` `POST /time/{uuid}/ladder-preview`
- [x] P2.6 `[AITU]` **Split-peak regression test** — never delete this one

## [x] Phase 3 — Backend: figures, passages, score payload

- [x] P3.1 `[AITU]` `notation/figures.py` — closed vocabulary, dots on blanca and negra only
- [x] P3.2 `[AITU]` Proportional nearest-figure selection + the 120 ms regression
- [x] P3.3 `[AITU]` Printed length = onset → next onset in the same hand, capped at a redonda
- [x] P3.4 `[AITU]` `matrix/passages.py` — *added; `matrix/tempo_map.py` is deleted in P4.2*
- [x] P3.5 `[AITU]` Figure shift (`shift_ladder`) — backend only; the UI control is P7.3
- [x] P3.6 `[AITU]` Per-note overrides with a locality proof
- [x] P3.7 `[AITU]` `GET /time/{uuid}/score` returning the full payload
- [x] P3.8 `[AITU]` **The 00:46 test** — F5/E5/C5 must be corchea, corchea, corchea
- [x] P3.9 `[AITU]` `notation/tuplets.py` — tresillos found before figures are chosen (D-32)
- [x] P3.10 `[AITU]` Each hand measures its own attack in a shared column; `scripts/make_demo_pieces.py`

## [x] Phase 4 — Backend: pipeline, storage, migration

> **What P4.1 found.** The whole `data/` tree held **one** artifact, *Mr Blue Sky*, with its
> `events.json` intact and never hand-edited. Its `raw.npz` was proved re-derivable cell for cell.

- [x] P4.1 `[AITU]` **Artifact inventory** — which are re-derivable, which are hand-edited
- [x] P4.2 `[AITU]` Rewire `transcription/pipeline.py` onto `time_pipeline.py`; delete `granularity.py`, `approximation.py`, `tempo_map.py` — *also retired the five tempo-based tabs (I-06), so P1.5, P1.6 and P7.11 are done*
- [x] P4.3 `[AITU]` Hand split on the snapped time matrix; audit `hands/` assumptions — *measured: the split is identical at 40, 20 and 10 ms; `hands/` needed no change*
- [x] P4.4 `[AITU]` Remove `Granularity` from naming and paths; decide the new version-folder scheme — *`v2_f40`, recorded in `contract.md` §8*
- [x] P4.5 `[AITU]` Migration; flag `needsRederivation` where raw events are missing — *`scripts/migrate_to_time_matrix.py`; **applied** to `data/` on 2026-08-08*
- [x] P4.6 `[AITU]` Decide the fate of `matrix/isochrony.py` — *deleted; the failure it fixed cannot happen on a wall clock*
- [x] P4.7 `[AITU]` `text_notation.py` expresses `frameMs` — *`tempoBpm` and `timeStepSeconds` gone; `example-scores.json` converted*
- [x] P4.8 `[AITU]` Full backend suite green; delete the BPM-reinterpretation test — *589 pass, 5 skip, 0 fail*

## [x] Phase 5 — Renderer: the time → x map `[vexflow-v2]`

- [x] P5.1 `[GN]` One merged two-hand timeline — *no alignment window: grouping runs before the snap (I-03)*
- [x] P5.2 `[GN]` `FrameGrid.frameWidths` measured from content; silence compresses
- [c] P5.3 `[GN]` Time-fraction placement for orphan notes — **cancelled:** a note with no counterpart keeps its own column under D-24
- [x] P5.4 `[GN]` Retire `FrameClock.frameTimestamps` — *the clock is one scalar again*
- [x] P5.5 `[GN]` Remove `BEATS_PER_FRAME` — *the host says how many frames a negra covers (`framesPerQuarter`)*
- [x] P5.6 `[GN]` Tests: alignment, silence compression, one-map invariance — *`tests/time-to-x.test.ts`*

## [x] Phase 6 — Renderer: figures, frame groups, no bars `[vexflow-v2]`

- [x] P6.1 `[GN]` `figure-selection.ts` consumes the payload's figures (`printedFigureFor`)
- [x] P6.2 `[GN]` Delete `STAFF_SPACES_BY_BEATS` — *widths are measured from content*
- [x] P6.3 `[GN]` Delete `metre.ts` and the time-signature path — *`bar-overlay.ts`, the `bars` option and the editor's Bars tab went too*
- [x] P6.4 `[GN]` Frame groups and frame measures drawn from `LayoutHints`
- [x] P6.5 `[GN]` Passage headers on the staff
- [x] P6.6 `[GN]` No rest glyphs — `rests: false` (D-16)
- [x] P6.7 `[GN]` **Open question:** what beams group by, now there is no beat — *answered: a maximal run of consecutive beamable notes in one hand*
- [x] P6.8 `[GN]` Bump to 0.28.0; update docs; delete `onTempoRequest`
- [x] P6.9 `[GN]` Delete the 1.x reader — *`parseMatrixEnvelope` reads schema 2.0 only*
- [x] P6.10 `[GN]` Tuplet mark: bracket, numeral, and a beam split at every tuplet boundary (D-32)
- [x] P6.11 `[GN]` `thirtysecond` and `sixtyfourth` figures with their flag glyphs (D-12)
- [x] P6.12 `[GN]` `beamBreakAt`: the reader breaks a beam on any note, applied after every rule (D-34)

## [x] Phase 7 — Frontend: the ladder UI

The **Rhythm** tab is the whole screen: plot, naming, speed changes, the sheet, the player,
per-note overrides and beam breaks.

- [x] P7.1 `[AITU]` Clickable peak plot with live ladder preview
- [x] P7.2 `[AITU]` Passage drawing from a score selection
- [x] P7.3 `[AITU]` Figure-shift control — *shifts the **piece**, not one passage; the score route carries one `anchorFigure`*
- [x] P7.4 `[AITU]` Per-note figure override
- [x] P7.5 `[AITU]` Playback from `events.json` times
- [x] P7.6 `[AITU]` Library surfaces `needsRederivation` — *done in P4.5*
- [x] P7.7 `[AITU]` Remove the BPM input from every tab
- [x] P7.8 `[AITU]` **Break the beam here** on the selected note, beside the figure picker (D-34)
- [x] P7.9 `[AITU]` A playhead moving along the staff during playback — *clicking the progress bar seeks*
- [x] P7.10 `[AITU]` Save a named rhythm with the piece — *`rhythm.json` beside `events.json`; `GET`/`PUT`/`DELETE /time/{uuid}/rhythm`*
- [x] P7.11 `[AITU]` Retire the older tempo-based tabs — *done in P4.2; there were five, not four*
- [x] P7.12 `[AITU]` **Added, not in `plan.md`.** Choose the key signature for the whole piece — *lost in P4.2 with the Music Notation tab; no phase was tracking it*
- [x] P7.13 `[AITU]` **Added, not in `plan.md`.** Shift-pick a stretch of columns, Command-pick a set of notes, two draggable toolboxes
- [x] P7.14 `[AITU]` **Added.** The sheet passes `silenceGroupPx`, and stops being text-selectable
- [x] P7.15 `[AITU]` **Added.** Marked stretches show their corners; their edits come off one at a time

## [x] Phase 8 — The review stream

**Not in `plan.md`.** Ten features on 2026-08-08, every one of them from David watching the app
work on *Mr Blue Sky* rather than from the plan. One report covers all ten:
[`progress/P8.1-P8.10-the-review-stream.md`](progress/P8.1-P8.10-the-review-stream.md).

- [x] P8.1 `[AITU]` The note toolbox — fingering 1–5, play it with the other hand, start a new beam, take it off the page
- [x] P8.2 `[AITU]` A toolbox opens beside what it is about, and stays where it is dragged
- [x] P8.3 `[AITU]` An override has to touch a drawn note, or it is not drawn and not saved
- [x] P8.4 `[AITU]` A floating Save / Remove all bar that follows the page
- [x] P8.5 `[AITU]` A hand correction is written onto the recording, not onto the page — *plus a hand-split cache: redraw after an edit, 1.1 s → 0.07 s*
- [x] P8.6 `[AITU]` A hand is not written six ledger lines outside its own staff — *a real search bug in `beam.py`; piece cost 660.6 → 433.2*
- [x] P8.7 `[AITU]` The sheet goes on paper — vector PDF, page re-wrapping, margin decides how much a line holds
- [x] P8.8 `[AITU]` Five lines to a page — screen-only furniture off the printed page; 12 pages → 8
- [x] P8.9 `[GN]`/`[AITU]` No octave bracket the reader did not ask for — *twenty unasked brackets on Mr Blue Sky, gone*
- [x] P8.10 `[AITU]` One figure over a whole passage — *plus fusa and semifusa in the list*

## [c] Phase 9 — Verification and documentation

**`plan.md` calls this Phase 8.** Renumbered here so it does not collide with the shipped features
above.

**Cancelled on 2026-08-10, by David.** The app works end to end and the useful next input is a
round of real piano music, not a checklist run against the one piece we already know. What these
boxes would have produced is replaced by that round; what it turns up becomes a new plan.
`CLOSURE.md` §4 has the full reasoning.

- [c] P9.1 `[AITU]` Run and record all six success criteria — *four are backed by tests and recorded below; the two that need a long real recording are cancelled*
- [c] P9.2 `[AITU]` Regression on a straight-feel piece — *replaced by the round of real playing*
- [x] P9.3 `[AITU]` Rewrite or archive `01-matrix-notation-logic.md` — *done at closing: an obsolete-model banner points here*
- [x] P9.4 `[AITU]` Update `transcription-quality.md` and `rhythm-figures-and-tempo.md` — *done 2026-08-08*
- [x] P9.5 `[AITU]` Session trail + `context/00-index.md` — *`../progress/2026-08-10-time-based-concept-closed.md`*

---

## Success criteria (PRD §5) — final state

- [x] 1. The 00:46 F5–E5–C5 prints as three equal corcheas — `test_time_score_api.py`
- [x] 2. A ladder change moves nothing outside its passage — `ladder-locality.test.ts`; **D-33** says what does move inside it
- [x] 3. Two pipeline runs on the same audio give identical columns, with no tempo input — `test_time_matrix_build.py`
- [c] 4. Playback stays aligned with the source audio over five minutes — **never measured.** Cancelled with Phase 9; the round of real playing answers it better than a test would
- [c] 5. Every stored artifact is migrated or explicitly flagged — **the migration ran on 2026-08-08 and the flag is tested**; only the formal recording step is cancelled
- [x] 6. A held left-hand note under a fast right-hand run renders as one long note, aligned — `test_time_score_payload.py`

## Open questions — final state

- [x] P6.7 — what do beams group by, with no beat? **Answered:** a maximal run of consecutive beamable notes in one hand, cut where the melody turns, where the key or clef changes, where a cue starts, at every tuplet boundary, and wherever the reader asks (D-34).
- [x] P4.4 — new version-folder scheme: **`v2_f40`**, version number plus frame length in ms. `contract.md` §8.
- [x] P4.6 — delete `isochrony.py` or keep it as an optional user action? **Deleted.**
- [c] `frameMs` = 40 is provisional **for how the page reads**. Left provisional. It is settled for the hand split: P4.3 measured no difference between 40, 20 and 10 ms. If 40 ms reads badly on some piece, that is an observation for the next plan.

## Carried into the next plan

Nothing is carried automatically. These are the things a reader of this file would otherwise
assume are still owed, listed once so the next plan can decide about them deliberately:

- The data safety check (P1.7).
- A key change part-way through a piece: the package draws one, nothing stores one.
- Whether any of the five deleted views should come back on the wall-clock path.
- Shifting **one stretch** a step longer, rather than the whole piece.
