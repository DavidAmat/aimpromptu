> Context: [rendering-pipeline.md](../../../context/frontend/rendering-pipeline.md) · [02-notation-spec.md](../../../context/music/notation-logic/02-notation-spec.md)

# Grid notation

How sheet music is drawn. Replaces the VexFlow stack — `PianoSheet.tsx`,
`renderScore.ts`, `matrixToNotation.ts`, `notes.ts` and the backend-built
`ScoreDocument` are all gone.

## The package

[`@aimpromptu/grid-notation`](../../../../vexflow-v2/documentation/README.md) is a
local TypeScript package, developed in the sibling `vexflow-v2` checkout and
installed from disk:

```json
"@aimpromptu/grid-notation": "file:../../vexflow-v2"
```

npm turns that into a symlink, so editing the package and rebuilding it there is
picked up here — `pip install -e`, with one difference: **npm does not build the
dependency for you.** After any change in `vexflow-v2`, run `npm run build` (or
`npm run check`) there, or `dist/` stays stale.

`vite.config.ts` excludes it from `optimizeDeps` for the same reason: Vite
pre-bundles linked dependencies and caches the result.

### The stale-`dist` trap

This has bitten once and will bite again, so it is worth stating as a rule.
`dist/` is in the package's `.gitignore`, the symlink is live, and there is no
version anywhere in this app's lockfile. So what runs in the browser is
**whatever `dist/` was last built from** — and nothing warns when that is eleven
releases behind the source beside it. That is exactly what happened between
0.16.0 and 0.26.2: the package's git log said 0.26.2 while `dist/` was still
0.15.0, and the app quietly kept engraving with the old code.

Pulling the package is therefore never enough. Rebuild it, and if a documented
feature seems to be missing, check the build before checking the docs:

```bash
grep -c planAccidentalColumns ../../vexflow-v2/dist/index.d.ts   # 0.26.2
```

Useful markers, one per release worth dating: `suggestKeySignature` (0.16.0),
`FrameClock` (0.17.0), `StavesMode` (0.18.0), `planMerge` (0.19.0),
`renderScorePages` (0.25.0), `planAccidentalColumns` (0.26.2).

## Why it exists

VexFlow lays notes out from accumulated tick arithmetic inside measures. A piano
matrix has no measures and no metre — it has **frames**, and the one property the
whole project depends on is that a right-hand and a left-hand event in the same
frame print at the same x. Tick-based layout can only approximate that, and the
approximation drifts.

This package makes frame columns the horizontal source of truth: one
frame → x function, shared by both staves and the ruler. The hands cannot come
apart, because nothing computes their positions separately.

Two consequences worth knowing before reading a score:

- **Frames are not evenly spaced.** A frame is as wide as what it draws, so
  horizontal distance reads as *density*, not duration. Time is read from the
  frame labels, or by clicking one for the clock time.
- **The score re-wraps, it never scales.** A narrower window puts the music on
  more lines at the same size. Do not give the host `width: 100%` expecting it to
  shrink; let it scroll.

## What this app supplies

| File | Role |
|------|------|
| `src/music/gridNotation.ts` | The seam: `readEnvelope`, `patchesToCellEdits`, key-signature re-exports |
| `src/music/mergeOnsets.ts` | `planHostMerge` — a deliberate superset of the package's `planMerge` |
| `src/components/notation/GridScore.tsx` | React lifecycle around `GridNotationEditor` |
| `src/components/notation/ScoreReadingControls.tsx` | Bar lines and ties — reading aids, session-local |
| `src/api/notation.ts` | `/notation/artifacts`, `/{id}/matrix`, `/{id}/grid-state`, `/{id}/merge-onsets` |
| `src/pages/playground/NotationPage.tsx` | Artifact picker, starting key, transposition, printing, saving |

There is **no conversion layer**. The renderer reads the pipeline's own envelope
— `rMatrix`/`lMatrix`, `1` onset / `-1` sustain / `0` silence, the granularity
naming the frame length — which is why there is no score model in this app to
keep in step with the matrix.

## GridScore: the one rule

The editor owns real DOM and a lot of state — the selection, the open toolbox,
the scroll position, the transport. Build it **once per piece**, drive later
changes through its methods, destroy it on unmount.

Which is why its effect depends on the music and the starting key, never on the
callbacks: callbacks change identity on every parent render, and depending on
them would tear the editor down constantly. They live in a ref the effect reads
at call time.

The same reasoning applies upward: `NotationPage` keeps the renderer's live
annotations and edit patches in **refs**, not state. Feeding either back in as a
prop would rebuild the editor on every keystroke and close the toolbox the reader
is typing in.

## Where the UI went

Everything about *one score* now lives in the score, in a toolbox that opens
under whatever was clicked — lyrics, playing-style markings, fingering, key
changes, line breaks, note dragging, playback. The page keeps only what is not
about one score: which artifact, what key it starts in, transposition, saving.

Deliberately gone: `KeySignaturePanel` (now the score's Key tab), `OctavePanel`
(now its Octave tab), the measure-width slider and the beat-guide toggle. "Cut
measure" came back in a different shape — the Bars tab's *Downbeat is f n* plus
*Push to the next bar*.

What the page kept or gained, and why each is on the page rather than in the
toolbox — the toolbox opens on a *selection*, and all of these are about the
whole piece:

| Control | Notes |
|---------|-------|
| **Print** | `editor.print()`. The page is the screen re-wrapped to paper, never scaled — this app has no print path of its own and must not grow one |
| **Suggest octaves** | `applySuggestedOttavas()`, the old backend's own thresholds. A suggestion the reader accepts, not a rule; nothing sounds different |
| **Key suggestion** | `suggestKeyFor(0, frameCount)`. Reports the *saving*, never the raw count, and never applies itself |
| **Bar lines / ties** | `ScoreReadingControls`. Session-local; see below |
| **One staff** | In the Hand split card, next to the panel that raises the doubt it answers |

### Reading aids are not markup

Bar lines, ties and one-staff mode change the page and not a note of the music,
and none of them is stored. `GridScoreState` carries the reader's **markup** —
lyrics, fingering, key changes, spellings, ottavas — and a reading aid is not
that. Persisting one means a new field on that contract and therefore a backend
change; worth doing when someone asks, not before.

Two of the three apply live through `setStaves` / `setBars`. **Ties do not** —
the renderer has no runtime setter, so toggling ties rebuilds the editor and
drops the selection. Fine for something set once; check that before putting it
behind a control anyone would flick repeatedly.

### Inserting and removing frames

The score's Line tab offers *Insert silent frames* and *Remove frames*, and
these are the only edits that change **how long the piece is**. Everything this
app sends the backend is addressed by absolute frame index — a cell edit names a
frame, a merge names a target column — so once frames move, every pending index
means a different column.

There is no backend route for a structural edit yet, so `NotationPage` treats
one as a **stop**: `onMatrixStructurePatch` drops the pending cell patches,
disables saving and merging, and says the on-screen piece and the stored matrix
no longer agree. Reloading is the way out.

Note the package does *not* hide these buttons when the callback is absent,
though decision D39 says a host that cannot handle them "simply does not offer
the gesture". Wiring the callback is not optional here — leaving it off means
the numbering drifts silently and the next save writes to the wrong frames.

## Persistence

Two things come out of a session and they are stored separately:

| What | Where | How |
|------|-------|-----|
| The music | The matrix itself | `onMatrixPatch` → `patchesToCellEdits` → `POST /matrix/{uuid}/edit` |
| Everything else | `grid-notation.json` beside the matrix | `PUT /notation/{id}/grid-state` |

Keeping them apart is what lets the transcription pipeline be re-run without
losing the reader's markup. The annotation envelope is stored **verbatim**: it
belongs to the package, is addressed purely by matrix indices, and is documented
as additive, so a key this app has never heard of must survive a round trip.

Note edits are held until asked for rather than written per drag: a pitch change
is a real edit to the transcription, the same one the Matrix tab makes, and it
re-derives every granularity below it. A saved version is immutable, so it is
offered for the working artifact only.

## Merging a splintered chord

When the transcription hears one note of a chord a fraction of a beat early, it
gets its own column and prints as a stray short note in front of the chord.

The package validates this but **never performs it** (decision D35): the
correction belongs in the transcription's *seconds*, which the package never
sees, because a merge written into the grid is thrown away by the next
re-quantisation. So there are two routes in and both end at
`POST /notation/{id}/merge-onsets`:

- the score's own **Merge onto f*n*** button → `onMergeRequest` → one candidate;
- the **Merge notes** panel → `planHostMerge` → one plan, possibly per hand.

`planHostMerge` is not a duplicate of the package's `planMerge` and is named
differently to say so. It is a superset: the package rejects a selection
spanning both hands and returns onsets and a span, while this plans each hand
independently and carries the **rows**, which is what the endpoint needs to name
the notes that move. The one rule shared exactly is the refusal to merge across
an *unselected* onset — that silently reorders the passage, and it is the rule a
host is most likely to forget.

## The clock

`timeStepSeconds` is the piece's nominal seconds per frame and stays
authoritative. For a performance whose tempo is not constant the renderer also
takes `frameTimestamps`, and every conversion it makes then follows that map
rather than multiplying (decision D32). `readEnvelope` already returns it, and
`GridScore` passes it through.

**Today it changes nothing, and that is worth knowing rather than discovering.**
The backend's `dense_row_timestamps` generates `i * time_step_seconds` — uniform
by construction — so the map and the scalar agree exactly. A real tempo map
would have to come from re-quantising against one, which nothing does yet. The
wiring is in place for when it does.

Elsewhere in the app — `playback/matrixNotes.ts`, `playback/useMatrixPlayback.ts`,
`hooks/usePianoViewData.ts` — frames are still converted to seconds by hand.
That is fine while the clock is uniform. The day a tempo map exists, those and
the score will start disagreeing about when a frame happens, and the fix is to
route them through the renderer's `frameClock` rather than to add a second map.
