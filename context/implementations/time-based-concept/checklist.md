# Time-based concept — checklist

**The single status lookup for this refactor.** Start here when picking up work.

Status codes (same as `../plan/checklist.md`): `[x]` completed · `[p]` in progress ·
`[b]` blocked (state the blocker) · `[c]` cancelled (state why) · `[ ]` not started.

Mark `[p]` when you start and the final status when you finish. **Work done in `vexflow-v2` is
ticked here, not there** — see the reporting rule in [`README.md`](README.md).

Task detail: [`plan.md`](plan.md). Decisions: [`decisions.md`](decisions.md). Contract:
[`contract.md`](contract.md).

> **Current boundary.** The new path is the only path. The app has two Playground tabs, **Upload /
> Input** and **Rhythm**, and they carry the whole model: audio → time matrix → hands → peaks → a
> named ladder → figures → a drawn staff, with per-note overrides, per-passage ladders, tresillos
> and reader-placed beam breaks.
>
> **P4.2 removed the old tempo-based path from the backend and the five screens that read it**
> (I-06). A transcription now stores one file, `events.json`, and everything else is re-derived per
> request. What that cost is written down in `progress/P4.2-pipeline-rewired.md` §7: there is no
> piano-roll view, no falling-notes view and no grid editor any more.
>
> **Phases 4, 5 and 6 are complete.** The renderer package no longer contains a beat: no
> `BEATS_PER_FRAME`, no engraved spacing table, no bars, no metre, no time signature, no per-frame
> timestamp array, no 1.x file reader and no tempo callback. It is `@aimpromptu/grid-notation`
> **0.28.0**, and its envelope header is one field, `frameMs`.
>
> **The sheet now reads the payload's layout hints.** A dashed line every `frameMeasure` columns,
> a selection that snaps to `frameGroup` columns, and each passage's own label above the staff where
> it begins.
>
> **The migration has been run** (2026-08-08, with `--apply`). `data/` holds the recording, its
> metadata and `events.json`, and nothing else. The seven files the old pipeline wrote, and a full
> copy of the tree as it was before, are parked in `_to_delete/old-matrices/` for David to remove.
>
> **Everything is committed.** `aimpromptu` is on the branch `time-based-concept`. `vexflow-v2` is
> now on a branch of the same name: the renderer's whole half of this refactor was uncommitted on
> `main` until 2026-08-08 and is now recorded, one commit per task.
>
> **What is left: `P1.7`, and all of Phase 8.** P1.7 is the last open box outside Phase 8 and is the
> one piece of real backend work still to do.

---

## [x] Phase 0 — Freeze the contract

Documentation and type stubs only. No behaviour changes.

- [x] P0.1 `[AITU]` Sign off PRD, decisions and contract
- [x] P0.2 `[AITU]` Pydantic models for the new envelope, ladder, passage, score payload
- [x] P0.3 `[GN]` Mirror the same types in `src/matrix/types.ts`, keeping the 1.x types
- [x] P0.4 `[AITU]` `documentation/services/backend/time-matrix.md` stub; add this folder to `context/00-index.md`

## [p] Phase 1 — Backend: the time matrix

Built. P1.5 and P1.6 landed with P4.2, which is where the pipeline was rewired. P1.7 is the one box
here that is a real piece of work rather than a deletion.

- [x] P1.1 `[AITU]` `matrix/time_grid.py` — frame ↔ ms, `frameMs` default 40
- [x] P1.2 `[AITU]` `transcription/grouping.py` — chord grouping on raw times, non-chaining, window = `frameMs`
- [x] P1.3 `[AITU]` `events_to_time_matrix` — snap groups, drop sub-frame notes, keep full sustain
- [x] P1.4 `[AITU]` `PianoMatrix` carries `frame_ms`; `beats_per_column` raises on a time matrix
- [x] P1.5 `[AITU]` Delete `matrix/granularity.py` and the collapsed/clean steps — *done in P4.2*
- [x] P1.6 `[AITU]` Retire `matrix/approximation.py` — *deleted in P4.2*
- [ ] P1.7 `[AITU]` Update validator and cleaning for the new cell semantics — **not started**; the only Phase 1 box still open
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

**The remaining backend work, and the highest risk in the refactor.** P4.1 first, always: nothing
here is reversible without the raw events.

> **What P4.1 found.** The whole `data/` tree holds **one** artifact, *Mr Blue Sky*, with its
> `events.json` intact and never hand-edited. No saved versions, no library tracks. Its `raw.npz`
> was proved re-derivable cell for cell. **Copy `aitu-backend/data/` outside the repository before
> P4.5 writes anything:** `data/audio/**` is gitignored, so those recorded notes exist in one place
> only.

- [x] P4.1 `[AITU]` **Artifact inventory** — which are re-derivable, which are hand-edited
- [x] P4.2 `[AITU]` Rewire `transcription/pipeline.py` onto `time_pipeline.py`; delete `granularity.py`, `approximation.py`, `tempo_map.py` — *also retired the five tempo-based tabs (I-06), so P1.5, P1.6 and P7.11 are done*
- [x] P4.3 `[AITU]` Hand split on the snapped time matrix; audit `hands/` assumptions — *measured: the split is identical at 40, 20 and 10 ms; `hands/` needed no change*
- [x] P4.4 `[AITU]` Remove `Granularity` from naming and paths; decide the new version-folder scheme — *`v2_f40`, recorded in `contract.md` §8*
- [x] P4.5 `[AITU]` Migration; flag `needsRederivation` where raw events are missing — *`scripts/migrate_to_time_matrix.py`, dry run by default. **Not applied to `data/` yet** — see the report §9*
- [x] P4.6 `[AITU]` Decide the fate of `matrix/isochrony.py` — *deleted; the failure it fixed cannot happen on a wall clock*
- [x] P4.7 `[AITU]` `text_notation.py` expresses `frameMs` — *`tempoBpm` and `timeStepSeconds` gone; `example-scores.json` converted*
- [x] P4.8 `[AITU]` Full backend suite green; delete the BPM-reinterpretation test — *589 pass, 5 skip, 0 fail; both baseline failures gone*

## [x] Phase 5 — Renderer: the time → x map `[vexflow-v2]`

Complete. P5.3 is the one cancelled box: a note with no counterpart keeps its own column under D-24.

- [x] P5.1 `[GN]` One merged two-hand timeline — *no alignment window: grouping runs before the snap, so near-simultaneous onsets already share a frame, and one frame is one x (I-03)*
- [x] P5.2 `[GN]` `FrameGrid.frameWidths` measured from content; silence compresses
- [c] P5.3 `[GN]` Time-fraction placement for orphan notes — **cancelled:** a note with no counterpart simply keeps its own column under D-24
- [x] P5.4 `[GN]` Retire `FrameClock.frameTimestamps` — *the clock is one scalar again; `shiftFrameTimestamps` went with it*
- [x] P5.5 `[GN]` Remove `BEATS_PER_FRAME` — *the host says how many frames a negra covers (`framesPerQuarter`); the grid no longer answers*
- [x] P5.6 `[GN]` Tests: alignment, silence compression, one-map invariance — *`tests/time-to-x.test.ts`; D-25 stays out because P5.3 is cancelled*

## [x] Phase 6 — Renderer: figures, frame groups, no bars `[vexflow-v2]`

- [x] P6.1 `[GN]` `figure-selection.ts` consumes the payload's figures (`printedFigureFor`) — *the tie machinery is still present and goes with P6.9*
- [x] P6.2 `[GN]` Delete `STAFF_SPACES_BY_BEATS` — *the engraved table and its two width helpers are gone; widths are measured from content*
- [x] P6.3 `[GN]` Delete `metre.ts` and the time-signature path — *`metre.ts`, `bar-overlay.ts`, the renderer's `bars` option and the editor's Bars tab are all gone*
- [x] P6.4 `[GN]` Frame groups and frame measures drawn from `LayoutHints` — *the dashed lines follow `frameMeasure`, the selectable regions follow `frameGroup`*
- [x] P6.5 `[GN]` Passage headers on the staff — *each passage prints its label above the staff where it begins*
- [x] P6.6 `[GN]` No rest glyphs — `rests: false` (D-16)
- [x] P6.7 `[GN]` **Open question:** what beams group by, now there is no beat — *answered: a maximal run of consecutive beamable notes in one hand*
- [x] P6.8 `[GN]` Bump to 0.28.0; update docs; delete `onTempoRequest` — *the BPM tab went with it; five documents rewritten*
- [x] P6.9 `[GN]` Delete the 1.x reader — *`parseMatrixEnvelope` reads schema 2.0 only and refuses a 1.x file; the envelope header is `frameMs` alone*
- [x] P6.10 `[GN]` Tuplet mark: bracket, numeral, and a beam split at every tuplet boundary (D-32)
- [x] P6.11 `[GN]` `thirtysecond` and `sixtyfourth` figures with their flag glyphs (D-12)
- [x] P6.12 `[GN]` `beamBreakAt`: the reader breaks a beam on any note, applied after every rule (D-34)

## [x] Phase 7 — Frontend: the ladder UI

The **Rhythm** tab is the whole screen: plot, naming, speed changes, the sheet, the player, per-note
overrides and beam breaks.

- [x] P7.1 `[AITU]` Clickable peak plot with live ladder preview
- [x] P7.2 `[AITU]` Passage drawing from a score selection
- [x] P7.3 `[AITU]` Figure-shift control — *two buttons on the Rhythm tab; shifts the **piece**, not one passage, because the score route carries one `anchorFigure`. Corrected `shift_ladder`: a step is a doubling, not a dot (it contradicted D-18's own example)*
- [x] P7.4 `[AITU]` Per-note figure override
- [x] P7.5 `[AITU]` Playback from `events.json` times
- [x] P7.6 `[AITU]` Library surfaces `needsRederivation` — *done in P4.5; the audio list and the Rhythm tab both print the reason*
- [x] P7.7 `[AITU]` Remove the BPM input from every tab
- [x] P7.8 `[AITU]` **Break the beam here** on the selected note, beside the figure picker (D-34)
- [x] P7.9 `[AITU]` A playhead moving along the staff during playback — *`placeCursor` was already in the package; clicking the progress bar seeks, and a refused `play()` now says so*
- [x] P7.10 `[AITU]` Save a named rhythm with the piece — *`rhythm.json` beside `events.json`; one per piece, cleared by a re-transcription. `GET`/`PUT`/`DELETE /time/{uuid}/rhythm`*
- [x] P7.11 `[AITU]` Retire the older tempo-based tabs — *done in P4.2; there were five, not four: Matrix, Piano Roll, Notes Falling, Notes Falling (raw) and Music Notation*

## [ ] Phase 8 — Verification and documentation

- [ ] P8.1 `[AITU]` Run and record all six success criteria
- [ ] P8.2 `[AITU]` Regression on a straight-feel piece
- [ ] P8.3 `[AITU]` Rewrite or archive `01-matrix-notation-logic.md`
- [ ] P8.4 `[AITU]` Update `transcription-quality.md` and `rhythm-figures-and-tempo.md`
- [ ] P8.5 `[AITU]` Session trail + `context/00-index.md`

---

## Success criteria (PRD §5) — tick only in P8.1

Marked here with what currently backs each one, so P8.1 records rather than discovers.

- [x] 1. The 00:46 F5–E5–C5 prints as three equal corcheas — `test_time_score_api.py`
- [x] 2. A ladder change moves nothing outside its passage — `ladder-locality.test.ts`; **D-33** says what does move inside it
- [x] 3. Two pipeline runs on the same audio give identical columns, with no tempo input — `test_time_matrix_build.py`
- [ ] 4. Playback stays aligned with the source audio over five minutes — **not measured**; needs a long real recording
- [ ] 5. Every stored artifact is migrated or explicitly flagged — *the migration and the flag exist and are tested (P4.5); tick this in P8.1 once it has been run*
- [x] 6. A held left-hand note under a fast right-hand run renders as one long note, aligned — `test_time_score_payload.py`

## Open questions carried into implementation

- [x] P6.7 — what do beams group by, with no beat? **Answered in P6.7's report:** a maximal run of consecutive beamable notes in one hand, cut where the melody turns, where the key or clef changes, where a cue starts, at every tuplet boundary, and wherever the reader asks (D-34).
- [x] P4.4 — new version-folder scheme: **`v2_f40`**, version number plus frame length in ms. `contract.md` §8.
- [x] P4.6 — delete `isochrony.py` or keep it as an optional user action? **Deleted.** The 1.27-columns failure it fixed is arithmetic a wall-clock grid cannot produce.
- [ ] `frameMs` = 40 is provisional **for how the page reads** (P8.2). It is settled for the hand split: P4.3 measured no difference between 40, 20 and 10 ms.
