# Task 9.6.1 — Beat guides and cut-measure · progress

Status: **done** on 2026-07-27, including the doc's exact Do-Re-Mi-Fa example as a test.

## Beat guides (9.6.1.1)

The document carries a `BeatGuide` per beat: its column, its measure, whether it opens the measure,
and its wall-clock time. The spacing follows the **time signature's** beat, not the granularity — a
6/8 measure counts corcheas, so its guides sit one corchea apart. When a beat is not a whole number
of columns the guides fall back to one per barline rather than drawing a half-column line.

The renderer places them by interpolating between the stave's note start and end for that measure, so
they land correctly at any width and survive a re-wrap. Measure starts are skipped — the barline
already marks those. Frame numbers are drawn above the top stave, subtle gray, dashed, toggleable.

Dashes are drawn by hand as short segments because the VexFlow SVG context does not expose
`setLineDash`.

## Cut measure up to here (9.6.1.2)

`POST /notation/{artifact}/cut-measure` with the clicked column. It computes how far that column is
into its measure and inserts exactly enough timeline columns to push it to the next barline — which
is Task 2.4.2 tempo insertion, not a notation-only trick. The inserted matrix cells are silent
padding, but the score's onset-led duration rule extends the preceding note/chord across them rather
than drawing a rest in the middle of the music. The edit round-trips through the canonical raw
resolution the same way a grid edit does, and `persist_edited_raw` keeps the pre-edit raw.

The doc's example is the test: a 4/4 measure of Do Re Mi Fa as negras, cut at the Mi, gives
`Do Re Mi(blanca) | Fa …`. One column is inserted in the timeline, the printed Mi expands to the
old barline, and two measures come out without a visible middle rest.

Refused in two cases, both with a readable message:

- **the column already starts a measure** (422) — there is nothing to cut;
- **the artifact is a saved version** (409) — those are immutable; load it in the Playground, cut
  there, save a new version.

In the tab it is a **Cut measure up to here** toggle; with it on, the sheet becomes clickable and a
click near a dashed guide opens a confirmation naming the frame.

## Re-render (9.6.1.3)

The endpoint returns the rebuilt document with the result, so the new barring appears without a
second request. The page also bumps its revision so any later fetch bypasses the cache.

## Errors found

The click target needed hit-testing rather than DOM handlers: the guides are drawn onto the canvas,
not as elements. `renderScore` returns the guide positions it drew and `ScoreSheet` matches a click
within 10 px — which also means the tolerance is one number to tune, not a layout change.

## Manual trial

[`user_review/epic-09-notation.md`](../user_review/epic-09-notation.md) step 9.9 — play
`Do Re Mi Fa` as slow negras at 60 BPM, cut at the Mi, and confirm Mi expands to the barline and Fa
opens a new measure, with no rest printed between them. This is the doc's own example end to end.

## For the next worker

Only a working artifact can be cut. Doing the same to a saved version means loading it into the
Playground first — that path exists (Epic 6 input sources) but is not wired as a one-click "edit this
version" button anywhere yet.
