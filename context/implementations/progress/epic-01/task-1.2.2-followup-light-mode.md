# Task 1.2.2 follow-up — the app is light, and pinned

Status: **agreed with the supervisor and applied** on 2026-07-27, reversing the dark-mode default
recorded in [`task-1.2.2-progress.md`](task-1.2.2-progress.md).

## What prompted it

The supervisor could not judge the Matrix tab's struck-vs-held distinction, and reported it as their
Mac and Chrome being in dark mode. It was not: the app's own theme was hardcoded `mode: "dark"`.

The consequence was worse than cosmetic. A struck note is `semantic.matrixOneHand.onset`, which is
`grays.ink` — and the page background was **also** `grays.ink`. A black circle on a black page. The
one distinction the Matrix tab exists to show was invisible, and had been since Epic 7.

The original reasoning ("the matrix grid, piano roll and falling views read better on a dark ground")
was never checked against the semantic colors those views actually use.

## The decision

**Light, always — not "light by default".** Sheet music is black on white, a piano matrix is black on
white, and every semantic color in `palette.ts` is a saturated brand shade or a near-black ink, which
is to say: chosen to sit on a light ground.

Three locks, because each covers a different failure:

| Lock | What it stops |
|------|---------------|
| `mode: "light"` in `theme.ts`, and no `prefers-color-scheme` branch anywhere | The app choosing dark |
| `color-scheme: light` in `index.css` and `MuiCssBaseline` | Chrome darkening scrollbars and native form controls under a dark OS |
| `<meta name="color-scheme" content="light">` in `index.html` | Chrome's Auto Dark Mode re-tinting the page, before any CSS loads |

None is sufficient alone. The meta tag matters most: it is read before stylesheets, so the first
paint is already light.

## The real fix underneath: `surface`

Flipping the mode alone would have moved the bug rather than removed it. Views were reaching for
`grays.charcoal` to draw a grid line and `grays.paper` to draw a label — hex-free, but still silently
encoding "we are on a dark ground". A second theme change would have broken them again.

So `palette.ts` gained a `surface` group whose names say **what the color is for**, not how dark it
is: `page`, `panel`, `line`, `strongLine`, `text`, `mutedText`, `blackKey`. Anything that has to read
against the page reads it from there, and changing ground is now one edit.

Repainted: `MatrixGrid`, `PianoRollPage`, `NotesFallingPage`, `WaveformView`, `LiveLevelBars`,
`renderScore`, and one stray hex in `PianoSheet` (`#17130d`, a lyric fill that predates the rule).

**Struck and held keep their colors exactly**, as the supervisor asked: onset `grays.ink`, sustain
`grays.silver`, hands dark/light Blue and Green. Nothing about the encoding changed — only the ground
it is read against, which is what makes it legible.

## Notable

`NotesFallingPage` was the one view with a genuine argument for dark: Synthesia-style falling notes
are conventionally light-on-black. Its lane is now `surface.panel` for consistency with the rest of
the app. If it reads worse in the trial, that is a real finding and the lane is one token to change
back — but it should be a deliberate exception, not a leftover.

## Verification

`tsc -b`, `eslint` and `npm run check:render` clean. Verified live in the supervisor's own
dark-mode Chrome at `localhost:5173`: Matrix (struck notes now solid black on white, black-key
columns as light bands, two-hands blue/green legible), Piano Roll, Notes Falling and Music Notation
all light, no console errors, and no re-tinting from the dark OS.

## For the next worker

- Never read a raw `grays.*` for something that sits on the page — use `surface`. `grays` stays for
  the few places a specific value is the point (a note's own color).
- There is deliberately **no** theme toggle. If one is ever wanted, `surface` is the seam: give it a
  second set of values and everything downstream follows.
- `src/App.css` is dead (nothing imports it) and still carries cream/beige hexes from the pre-MUI
  MVP. Worth deleting when someone is next in that area.
