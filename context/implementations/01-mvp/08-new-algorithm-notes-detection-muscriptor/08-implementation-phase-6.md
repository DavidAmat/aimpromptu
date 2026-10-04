# 08 Phase 6: The flow page, the Source tab and the Audio tab

The plan is [`08-plan.md`](08-plan.md) sections 7, 9.2 and 9.4, and section 12, Phase 6. The status
lookup is [`08-checklist.md`](08-checklist.md). This report is for the agents of later phases: what
was built, the choices made inside the phase, the measurements, and what Phases 7 to 9 must know.

# 1. What was done

| Task | Result |
|---|---|
| 6.1.1 route | `/piece/new` (Source only), `/piece/:uuid` (opens on `resume`), `/piece/:uuid/<step>`; `/` goes to `/piece/new`; `/piece` (the new first top-bar entry **Piece**) opens the working piece or a new one. `main.tsx` now creates a data router (section 2.1) |
| 6.1.2 tabs | `components/piece/StepTabs.tsx`: numbered tabs with a state icon (ready, running, stale, missing), enabled from `steps[i].enabled`, tooltip `steps[i].reason`. A tab that is not enabled is greyed and ignores the press (not MUI `disabled`, so its tooltip still shows). A step typed in the address that is not enabled redirects to `resume` |
| 6.1.3 resume | `pages/piece/PieceResume.tsx` follows the backend's `resume`. `b99bc3ae` opens on Sheet, `a585f9eb` on Notes, a new audio on Audio |
| 6.1.4 save bar and guard | `components/piece/SaveBar.tsx` (the `FloatingBar`), `useUnsavedChanges(summary, {save, discard})` in `pages/piece/pieceContext.ts`. `useBlocker` asks on any in-app navigation (Stay / Discard / Save and continue); `beforeunload` while something is unsaved |
| 6.2.1 Source | `pages/piece/SourceTab.tsx`: the library (`AudioLibraryList`, opens `/piece/<uuid>`), YouTube, upload (both open `/piece/<uuid>/audio`) |
| 6.2.2 YouTube job | Backend `POST /youtube/jobs` (202, `{jobId, status}`), URL checked before the job (422), key `youtube:<url>`; `youtube.download` has a new `store` stage around the conversion; the `done` frame carries `audioUuid`, `alias`, `durationSeconds`. Frontend `components/piece/YouTubeDownload.tsx`; `useProgress` gained `result` (the `done` payload) |
| 6.3.1 waveform | Backend `GET /audio/{uuid}/frames/peaks` (`frames.frame_peaks`). Frontend `components/audio/CutWaveform.tsx` (two stacked canvases and an overview), painters in `waveformPaint.ts`, the view window in `audio/frameView.ts` |
| 6.3.2 edits | `audio/cuts.ts` (pure, the backend's `normalize_cuts` rules), `useEditHistory<{cuts}>` for undo and redo, `npm run check:cuts` (22 checks) |
| 6.3.3 playback | `audio/useCutPlayer.ts`: the original file in an `Audio` element; **Play all** jumps over the page's current cuts, **Play selection** plays the frames selected, cut or not |
| 6.3.4 save and transcribe | `pages/piece/AudioTab.tsx`: `PUT /audio/{uuid}/cuts` with `baseRevision`; **Transcribe** saves first, `POST /matrix/transcribe` (`force` only for current notes, after a confirmation), refreshes the status and opens the Notes tab |
| 6.3.5 Input page | `TranscriptionSettings` has no engine state, no engine field and sends no `engine`; it warns when MuScriptor is not installed. The Input page shows one line pointing to the **Piece** page |

Also new: `pages/piece/PiecePage.tsx` (the flow page), `PieceIndex.tsx`, `LaterStepTab.tsx` (Notes,
Hands and Sheet until Phases 7 and 8, section 2.6), `api/pieces.ts` (`piecesApi.status`, the types),
`audioApi.cuts`, `saveCuts`, `framePeaks`, `matrixApi.activeJob`, `youtubeApi.startDownload`,
`scripts/check-flow.mjs` (`npm run check:flow`, section 3.1).

Checks: frontend `tsc -b`, `npm run lint`, `npm run build`, `check:render`, `check:history`,
`check:note-names`, `check:geometry`, `check:cuts`, `check:flow` all pass. Backend: 6 new tests
(`test_audio_frames.py` 3, `test_youtube.py` 3); `make test-backend` in the container: 1,034 passed, 1
failed (the known `test_the_worked_example_at_00_46_prints_three_equal_corcheas`, Phase 0 report
2.1). `black`, `flake8` and `mypy` clean on the changed backend files. Screenshots of the old pages
(Input, Piano Sheet of `b99bc3ae`, Library, YouTube) under the new router: no console error.

# 2. Choices made inside the phase

## 2.1 A data router, for the guard

The plan asks the page to ask before the reader leaves a tab with unsaved edits. React Router's
`useBlocker` does this for every in-app navigation (tabs, top bar, back button), but only under a
data router; `<BrowserRouter>` cannot block. `main.tsx` therefore creates `createBrowserRouter` with
one route, `path: "*"`, whose element is `WorkingArtifactProvider` and `App`. `App`'s `<Routes>` are
unchanged and are descendant routes of that splat route. No page changed.

A navigation the page makes itself right after a successful save passes
`{ state: SAVED_NAVIGATION }`, which the blocker lets through: the summary state is cleared by an
effect, one render later than the save.

## 2.2 One waveform request, per time frame

The plan (section 9.4) proposed asking for more points in the visible range when zooming in. One
pair of values per 10 ms time frame for the whole audio is only 2 bytes per frame, so
`GET /audio/{uuid}/frames/peaks` sends all of it once (signed bytes scaled so the loudest sample is
127, base64) and every zoom is drawn from memory. The frames are those of `normalized.wav`, the same
count as `GET /audio/{uuid}/cuts` (`frame_count`), so frame `f` of the waveform is frame `f` of a
cut. No cache: the route reads the WAV each time (section 3.2).

## 2.3 The Audio tab shows the original audio

The waveform is the original audio with the cuts drawn on it (shaded and crossed, with their length
as a label), not the piece with the cuts removed. This is what lets the reader see and restore a cut.
All frames on this tab are frames of the original audio; the piece's frames appear only as the
"Selected region" length.

## 2.4 The gestures (changed after the user's first check)

The first version moved the playhead on every single click in the waveform and grabbed a selection
edge only within 6 px, with nothing drawn to show it. The user found it buggy: a click meant to clear
the selection could start a new one, the selection sometimes kept following the pointer after the
button was up, and the edges were hard to grab. Each place now has one job:

- **The time ruler** (26 px at the top) holds the playhead, drawn there as a handle. A press moves
  the playhead, a drag moves it along. A **double-click** anywhere also moves it; the first click of
  the double-click clears the selection, so the double-click puts the selection back.
- **A single click** in the waveform never moves the playhead: it clears the selection, or inside a
  cut selects the whole cut (Restore is then one click away). Shift-click stretches the selection.
- **A drag** selects `[round(min), round(max))`, at least one frame, once the pointer moved 4 px.
- **The edges** carry a grip in the middle of the waveform, and a press within 10 px on either side
  of an edge grabs it; the other edge stays. The hovered or dragged edge is drawn wider, with its time
  beside it. A drag past the side of the view scrolls the view, so an edge can be placed precisely
  while zoomed in. **Zoom to the selection** frames it with a margin of a fifth of its length; the
  zoom buttons zoom around the selection, else the playhead.
- **A press never stays stuck.** A move with no button down ends the press, as does losing the
  pointer capture, and Control-click (a Mac's right click, whose menu takes the release) is ignored.
- Command or Control and the wheel zoom around the pointer, which also covers a trackpad pinch (the
  browser sends it as a wheel event with `ctrlKey`). A sideways swipe, or Shift and the wheel, pans. A
  plain vertical wheel scrolls the page. The narrowest view is 50 frames (0.5 s).
- Keys: Space play or pause (`useSpacebarPlay`), Delete or Backspace, Command-Z, Shift-Command-Z,
  Command-Y, Escape clears the selection.
- The playhead follows playback: when it crosses the right edge of the view, the view turns one page.
  Only on that crossing, so a reader who moved the view elsewhere is not pulled back.

`check:flow` checks each of these (29 checks with the transcription).

## 2.5 Playback over the cuts

`useCutPlayer` checks the position on each animation frame and jumps 2 frames (20 ms) before a cut
starts, so at most a few milliseconds of a cut are heard. A browser pauses animation frames in a
background tab, so the audio element's `timeupdate` (about 4 Hz, also in the background) runs the
same check: there a jump can be up to about 250 ms late, but a cut is never played through. React
does not re-render during playback: the playhead canvas reads `player.position()` on its own frame.
**Play selection** returns the cursor to the start of the selection when it ends, to play it again.

## 2.6 Transcribe, and the three later tabs

- **Transcribe** asks for confirmation only when the notes are `ready` and nothing is unsaved: that is
  the one case where current notes (with their edits) are replaced. Stale or missing notes are not
  worth keeping (Q-2), and with unsaved cuts an alert above the waveform already says that saving
  makes the notes stale. `force: true` is sent only in the confirmed case; the backend transcribes
  stale notes again without it.
- The label says what will happen: "Transcribe", "Save and transcribe", "Transcribe again", "Save and
  transcribe again", "Show the transcription" (while one runs).
- `LaterStepTab` is the Notes, Hands and Sheet tab until Phases 7 and 8. It shows the state and reason
  of its step, follows a running transcription with `ProgressBanner` (the job id from
  `status.steps.notes.details.jobId`), refreshes the status on `done`, and opens the Playground view
  of the same piece (the flow page sets the working piece when it opens one). A new MuScriptor piece
  therefore cannot reach the Sheet tab of the flow page before Phase 8 (**Predict hands**), but its
  piano sheet opens in the Playground as before.

## 2.7 Smaller points

- The Source tab has three ways in, as the plan lists; **Record** and **Compose** stay on the
  Playground Input page.
- The flow page sets the working artifact (`audioUuid`, `label`) when it loads a piece, so the
  Playground tabs show the same piece.
- An MUI `Tooltip` with a string title gives its title as the accessible name of a child that has no
  label of its own: the tabs were named "Transcribe the audio to see its notes." instead of "3.
  Notes", and **Play all** was named by its tooltip. Every tooltip of the flow page uses
  `describeChild`, which makes the title a description. Other pages were not changed.
- `useProgress` keeps its stage ranges as they were: the video download also reports a `download`
  stage, and a shared range would have changed its bar.
- The YouTube job does not run in the GPU queue.

## 2.8 After the user's check: the edited audio, and the piano roll's note panel

**The edited audio is the audio of the piece** (plan section 9.2, "Changed in Phase 6"). The user
cut the start and the end of "Come on Eileen", transcribed it, and played it on the Playground's
Piano Roll: the untouched original played under notes in the time of the cut piece. The rule now:
once cuts are saved, every player plays the edited audio; the original stays on disk for the Audio
tab only (the user chose to keep it rather than replace it). `audio/piece_audio.py` writes
`piece-r<N>.flac` and `piece-r<N>.wav` when the cuts are saved, or on the first request if missing,
and deletes files of other revisions. On "Come on Eileen" (two cuts, 263.50 s to 257.05 s): written
in 0.7 s, 22 MB of FLAC, and its length equals the notes' `durationSeconds` (257.06 s). A test checks
the join sample for sample on a stereo 44.1 kHz original. Every audio answer is sent with
`Cache-Control: no-cache`, because the same address changes content when the cuts change.
`/audio/{uuid}/range` and the range edit still read `normalized.wav` in the time of the original
(Phase 4 report, 2.5): left as they are.

**The piano roll's note panel** (the user's request). The panel (`NoteSelectionToolbox`, used by
the Playground's Piano Roll and Notes Falling) now has the Spanish name as its title (`Do - 5`,
black keys with a sharp, `spanishKeyName`), or "N notes", and no explanation text. On the Piano
Roll it also has **To left hand** / **To right hand** when every picked note has a hand. The move
is written at once through `PATCH /pieces/{uuid}/notes` with two `hand` operations that save every
hand as the roll draws it, with the picked notes moved (the same idea as the piano sheet's first
hand change, Phase 5 report 2.5): saving only the moved notes would let the split run again and move
others. `GET /matrix/{uuid}/events` now sends each note's `id` and the `revision` and
`handsRevision` the PATCH needs. Checked in a browser on a temporary transcribed copy: title "Si -
3", one note changed hand and no other, hands revision 1 to 2.

**A hand move without a reload** (the user's next request). The first version reloaded the whole
piece after the save, so the roll blanked and every note was drawn again. Now the page keeps the
moved hands over the loaded notes (`HandEdits` in `PianoRollPage.tsx`, tagged with the loaded
`RawEvents`, so a real reload drops them), changes the colour on the press, saves in the background,
takes the new `revision` and `handsRevision` from the PATCH answer for the next move, and puts the
colours back if the save fails. Each rectangle is now `components/notes/RollNote.tsx`, a memoized
component that React skips when its own values did not change, which also spares the whole list on
each frame of playback. Measured in headless Chromium on a transcribed copy of Superestrella (1,351
notes): 0 note elements rebuilt, only the moved notes recoloured (1, then 7), one request (the
PATCH), and the colour changes 25 to 40 ms after the press (42 to 50 ms without the memoized note).

## 2.9 Notes without a hand (the user's rule)

On "Come on Eileen" the Hands step said "4 notes have no hand". The hand split runs on the piano
sheet's grid (40 ms columns) and places no note shorter than one column (D-05) or sharing its
column with another note of its key. Here: one note of 10 ms at 1:15.01 and a chord of three 30 ms
notes at 4:10.00, out of 2,219. The Piano Roll's hand move (section 2.8) then saved the hand of
every placed note, which left those 4 as the only ones without a hand.

The user's rule: after the hand prediction every note has a hand; a note the split cannot place is
shown in red, because it is often a note the engine imagined, and the user deletes it or gives it a
hand. Built on the Playground's Piano Roll: once the piece has hands, a live note without one is
drawn solid red (`missingHand` in `noteVisuals`; a note marked to come off stays dashed red), its
tooltip says why, a notice above the roll counts them with **Select them**, and the note panel
offers **To left hand** / **To right hand** for them. The Hands step's reason now says the same.
Checked on a temporary copy of "Come on Eileen" with the same cuts: 4 red notes, **To right hand**
made the Hands step `ready`.

**Finding them** (the user's next request). A 10 ms note in four minutes is a dot, so:
`components/notes/HandlessStrip.tsx` is a strip as wide as the page for the whole song, under the
notice, with a red mark per note without a hand and the playhead as a line; a click on a mark goes to
that note, a click elsewhere moves the playhead. **Review one by one** (or a mark) selects one such
note alone, moves the playhead 1 s before it, scrolls the roll to it at once (a smooth scroll over
minutes left the wrong place on screen) and the page up or down so the note is mid-window. The panel
then shows "No hand · 04:10.00 · 30 ms" and "2 / 4" with arrows in its title bar; the arrow keys do
the same. After **Delete** or a hand button the review goes on to the next note, and ends after the
last. Checked on a temporary copy of "Come on Eileen": 4 marks, every step with the note inside the
window, the list shrinking 4, 3, 2, 1, 0, no console error.

**A sounding note** (the user's request). The old rule filled a sounding note with the right
hand's light blue, which a right-hand note already has, so right-hand notes did not change while
they sounded. `noteVisuals` now draws every sounding note black with its name in white
(`labelFill`, a new field), and a thick border in the colour of its hand: blue right, green left,
red for no hand. Both the Piano Roll and Notes Falling use it. Phase 7's canvas should keep the same
rule.

**For Phase 8 (the Hands tab).** `POST /pieces/{uuid}/hands/predict` gives the notes the split did
not place a hand by the quick rule (Phase 5 report 2.4). Under this rule it must not: those notes
stay without a hand (`-` in the answer), red on the Hands tab, for the user to delete or assign. The
quick rule stays for a note the user adds after the hands were saved (plan section 8.3).

# 3. Measurements

## 3.1 The flow in a browser

`npm run check:flow` (headless Chromium through the containers, section 1) uploads a temporary copy
of Superestrella (189 s), walks the flow and deletes it. Result on 2026-09-29, after the gesture
changes of section 2.4: 29 of 29 checks, no console error, no failed request.

| What | Value |
|---|---|
| A 19 s cut (frames 5,675 to 7,567), **Play all** from 1 s before it for 1.8 s | stopped at frame 7,641: 0.74 s after the cut's end, as expected |
| **Transcribe** of the piece with that cut | 1,169 notes, `muscriptor-large`, ready in about 25 s |
| YouTube download of a 19 s video ("Me at the zoo"), click to the Audio tab | 2.5 s; the name filled from the title |
| A top-bar link with an unsaved cut | blocked by the dialog; **Discard** then leaves |

## 3.2 The waveform route

`GET /audio/{uuid}/frames/peaks` on Superestrella, through the backend container: 18,917 frames,
50.6 KB of JSON, 35 KB sent with gzip, 8 to 30 ms (the first request 30 ms, then 8 to 14 ms). The
whole-view paint loops once over the visible frames (18,917 at most for this piece).

# 4. Notes for later phases

**Every phase.** Nothing of Phases 3 to 6 is committed yet. `npm run check:flow` walks the flow page
end to end (about 40 s with the transcription, `--no-transcribe` for 10 s); extend it with each new
tab. It needs `make up` and uses the pieces `b99bc3ae` and `a585f9eb` read-only.

**Phase 7 (the Notes tab).**
- Replace `<LaterStepTab step="notes" />` in `App.tsx` with the Notes tab. Keep what it does while a
  transcription runs: `status.steps[notes].details.jobId`, and `refresh()` from `usePiece()` on
  `done`, so the tabs update.
- Unsaved edits: `useUnsavedChanges(summary, {save, discard})` and `<SaveBar>`; after a save that is
  followed by a navigation of the page itself, pass `{ state: SAVED_NAVIGATION }`.
- **The notes are in the time of the piece; the audio file is in the time of the original.**
  `useCutPlayer` works in original frames and jumps the cuts. The Notes tab needs the other
  direction too: a piece frame from the audio's position, and an original time from a piece time to
  seek. `keptRanges(cuts, totalFrames)` in `audio/cuts.ts` gives the frame table, the same rows as
  `kept` of `GET /audio/{uuid}/cuts`; add `toPiece` and `toOriginal` beside it (one binary search
  each), with cases in `check:cuts`.
- The canvas patterns of `CutWaveform` (a lower canvas painted on change, the playhead alone on an
  upper canvas read from `position()` on each animation frame, `prepare()` for the pixel density, the
  non-passive wheel listener) are the ones section 9.5 asks for. `frames/peaks` can draw a waveform
  under the rectangles.
- Use `describeChild` on every `Tooltip` around a labelled control.

**Phase 8.** Replace the Hands and Sheet `LaterStepTab`s. The Sheet tab must honour the stale banner
rule of the Phase 5 report (section 4).

**Phase 9.** The new routes (`/pieces`, `/audio/{uuid}/cuts`, `/audio/{uuid}/frames/peaks`,
`/youtube/jobs`) are not yet in `documentation/services/backend/`. The Playground's "Create segment"
(which copies the audio) still exists beside the cuts.

# 5. Files

New, backend: none (changes only). New, frontend: `src/api/pieces.ts`, `src/audio/cuts.ts`,
`src/audio/frameView.ts`, `src/audio/useCutPlayer.ts`, `src/components/audio/CutWaveform.tsx`,
`src/components/audio/waveformPaint.ts`, `src/components/piece/` (`StepTabs.tsx`, `stepLabels.ts`,
`SaveBar.tsx`, `YouTubeDownload.tsx`), `src/pages/piece/` (`PiecePage.tsx`, `pieceContext.ts`,
`PieceIndex.tsx`, `PieceResume.tsx`, `SourceTab.tsx`, `AudioTab.tsx`, `LaterStepTab.tsx`),
`scripts/check-cuts.ts`, `scripts/check-flow.mjs`.

Changed, backend: `api/audio.py` (`frames/peaks`), `api/youtube.py` (`/jobs`), `audio/frames.py`
(`frame_peaks`), `audio/youtube.py` (`store` stage), `tests/test_audio_frames.py`,
`tests/test_youtube.py`. Changed, frontend: `main.tsx`, `App.tsx`, `layout/routes.ts`,
`layout/AppLayout.tsx`, `api/audio.ts`, `api/matrix.ts`, `api/youtube.ts`, `api/index.ts`,
`hooks/useProgress.ts`, `components/input/TranscriptionSettings.tsx`,
`pages/playground/InputPage.tsx`, `package.json`, `README.md`. Documents: the plan (sections 7.1,
7.3, 9.4, 10.5, 14) and the checklist.
