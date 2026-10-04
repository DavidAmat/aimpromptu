# Task 10.2.1 — Performance view · progress

Status: **done** on 2026-08-13.

## What was implemented

`/library/play/:id` is the music stand. It loads the same time-score payload the Rhythm tab asks
for, with the saved rhythm applied: ladder, passages, key, overrides, beam breaks, fingerings. A
piece nobody has named yet still draws, using the biggest gap pile as a negra, so the stand is not
empty.

Editing is gone. `TimeScoreView` takes `readOnly`: note picking and the marked stretch are off, and
pointer events on the SVG are turned off so the ruler cannot start a selection either. The playhead
stays a sibling overlay and can still be dragged.

Overlays are pills: fingering, lyrics (disabled until Epic 12), tuplet & trill marks, dashed
guides. PDF is the same dialog the Rhythm tab uses. `ScorePlayer` is on the page, so Space plays
and pauses and the scrub bar seeks.

Back to the library is always there. **Next** appears when the URL carries `?playlist=` and
`index=`, and walks the playlist one piece at a time (Story 10.3 stores the list).

A promotion flagged `needsRederivation` still cannot open, same as 10.1.

## Errors found

The first `PerformancePage` draft set state in an effect that also owned the track, which tripped
`react-hooks/set-state-in-effect`. The page is now three components: one fetches the track, one
draws the stand, one resolves Next. Each effect writes only its own state.

## Deviations

No cached score file. Deriving on request is what the Rhythm tab already does; a second stored
payload would disagree with `events.json`. If a long piece is too slow later, cache beside the
version then — not now.

Tuplet & trill marks currently hide tresillo brackets (`tupletFor`). Trill marks themselves land
with Task 9.7.2, which is on another branch.

## Manual trial

1. Promote a playground piece that has a saved rhythm. Open it from Ready to play.
2. Confirm there is no toolbox, no marked stretch, no Save bar. Clicking a note does nothing.
3. Toggle fingering off and on. Toggle guides. Lyrics stays disabled.
4. Play from the middle of the scrub bar; Space pauses. Export PDF.
5. Open a piece flagged `needsRederivation` by URL — the warning, not the sheet.

## For the next worker

Play ids are still `artistSlug--trackSlug` with `?promotion=`. Playlist Next is
`?playlist=<slug>&index=<n>`. Loader: `aitu-frontend/src/library/loadPerformanceScore.ts`.
Excerpts (10.3.1.3) were skipped.
