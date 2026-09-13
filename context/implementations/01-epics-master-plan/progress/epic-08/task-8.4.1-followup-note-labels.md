# Tasks 8.2.1 / 8.4.1 follow-up — readable note labels

Status: **requested by the supervisor and applied** on 2026-07-27, after reviewing the Notes
Falling view on the new light theme.

> **A green "struck" key colour was built and then removed the same day**, at the supervisor's
> request. Every sounding key is Blue again, as it was. The reasoning and what was reverted are at
> the end of this report, so the idea is on record if it ever comes back.

## What was wrong

The label inside a falling rectangle was drawn at a fixed 10 px, anchored near the top, whatever the
rectangle measured. On a semicorchea that meant `Sol#-3` written straight across three neighbouring
notes — the screenshot the supervisor sent is unreadable in the busy passages. Three separate faults
in one line of code: the size ignored the box, the anchor ignored the centre, and nothing clipped.

## The fix: `piano/noteLabel.ts`

Fitting is now a decision with a rule, not a constant. Two directions constrain the type — `length`
runs along the note (its duration on screen) and `thickness` across it (the key's width) — and the
label is chosen in two passes over three candidates, fullest name first:

| Pass | Rule |
|------|------|
| Comfortable | The fullest name that still reaches 8 px |
| Cramped | Nothing was comfortable, so the fullest name that reaches 6 px at all |

Candidates are `Sol#-3` → `G#3` → `G#`: a short rectangle loses its octave before it loses its
pitch, because the pitch is what a player reads at a glance.

The resulting ladder, at a 22 px key width:

```
len   6-12   (blank)          — an empty box is honest; a lie across three neighbours is not
len  16      G#     @  8px    — very short: English abbreviation
len  20      G#3    @  8px
len  26      G#3    @ 11px
len  34      Sol#-3 @  8px    — shrink before abbreviating
len  45      Sol#-3 @ 11px
len  60+     Sol#-3 @ 12px    — the cap; always aimed for
```

The two passes are what make this behave. With only the "fullest name wins" rule, a 34 px rectangle
would take `Sol#-3` at 6 px — technically fitting, practically unreadable — instead of `G#3` at 8 px.
With only "biggest size wins", every rectangle would show `G#` and the octave would never appear.

Also applied to the **Piano Roll**, which had the same problem in milder form: it guarded with
`width >= 38` and drew a fixed 10 px, so it never overflowed but silently dropped every label on a
short note that could have carried one.

## Centring and borders

Labels are now `textAnchor="middle"` + `dominantBaseline="central"` about the rectangle's true
centre, with the falling view's rotation applied about that same point. Measured in the live DOM,
the offset from centre is `0.0, 0.0` on every rectangle.

Borders went from `1` to `2` and from `surface.mutedText` to `surface.text` (`#151515`), as asked.
Staged (dragged) notes keep their heavier warning outline so the distinction survives.

## Verification

`npm run check:render` gained a **label fitting** section, because this failure is invisible to a
type checker — every note name is a valid string at every font size — and invisible to a screenshot
of a simple scale. It asserts, at every rectangle length a real piece produces, that the drawn
extent never exceeds the box and the type never exceeds the thickness.

Verified live in the browser too: measured in the DOM, 0 of the rendered labels overflow, all are
centred to within 0.1 px, borders read `#151515` at width 2, and short rectangles carry `C4`/`D4`
rather than `Do-4`.

## The green "struck" colour, built and reverted

Briefly, the keyboard drew a **struck** key in light Green and a merely **held** one in Blue — the
matrix's `1` versus `-1` made visible, on the theory that a performer needs "play this" separated
from "keep holding it". The supervisor tried it and asked for it out: every sounding key is Blue
again.

Removed cleanly rather than left disabled — a dormant prop is a trap for the next reader:

- `Piano` lost its `onsetKeys` prop and is back to one overlay per sounding key.
- `useMatrixPlayback` lost `onsetKeys` / `sustainedKeys`; `pressedKeys` is again the only output.
- `soundingKeysByState` deleted from `matrixNotes.ts`.
- `public/piano/onset-white-key.svg` and `onset-black-key.svg` deleted, so the illustrator
  replacement set stays the original **two** overlay files.
- The check script's "struck vs held" section removed with it.

If the idea returns, the whole of it was one pure function splitting sounding notes by whether the
playhead sits inside the note's first frame, plus a second overlay asset per key type.

## For the next worker

- `fitNoteLabel` is pure and has no React in it; reuse it anywhere a name has to go inside a box.
- `CHAR_WIDTH_RATIO` (0.58) is an estimate of Inter's advance width. If the font changes and labels
  start looking tight, that constant is the dial — not the padding.
- The falling lane's very short rectangles are deliberately blank. If that reads as "missing data"
  rather than "too short to label", the alternative is a tooltip, not smaller type.
- The keyboard has **one** highlight colour. Do not reintroduce a second one without asking; it was
  tried and rejected.
