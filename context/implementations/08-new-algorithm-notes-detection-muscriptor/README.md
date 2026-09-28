# 08: MuScriptor, the live piano roll, and the move to Ubuntu

**State: in progress. Planned 2026-09-28, with all six decisions answered the same day. Phase 0 done 2026-09-28 ([`08-implementation-phase-0.md`](08-implementation-phase-0.md)); Phase 1 done on Ubuntu ([`08-implementation-phase-1.md`](08-implementation-phase-1.md)); Phase 2, the piano matrix notation format, done ([`08-implementation-phase-2.md`](08-implementation-phase-2.md)).** The brief is [`08-prompt.md`](08-prompt.md), the plan
is [`08-plan.md`](08-plan.md) and the status lookup is [`08-checklist.md`](08-checklist.md). Phase
reports go beside them as `08-implementation-phase-N.md`, following
[`../../language/communication-implementation-plans.md`](../../language/communication-implementation-plans.md).

| File | What it is |
|---|---|
| [`08-prompt.md`](08-prompt.md) | The brief, in the user's own words |
| [`08-plan.md`](08-plan.md) | The plan: MuScriptor, the piano matrix notation format, the flow page, revisions, the move to Ubuntu, ten phases |
| [`08-checklist.md`](08-checklist.md) | The status lookup, and the open decisions |
| [`muscriptor_paper.pdf`](muscriptor_paper.pdf) | The MuScriptor paper |
| [`examples/`](examples/) | Three screenshots of MuScriptor's own live piano roll visualization |
| [`measurements/`](measurements/) | Raw measurement files of the phases (Phase 2: the payload sizes and times of 34 pieces) |

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

The piano sheet page (`RhythmPage`) and the drawing package `vexflow-v2`. ByteDance and Transkun stay
in the code.
