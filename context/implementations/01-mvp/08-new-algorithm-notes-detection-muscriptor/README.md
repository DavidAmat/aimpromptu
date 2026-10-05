# 08: MuScriptor, the live piano roll, and the move to Ubuntu

**State: complete, 2026-10-01.** Planned 2026-09-28 (seven decisions, Q-1 to Q-7, all answered).
Phase 0 on the Mac (2026-09-28), then Phases 1 to 9 on the Ubuntu machine (2026-09-28 to
2026-10-01): MuScriptor measured, the piano matrix notation format, the containers and the tunnel,
MuScriptor in the backend with the live stream, the piece API and revisions, the flow page with its
five tabs, and Phase 9's checks, documentation and the removal of the old Piano Roll tab
([`08-implementation-phase-9.md`](08-implementation-phase-9.md)). Nothing is left
to do. The brief is [`08-prompt.md`](08-prompt.md), the plan
is [`08-plan.md`](08-plan.md) and the status lookup is [`08-checklist.md`](08-checklist.md). Phase
reports go beside them as `08-implementation-phase-N.md`, following
[`../../../language/communication-implementation-plans.md`](../../../language/communication-implementation-plans.md).

| File | What it is |
|---|---|
| [`08-prompt.md`](08-prompt.md) | The brief, in the user's own words |
| [`08-plan.md`](08-plan.md) | The plan: MuScriptor, the piano matrix notation format, the flow page, revisions, the move to Ubuntu, ten phases |
| [`08-checklist.md`](08-checklist.md) | The status lookup, and the decisions |
| `08-implementation-phase-0.md` to `-phase-9.md` | One report per phase, for the agents of later phases |
| [`muscriptor_paper.pdf`](muscriptor_paper.pdf) | The MuScriptor paper |
| [`examples/`](examples/) | Three screenshots of MuScriptor's own live piano roll visualization |
| [`measurements/`](measurements/) | Raw measurement files of the phases (Phase 2: the payload sizes and times of 34 pieces; Phase 3: CPU against GPU; Phase 4: the stream; Phase 5: the saved hands and the routes; Phase 7: the frame times of the Notes tab; Phase 8: a hand move on the piano sheet; Phase 9: the whole flow on three pieces) |

## What it is for

The app's transcription (ByteDance by default) is replaced by MuScriptor, run on the RTX 4090 of the
Ubuntu machine. The notes appear on the piano roll visualization while the transcription runs. The
user then edits the rectangles, predicts the hands and corrects them on the same view, and only then
opens the piano sheet. One flow page with five tabs (Source, Audio, Notes, Hands, Sheet) replaces the
loose Playground tabs as the way in, and revisions stop an old piano sheet from being shown after a
change.

Before any of that, the project moves from the Mac mini to the Ubuntu machine, into containers, and is
opened from the Mac through one SSH tunnel.

## What it does not touch

The piano sheet page (`RhythmPage`) is used as it was, given the piece by the flow page; its hand
move was made faster, and one bug of the drawing package `vexflow-v2` was fixed (an octave bracket
over several lines). ByteDance and Transkun stay in the code.

## Where the result is documented

[`context/backend/muscriptor.md`](../../../backend/muscriptor.md) (the engine),
[`context/backend/pieces-and-revisions.md`](../../../backend/pieces-and-revisions.md) (the steps and
revisions), [`context/backend/piano-matrix-notation.md`](../../../backend/piano-matrix-notation.md) (the
format), [`context/frontend/flow-page.md`](../../../frontend/flow-page.md) (the flow page),
[`context/04-local-development.md`](../../../04-local-development.md) and
[`context/02b-local-setup.md`](../../../02b-local-setup.md) section 12 (the containers and the tunnel).
