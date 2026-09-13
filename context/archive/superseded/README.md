# Superseded context documents

Moved here on 2026-09-13 by Task 14.1.1. Every file in this folder describes a model or a screen
the app no longer has. They were kept rather than deleted because they are the record of what we
moved away from, and several plan documents still cite them.

**Nothing here is current.** Where a file said something that is still true, this page says where
that truth now lives.

| File | What it described | Where the current answer is |
|---|---|---|
| [01-matrix-notation-logic.md](01-matrix-notation-logic.md) | Column timing computed from a BPM, duration approximation against a figure grid, the collapse and clean steps | [`documentation/services/backend/events-to-sheet.md`](../../../documentation/services/backend/events-to-sheet.md) |
| [03-editing-logic.md](03-editing-logic.md) | Hand-editing a range of matrix cells — a screen deleted in P4.2 | Editing happens on the drawn sheet: [`documentation/services/backend/rhythm-and-annotations.md`](../../../documentation/services/backend/rhythm-and-annotations.md) |
| [app-shell.md](app-shell.md) | `App.tsx` fetching `/scores` into global layout state | [`context/frontend/pages.md`](../../frontend/pages.md) |
| [loaded-scores.md](loaded-scores.md) | `ScoreStack` and `LayoutControls` | Deleted with the VexFlow stack; no equivalent — the score re-wraps rather than being scaled |
| [compose-panel.md](compose-panel.md) | `SequenceComposer`, the text-notation entry point | Deleted in P4.2. A piece now starts from a recording, or from **Compose** — [`context/backend/editing.md`](../../backend/editing.md) |
| [rendering-pipeline.md](rendering-pipeline.md) | `matrixToNotation.ts` → `PianoSheet.tsx` (VexFlow) | [`context/frontend/rendering.md`](../../frontend/rendering.md) |

## The two that carried something still true

**`01-matrix-notation-logic.md` — Appendix B and the wire format.** Appendix B is the sustain rule:
a sustain dies when any other key is struck on that hand. It is still in force and still
implemented, in `aitu-backend/src/aitu_backend/matrix/cleaning.py`. The sparse-COO wire format —
parallel `rows` / `cols` / `onset` arrays, `1` onset, `-1` sustain, `0` silence — is also unchanged
and is now specified in
[`documentation/services/backend/time-matrix.md`](../../../documentation/services/backend/time-matrix.md).

Everything else in that file starts from a BPM and does not.

**`compose-panel.md` — the name.** "Compose" means something different in the app today: building a
piece passage by passage from recordings, not typing text notation. The word was reused
deliberately, and the two have nothing else in common.
