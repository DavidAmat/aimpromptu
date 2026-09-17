# 06 — Phase 3: the documentation and the checks

Technical report. The plan is [`06-plan.md`](06-plan.md), the status lookup is
[`06-checklist.md`](06-checklist.md).

## 1. The pages changed

| File | What was added |
|---|---|
| `context/frontend/annotations.md` | A **Taking it back** section: the keys, one press is one step, and the table of the four edits that write to the recording with a yes for the hand swap and a no for the other three. **Space between lines** in the whole-piece list |
| `context/frontend/rendering.md` | **How far apart the lines are** — why it is a control rather than a constant, and that it is vertical and so nowhere in the `time → x` map |
| `documentation/services/frontend/grid-notation.md` | `systemGap` in the options table; why it goes through `setSystemGap` and never through the build; why the gap effect is written above the playhead effect; the release marker and 0.33.0 |
| `documentation/services/backend/rhythm-and-annotations.md` | `line_spacing` in the field table and its paragraph; a new section 4, **Taking an edit back**; sections renumbered |

Two corrections to prose that was already wrong, made while passing:

- `grid-notation.md` said "`RhythmPage` keeps live annotations in refs rather than state". It never
  did — `live` is a `useMemo` — and after Phase 1 the accurate statement is that the edits are one
  object behind `useEditHistory` whose setters keep a constant identity, which is the property that
  matters for the same reason the old sentence was trying to name.
- `annotations.md` had the four recording-writing edits under a heading saying "three things".

`00-index.md` needed no change: no file was added or removed under `context/`, and both pages stay
under the ~200-line guidance (141 and 114).

## 2. Every check, and what it says

| Where | Command | Result |
|---|---|---|
| `vexflow-v2` | `npx vitest run` | **404 passing.** One pre-existing failure, `_to_delete/p63-deleted/bars.test.ts`, which imports a `../src` that is not there |
| `vexflow-v2` | `npm run build` | Clean; `dist/index.d.ts` carries `setSystemGap` |
| `aitu-frontend` | `npx tsc -b` | Clean |
| `aitu-frontend` | `npm run lint` | Clean — zero errors, zero warnings |
| `aitu-frontend` | `npm run build` | Clean |
| `aitu-frontend` | `npm run check:render` | **30 passing**, up from 26 |
| `aitu-frontend` | `npm run check:history` | **20 passing**, new |
| `aitu-backend` | `uv run pytest` | **884 passing.** One failure, `test_the_worked_example_at_00_46_prints_three_equal_corcheas`, documented in `04-local-development.md` as pre-existing on a clean checkout |
| `aitu-backend` | `make lint` | One failure, `events_to_matrix.py:68 E402`, on a file this work never touched and which `git status` shows unmodified. The two files this work changed lint clean |

Both pre-existing failures were confirmed as such rather than assumed: the E402 file is unmodified
in `git status`, and the worked-example test is named in the local-development troubleshooting table.

## 3. Driven against the running services

`make serve`, then on the demo piece `classical-mix`:

- **The spacing round trip.** `PUT …/rhythm` with `lineSpacing: 72` → `200`; `GET` → `72.0`.
- **The hand swap, and its undo.** A right-hand note at column 6, row 51 sent to the left hand
  renamed **2 neighbouring notes** — the D-14 effect, exactly as the documentation says — and the
  undo call restored the whole score identically: every note's hand, column, row and figure.

The test reading was deleted afterwards (`DELETE …/rhythm` → `204`, `GET` → `404`), so the demo
piece is as it was found.

## 4. What no check here covers

There is **no browser driver on this machine**, so nothing automated pressed Command-Z, dragged the
slider, or looked at a real page. What is covered is every layer under that:

- the history's bookkeeping, as a pure reducer (`check:history`);
- the drawing's response to the gap, in the package's own suite and again at the app's seam in
  jsdom (`check:render`);
- the two backend routes an undo and a save depend on, against the running server.

What is left is the click-through, which is in the walkthrough as a human step.
