# Task 9.2.1 — Notation tab UI · progress

Status: **done** on 2026-07-27. Renders, wraps, saves and promotes; awaiting the supervisor's trial.

## Delivered

| File | What it is |
|------|-----------|
| `music/scoreDocument.ts` | TS mirror of `schemas/notation.py`, plus the annotation overlay |
| `components/notation/renderScore.ts` | The VexFlow drawing, as a plain function |
| `components/notation/ScoreSheet.tsx` | React shell: host element, resize, guide clicks |
| `components/notation/PromoteDialog.tsx` | The Task 5.2.1 promotion dialog |
| `components/notation/KeySignaturePanel.tsx` | Passage key changes and per-measure suggestions |
| `components/notation/OctavePanel.tsx` | Ottava and clef-switch thresholds |
| `pages/playground/NotationPage.tsx` | The tab (was two placeholders) |
| `scripts/check-render.mts` | `npm run check:render` — headless render smoke test |

The tab picks an artifact, fetches its document and draws it. Everything else on the page is a
decision that changes what the *backend* builds: key signature, single hand vs grand staff,
transposition preview and accept, cut measure, annotation save, promote.

### Why the renderer is split in two

`renderScore.ts` is a plain `(host, document, options)` function with no React in it, because VexFlow
fails in two ways and only one of them is loud: a wrong modifier order throws, a wrong tick count
just draws nothing. Both end up as a blank tab. Splitting it out means `npm run check:render` can
draw every golden document under jsdom and assert real glyphs came out — which is how the ottava
brackets and mid-line clef changes got caught before a browser ever saw them.

### Responsive wrapping

Wrapping is by **measure**, and both hands wrap at the same measure, so a grand staff cannot drift
out of alignment. A `ResizeObserver` re-runs the same layout maths; nothing is stored in pixels. The
check script asserts that the same score in a 460 px window is taller than in a 1600 px one.

Simultaneous notes stay vertically aligned because both hands' voices are handed to **one**
`Formatter` per measure.

## Errors found and how they were solved

**MUI v9 dropped layout props.** `alignItems`, `flexWrap` and `useFlexGap` as direct `<Stack>` props
are compile errors now; they moved into `sx`. Already recorded in `09-coding-conventions.md`, and now
followed here.

**ESLint refuses `setState` in an effect body.** `PromoteDialog` cleared its error before fetching;
moved into the `.then` callback.

**`ScoreQuery` was not assignable to the client's `query` type.** An interface without an index
signature does not satisfy `Record<string, …>`; the query object is now built explicitly in
`notationApi.get`, which is clearer anyway.

**The overlay could be silently dropped.** Editing a key change posted the whole `annotations` block,
so anything the page had not loaded would have been wiped. Fixed by having the document echo its
annotations back (see Task 9.1.1) and seeding the editor from it.

## Changes made along the way

- The old `PianoSheet.tsx` is **kept, not replaced**. It still serves the text-notation MVP pages
  (`SequenceComposer`, `ScoreStack`), which render a `MatrixScore`, not a `ScoreDocument`. The new
  path is additive; retiring the old one belongs with those pages.
- Added `jsdom`, `tsx` and `@types/jsdom` as devDependencies for the render check. Run
  `npm install` before `npm run check:render`.

## Manual trial

[`user_review/epic-09-notation.md`](../user_review/epic-09-notation.md) — the whole guide, but
especially step 9.2 (resize the window) and step 9.7 (promote).

## For the next worker

- `ScoreSheet` reports guide clicks by hit-testing the guide positions `renderScore` returns; there
  are no DOM event handlers on the SVG itself.
- Lyrics and finger numbers render through VexFlow `Annotation` modifiers and are already wired to
  the overlay — Epic 12 needs an *authoring* UI, not a renderer.
- The page reads BPM and granularity from the shared working artifact, so changing them in the
  Matrix tab and coming back re-renders at the new settings.
