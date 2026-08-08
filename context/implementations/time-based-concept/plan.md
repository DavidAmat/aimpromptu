# Implementation plan

Nine phases. Every task cites the decisions it implements. Status lives in
[`checklist.md`](checklist.md), not here.

Task ids are `P<phase>.<n>`. Each task is tagged with the repository it lands in:

- **`[AITU]`** — `aimpromptu/aitu-backend` or `aimpromptu/aitu-frontend`
- **`[GN]`** — `vexflow-v2` (`@aimpromptu/grid-notation`)

> Work done in **`[GN]`** is still reported here. See the reporting rule in
> [`README.md`](README.md).

## Dependency shape

```
P0  freeze the contract
     |
     +-- P1 -> P2 -> P3 -> P4        [AITU]  backend
     |
     +-- P5 -> P6                    [GN]    renderer   (parallel with P1-P4)
                 |
     P3 + P6 --> P7                  [AITU]  frontend
                  |
                  P8  verification and docs
```

P5 and P6 can start the moment P0 lands. They must not wait for the backend — that is the entire
reason the contract is frozen first.

---

# Phase 0 — Freeze the contract

Documentation and type stubs only. No behaviour changes.

| id | repo | task | decisions |
|---|---|---|---|
| P0.1 | AITU | Review and sign off [`PRD.md`](PRD.md), [`decisions.md`](decisions.md), [`contract.md`](contract.md). Any disagreement resolved *here*, before code. | all |
| P0.2 | AITU | Add the `TimeMatrixEnvelope`, `FigureLadder`, `Passage`, `TimeScorePayload` Pydantic models to `aitu_backend/schemas/`. Unused for now; they exist so both sides compile against the same names. | contract §2–5 |
| P0.3 | GN | Mirror the same types in `src/matrix/types.ts` alongside the existing 1.x types. Do not delete the 1.x types yet. | contract §7 |
| P0.4 | AITU | Write `documentation/services/backend/time-matrix.md` stub with the `> Context:` header pointing here. Add all new files to `context/00-index.md`. | — |

**Exit:** both repos compile with the new types present and unused; `00-index.md` lists this folder.

---

# Phase 1 — Backend: the time matrix

Replaces the granularity-based raw matrix with a wall-clock one.

| id | repo | task | decisions |
|---|---|---|---|
| P1.1 | AITU | `matrix/time_grid.py`: the frame ↔ ms conversions, `frameMs` default 40, validation. This is the only module that knows the frame length. | D-01 |
| P1.2 | AITU | `transcription/grouping.py`: chord/arpeggio grouping on **raw** float times. 20 ms window, non-chaining, measured from the group's first onset. Returns groups, not columns. Port the tested implementation from `poc-onset-duration-distribution/scripts/common.py::collapse_attacks`. | D-04 |
| P1.3 | AITU | Rewrite `transcription/events_to_matrix.py`: drop sub-frame notes, group per P1.2, snap each group to one frame, write measured sustain capped at one redonda. No tempo argument anywhere in the signature. | D-02, D-05, D-06 |
| P1.4 | AITU | Rewrite `matrix/model.py`: `PianoMatrix` carries `frame_ms` instead of `granularity` + `tempo_bpm`. `seconds_per_column` becomes a constant lookup. | D-01, D-30 |
| P1.5 | AITU | **Delete** `matrix/granularity.py` (collapse/upsample) and the `collapsed`/`clean` processing steps. There is one grid now; there is nothing to collapse to. | D-01 |
| P1.6 | AITU | Retire `matrix/approximation.py` (Appendix C) — duration approximation moves to the ladder in P3.3 and is no longer a grid operation. Keep the module only if `text_notation.py` still needs it; otherwise delete. | D-11, D-13 |
| P1.7 | AITU | Update `matrix/validator.py` and `matrix/cleaning.py` for the new cell semantics. Appendix B's "a sustain dies when any other onset starts" is now only about *measured* sustain, not about printed length. | D-06, D-14 |
| P1.8 | AITU | Tests: determinism (same audio twice → identical columns), no-BPM (no code path accepts a tempo), grouping straddle case (two onsets 39 ms apart either side of a frame boundary land in one group). | D-02, D-04 |

**Exit:** `events.json` → time matrix, with no tempo input, byte-identical across runs.

---

# Phase 2 — Backend: measurement

The PoC promoted to production code. **Everything here reads raw timestamps.**

| id | repo | task | decisions |
|---|---|---|---|
| P2.1 | AITU | `matrix/intervals.py`: gaps between consecutive attacks per hand, from raw times. Port from `poc-onset-duration-distribution/scripts/common.py`. | D-03, D-07 |
| P2.2 | AITU | `matrix/peaks.py`: KDE + basin peak finding. Port `analysis.py::gaussian_kde_grid` / `find_peaks`. Guard: assert the input is raw seconds, never frame indices. | D-07 |
| P2.3 | AITU | `matrix/ladder.py`: given a peak the user named and its figure, build the full nine-entry ladder by proportion. Also the reverse preview — "if you call *this* peak a negra, here is what every other peak becomes". | D-10, D-12 |
| P2.4 | AITU | `GET /matrix/{uuid}/peaks?startSeconds=&endSeconds=&hand=` → peak list with centre, count, share and basin. Whole piece when the range is omitted. | D-08 |
| P2.5 | AITU | `POST /matrix/{uuid}/ladder-preview` → given `{anchorFigure, anchorMs}`, return the ladder plus what each detected peak would be labelled and its fit error. Drives the click-a-peak dialog. | D-09, D-10 |
| P2.6 | AITU | Tests: the split-peak regression — build the same gaps, measure on raw times and on snapped columns, assert the raw run finds one peak where the snapped run finds two. This test is the reason D-07 exists; it must never be deleted. | D-07 |

**Exit:** the peak table for *Mr Blue Sky* segment A reproduces the PoC's 125 / 211 / 337 / 463 / 674 / 799 within 1 ms.

---

# Phase 3 — Backend: figures, passages, score payload

| id | repo | task | decisions |
|---|---|---|---|
| P3.1 | AITU | `notation/figures.py`: the closed vocabulary. Dots on blanca and negra only. Replaces `notation/durations.py`'s VexFlow token table. | D-12 |
| P3.2 | AITU | Proportional nearest-figure selection: minimise `|log2(gap / candidate)|`. Add an explicit regression for the 120 ms case (must resolve to corchea at negra = 320, never a coin toss). | D-11 |
| P3.3 | AITU | Printed-length rule: onset → next onset **in the same hand**, chord groups from P1.2 treated as one event, capped at one redonda. | D-14, D-15 |
| P3.4 | AITU | `matrix/passages.py`: user-drawn passage list keyed by frame, tiling and non-overlapping, each with its own ladder. Replaces `matrix/tempo_map.py` — the seam logic there is no longer needed because frames do not move. | D-19, D-20, D-21 |
| P3.5 | AITU | "Figure shift": re-point a passage's ladder by N steps. Pure relabelling; assert no `startFrame` changes. | D-18 |
| P3.6 | AITU | Per-note overrides: store, apply, and prove locality — a stored override changes exactly one `PrintedNote.figure` and nothing else in the payload. | D-17 |
| P3.7 | AITU | `GET /score/{uuid}` → the full `TimeScorePayload` from [`contract.md`](contract.md) §5. | contract §5 |
| P3.8 | AITU | Tests: the 00:46 case. F5 / E5 / C5 must come out **corchea, corchea, corchea** with negra = 320. This is success criterion 1. | D-11, D-12, D-14 |
| P3.9 | AITU | `notation/tuplets.py`: find tresillos before any figure is chosen — three consecutive gaps in one hand that match each other and are a third of a figure the ladder knows. Non-overlapping. The three notes print as the figure one step down, carry `tuplet: 3` and a `tupletId` unique across both hands, and have `fitError` 0. The peak plot names a third-of-a-negra pile "corchea de tresillo". | D-32 |

**Exit:** `GET /score/{uuid}` returns a payload the renderer can draw, and the 00:46 test is green.

---

# Phase 4 — Backend: pipeline, storage, migration

The highest-risk phase. Nothing here is reversible without the raw events, so do P4.1 first.

| id | repo | task | decisions |
|---|---|---|---|
| P4.1 | AITU | **Inventory every stored artifact** before touching anything: which have `events.json` (re-derivable) and which are hand-edited (not). Write the list to `progress/P4.1-artifact-inventory.md`. Do not proceed until it exists. | — |
| P4.2 | AITU | Rewire `transcription/pipeline.py`: events → time matrix → hand split → score payload. The `collapse` and `clean` stages are gone. | D-31 |
| P4.3 | AITU | Move the hand split to run on the snapped time matrix. `hands/` itself is unchanged — it reads onset groups, which still exist — but its input granularity assumptions must be audited. | D-31 |
| P4.4 | AITU | Remove `Granularity` from `schemas/naming.py` and `storage/paths.py`. Version folders `v2_gsc` become `v2` (or `v2_f40`); decide the new scheme in this task and record it in `contract.md`. | D-01, D-30 |
| P4.5 | AITU | Migration: for every artifact with `events.json`, re-derive at 40 ms. For hand-edited artifacts with no raw events, mark `needsRederivation: true` and surface it in the library — **never silently reinterpret one.** | success criterion 5 |
| P4.6 | AITU | Retire `matrix/isochrony.py` or repoint it. Its run-evening logic is about forcing notes onto a beat grid, which no longer exists. Decide: delete, or keep as an optional "tidy this run" user action. Record the decision in `progress/`. | D-14 |
| P4.7 | AITU | Update `matrix/text_notation.py` — the portable text format must express `frameMs`, not a granularity code. | D-30 |
| P4.8 | AITU | Full backend test suite green. Note the two pre-existing failures (`test_api_smoke::test_scores_returns_a_list`, `test_changing_the_bpm_reinterprets_the_same_grid`) — the second should now be **deleted**, not fixed. | — |

**Exit:** the pipeline runs end to end with no tempo anywhere, and every stored artifact is either migrated or flagged.

---

# Phase 5 — Renderer: the time → x map

**`[GN]` — `vexflow-v2`.** Can start as soon as P0 lands.

| id | repo | task | decisions |
|---|---|---|---|
| P5.1 | GN | Build the merged event timeline: both hands' onsets in one ordered list, near-simultaneous onsets (within `alignWindowMs`) collapsed to a single x slot. | D-22, D-24 |
| P5.2 | GN | Feed `FrameGrid.frameWidths` from that timeline: constant width between consecutive events, silent frame groups collapsed to `silenceGroupPx`. `FrameGrid` already supports variable widths and is already documented as the only frame ↔ x transform — this extends it, it does not replace it. | D-22, D-23, D-26 |
| P5.3 | GN | Time-fraction placement for a note with no counterpart on the other hand: position by `(t − t_prev) / (t_next − t_prev)` across the slot, not at the midpoint. | D-25 |
| P5.4 | GN | Retire `FrameClock.frameTimestamps`. Frames are uniform by construction now; the array path becomes dead code. | contract §1 |
| P5.5 | GN | Remove `BEATS_PER_FRAME` and every beats-per-frame derivation. A frame has no beat value. | contract §1 |
| P5.6 | GN | Tests: vertical alignment (two onsets 15 ms apart share an x; 200 ms apart do not), silence compression (a 5 s rest occupies `silenceGroupPx × groups`), time-fraction placement, and one-map invariance (both staves and the ruler agree on every x). | D-22, D-24, D-25 |

**Exit:** a `TimeScorePayload` renders with correct x positions on both staves, no figures required yet.

---

# Phase 6 — Renderer: figures, frame groups, no bars

**`[GN]` — `vexflow-v2`.**

| id | repo | task | decisions |
|---|---|---|---|
| P6.1 | GN | Rewrite `notation/figure-selection.ts` to consume `PrintedNote.figure` directly. The renderer stops choosing; it draws what the payload says and applies `overrides`. Delete the beats-based candidate search and the `sequence`/tie machinery. | D-11, D-13, D-17 |
| P6.2 | GN | Rewrite `notation/spacing.ts`: horizontal space comes from the x map (P5.2), not from `STAFF_SPACES_BY_BEATS`. The engraved-spacing table is deleted — spacing is density, not duration. | D-22, D-26 |
| P6.3 | GN | Delete `notation/metre.ts`, `notation/bar-overlay.ts` and the time-signature path. | D-28 |
| P6.4 | GN | Frame groups and frame measures in `ruler/frame-ruler.ts`: dashed lines every `frameMeasure` frames, selectable regions every `frameGroup` frames, both from `LayoutHints`. | D-27 |
| P6.5 | GN | Passage headers: print `negra = 320 ms · ≈188 BPM` at the start of the piece and at every passage boundary. Replaces the tempo mark. | D-20 |
| P6.6 | GN | No rest glyphs. Verify silence reads correctly from the dashed lines alone at several zoom levels. | D-16 |
| P6.7 | GN | Audit `notation/beam-groups.ts`. Beaming grouped by beat, and there is no beat. Decide: group by frame measure, group by consecutive same-figure runs, or drop beams. Record the decision in `progress/`. | D-28 |
| P6.10 | GN | Draw the tuplet mark: a `tupletFor` lookup alongside `printedFigureFor`, a bracket with the numeral in a gap left for it, on the beam side of the group, and a beam split at every tuplet boundary so two tresillos in a row never read as one group of six. | D-32 |
| P6.12 | GN | `beamBreakAt`: a lookup saying a note starts a new beam group, applied after every automatic split — figures, key and clef changes, cue passages, tuplets, arpeggio low points. A break that would strand the first note leaves it with a flag. | D-34 |
| P6.8 | GN | Bump to `0.28.0`, update `docs/architecture.md`, `docs/contracts.md`, `docs/integration.md`. Delete the `onTempoRequest` host contract — there is no BPM to request. | contract §1 |
| P6.9 | GN | Delete the 1.x envelope reader once P4.5's migration has run. **Not before.** | contract §7 |

**Exit:** the 00:46 passage renders as three equal corcheas; no bar lines, no rests, no ties anywhere in the output.

---

# Phase 7 — Frontend: the ladder UI

| id | repo | task | decisions |
|---|---|---|---|
| P7.1 | AITU | Peak plot with clickable peaks. Click → dialog: "call this a …", with a live preview of what every other peak becomes and its fit error. | D-09, D-10 |
| P7.2 | AITU | Passage drawing: select a range on the score, compute its peaks (P2.4 with a range), name a peak, save the passage. | D-08, D-19 |
| P7.3 | AITU | Figure-shift control on a passage: "make everything one step longer/shorter". | D-18 |
| P7.4 | AITU | Per-note override: click a note, choose a figure, persist. | D-17 |
| P7.5 | AITU | Playback wired to `events.json` times. Verify against the source audio over a full five-minute piece. | D-29, success criterion 4 |
| P7.6 | AITU | Library: surface `needsRederivation` artifacts from P4.5 with a clear explanation and a re-derive action. | success criterion 5 |
| P7.7 | AITU | Remove the BPM input from every tab. Replace with the ladder display. | D-01, D-20 |

**Exit:** a user can load an audio, see peaks, name a ladder, draw a passage, override a note, and hear playback that matches the source.

---

# Phase 8 — Verification and documentation

| id | repo | task | decisions |
|---|---|---|---|
| P8.1 | AITU | Run all six success criteria from [`PRD.md`](PRD.md) §5 as an explicit checklist. Record the result per criterion in `progress/P8.1-success-criteria.md`. | PRD §5 |
| P8.2 | AITU | Regression on a second piece with a **straight** (non-shuffled) feel, to confirm the ladder is not overfitted to *Mr Blue Sky*. | — |
| P8.3 | AITU | Update `context/music/notation-logic/01-matrix-notation-logic.md` — Appendices A–D describe a model that no longer exists. Either rewrite or move to `archive/` with a pointer here. | — |
| P8.4 | AITU | Update `context/music/transcription-quality.md` and `documentation/issues/rhythm-figures-and-tempo.md`. The latter's runbook should end with "this class of bug is retired by the time-based matrix" or explain what still survives. | — |
| P8.5 | AITU | Write the session trail to `../progress/YYYY-MM-DD-time-based-concept.md` and add every new file to `context/00-index.md`. | — |

**Exit:** all six criteria recorded, docs consistent, index updated.

---

## Things to watch while executing

- **Do not measure on snapped columns.** Every phase has at least one place where it is tempting.
  P2.6 is the guard test; keep it.
- **P4.1 before P4.4.** Once the granularity leaves the path scheme, an un-inventoried hand-edited
  artifact is unrecoverable.
- **P6.9 after P4.5.** Deleting the old reader before the migration runs strands every stored score.
- **P6.7 (beaming) is a real open question**, not a formality. Beams group by beat and there is no
  beat.
- **40 ms is a guess.** It is right for segment A and coarse for the fast section. `frameMs` is
  configurable for exactly this reason — if fast passages look bad in P8.2, try 20 ms before
  changing anything structural.
