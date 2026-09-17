# 04 — Synthesia to notes

Opened 2026-09-13. Live.

Read a piano roll video — the Synthesia kind, where rectangles fall onto a keyboard — and produce the
same `events.json` the transcription model produces, so the whole app after that point is unchanged.
For this family of YouTube videos the notes are drawn on the screen on purpose, so we read them
instead of guessing them from the sound.

| File | What it is |
|---|---|
| [`04-prompt.md`](04-prompt.md) | The brief this plan answers, in the user's own words |
| [`04-plan.md`](04-plan.md) | The plan: what is built, in five phases |
| [`04-decisions.md`](04-decisions.md) | V-01 to V-43, frozen. A task may not reinterpret one. V-09 is superseded by V-37 |
| [`04-checklist.md`](04-checklist.md) | The status lookup |
| [`examples/`](examples) | 24 screenshots covering the different ways these videos draw a rectangle |
| [`04-phase-1-implementation.md`](04-phase-1-implementation.md) | Phase 1, Research: the survey, the catalogue, the five detectors, the scroll speed |
| [`04-phase-2-implementation.md`](04-phase-2-implementation.md) | Phase 2, Evaluation: the detector in the app, the annotation page, the score board |
| [`04-phase-3-implementation.md`](04-phase-3-implementation.md) | Phase 3: a real video downloaded, sampled, calibrated, measured and read into `frames.jsonl` |
| `04-phase-X-implementation.md` | One report per phase, written when the phase closes |
| [`../../../poc-synthesia-frames/`](../../../poc-synthesia-frames) | Phase 1's research spike: the scripts, the pictures and `RESULTS.md` |

**Story 2.1, the piano overlay, is replaced by
[`../05-piano-overlay-from-black-keys/`](../05-piano-overlay-from-black-keys/README.md)** (opened
2026-09-14): one rotatable rectangle over the piano area, every key found inside it, and a
`Calibration` of per-key borders. Everything else in this folder stands.

The wall-clock model is still binding: the five rules in
[`../01-epics-master-plan/plan/wall-clock-rewrite.md`](../01-epics-master-plan/plan/wall-clock-rewrite.md)
and D-01 to D-34 in
[`../03-time-based-concept/decisions.md`](../03-time-based-concept/decisions.md). Nothing in this
folder changes one of them.

Reports are flat files in this folder, `04-phase-X-implementation.md`, rather than a `progress/`
subfolder. That is what
[`../../language/communication-implementation-plans.md`](../../language/communication-implementation-plans.md)
asks for, and it is the newer instruction.
