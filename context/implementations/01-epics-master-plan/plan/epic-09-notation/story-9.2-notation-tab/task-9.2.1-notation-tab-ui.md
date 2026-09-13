# Task 9.2.1 — Notation tab UI

`/playground/notation`: the sheet-music view. Builds on the existing `PianoSheet.tsx` VexFlow renderer.

## Subtask 9.2.1.1 — Artifact selection and render

Pick a saved artifact by name; frontend fetches only the pre-built score document (Task 9.1.1) and renders it. Two-hands = braced grand staff (treble above, bass below); toggle for single-hand mode.

## Subtask 9.2.1.2 — Responsive wrapping

Sheet wraps to browser width like text (no fixed page): reuse and harden the existing wrap logic (one-hand wraps by note count, two-hand by aligned time-window slices). All overlays (beat guides, annotations) must reposition on rewrap — no hardcoded absolute positions.

## Subtask 9.2.1.3 — Actions

- Save annotations (metadata only — matrices are not editable from this tab) into the version's `metadata.json`.
- Promote-to-library button opening the Task 5.2.1 dialog.

## Acceptance

Manual trial: render a saved two-hand piece, resize the browser window and verify clean rewrapping, then promote it.
