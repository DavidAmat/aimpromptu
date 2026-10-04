# Task 7.4.1 — Cell editing · progress

Status: **done and browser-verified** on 2026-07-27.

## Delivered

- Matrix edit mode with onset/sustain palette.
- Empty-cell placement and active-cell selection; Shift adds/removes cells from a multi-selection.
- Delete uses the engine rule that removing any part of a note removes its onset and sustain tail.
- `POST /matrix/{audioUuid}/edit` previews the complete staged edit list through the backend
  primitives. Illegal sustains return the domain reason and do not change the preview.
- Save expands the edited view back to the canonical fusa source, updates every Playground tab,
  and keeps the first untouched transcription in `raw_before_edit.npz`.
- Cancel reloads the persisted working matrix.

## Error found

The browser exposed concurrent recomputes writing the same scipy `.npz` file. One request could
read the other request's half-written zip archive. Matrix storage now writes a sibling temporary
file and atomically replaces the destination; a storage test locks that behavior.

## Verification

- Backend edit API tests cover preview, orphan-sustain rejection, tail deletion, persistence,
  parent retention, and coordinate/value validation.
- Browser trial added an onset to the imported five-note scale, saw the staged badge, saved it,
  and loaded the result in the other views without console errors.

## Supervisor trial

Record slow `Do Re Mi Fa Sol` negras at 60 BPM. In Matrix, add an obviously wrong note, Save, and
open Piano Roll to confirm it is present. Return to Matrix, select it, Delete, Save, and confirm it
has disappeared everywhere.
