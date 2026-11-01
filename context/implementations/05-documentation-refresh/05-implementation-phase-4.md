# 05, Phase 4: the Sheet page (the frontend shell)

Written for: the join of wave C and the agent of the wave D join. Branch `feat/05-docs-refresh`.

## Docs changed

- `context/frontend/sheet-page.md` (new, 200 lines): where the page is drawn (the step's roles), the header, the
  empty sheet, the buttons (`sheetButtons`), the floating toolbox, the zoom, the sheet's state, the cursor and the
  recording, what the view draws over the drawing, the keys, the AI's panels, the files. Undo and redo are left for
  Phase 8.
- `context/frontend/rendering.md` (the frontend half, owned in wave C): the sheet section now points at `sheet-page.md`;
  the stale words "Sonnet" and "research viewer" are gone; the test hooks and the checks are kept.
- `context/frontend/timestamps.md`: the table "Where it applies today" rewritten to the code as it is. Four components
  it named (`MatrixGrid`, `MatrixPage`, `TranscriptionSettings`, `AudioRecorder`) no longer exist. Added the sheet's
  times. Says that no frame label is printed today.

## What was stale

- `rendering.md`: "the sheet goes to Sonnet by itself" and "Sonnet 5.5 today" (the page says **AI**, see the rule of
  section 4.3 of the plan); the page list was out of date (`FramesSheetPage` header and buttons, the AI panels).
- `timestamps.md`: four removed components; `formatFrameLabel` and `FRAME_LABEL_WIDTH` have no caller.
- `projects.md` section 4 "Sheet" (its pending edit E4.1 below): "A new transcription goes to Sonnet by itself" is not
  true since 2026-10-30 (commit `ca67aca`, "The AI starts only from the button").

## Code and docs that disagree (for the user)

1. **The AI does not start by itself, but a marker is still written.** `transcription/pipeline.py` calls
   `store.ask_sonnet` after a new transcription, which writes `sheet.pending` (`storage/paths.py`). No code reads it:
   `store.asked` has no caller. So the marker is dead, and the pipeline's docstring still says "the Sheet step starts
   it by itself". Options: remove the marker and its writer (recommended: one small code change, a Phase of its own); or
   keep it as it is. The docs say the page starts no run by itself, which is what the code does.
2. **Comments still say "Sonnet".** `pages/piece/sheet/frames/FramesSheetPage.tsx` header (line 6: "Sonnet 5.5 today");
   `pages/piece/sheet/frames/useFramesSheet.ts` header (lines 3 and 5: "Sonnet's job", "Sonnet started by itself");
   `part_sheet/job.py` header (line 1: "Sonnet writes"); `transcription/pipeline.py` (the docstring above).
   `part_sheet/job.py` also says "GPT-6.1 Terra ... Sonnet 5.5 until implementation 04-3" (history, fine).
3. **A second time helper.** `formatSeconds` in `pages/piece/sheet/sheetConstants.ts` gives the same `mm:ss.cc` as
   `formatTime` in `audio/time.ts`. The sheet's modules use it (the note, range and lyrics toolboxes, the keyboard).
   The rule "nothing formats a time inline" in `timestamps.md` says there is one. Not critical.
4. **No caller for the frame label.** `formatFrameLabel` (`audio/time.ts`) and `FRAME_LABEL_WIDTH` (`ui/timestamps.ts`)
   have no caller since the matrix grid was removed. Either delete them or use them again where frames are printed.
5. **`usePlayedNotes.ts` is not part of the sheet.** Only `pages/play/FallingView.tsx` (Play mode, Notes Falling) uses
   it. Phase 19 owns Play mode; it is named there so the sheet's docs do not claim it.

## New terms for the glossary (Phase 20)

- **the veil**: the pale band over the staves of a segment the AI is writing (`data-segment-state="working"`).
- **the reveal**: a segment that comes back, drawn column by column over blank staves (about 1.8 s).
- **the marking strip**: the strip above the upper staff of a line where a stretch is marked by a drag.
- **the window** (of a take): the blue frame, with a grip, of the frames of a passage's Proposal that go into the song.
- **the wheel zoom**: ⌘ or Control with the wheel over the sheet; the drawing scales at once, then is laid out again.

## Not checked

- The page was read from its code only. No app was started, no click, no AI run (plan section 5). The behaviour
  described in `sheet-page.md` comes from the code and its comments.
- Read in part: `FramesSheetPage.tsx` (the header, `sheetButtons`, the zoom and wheel, the keys, `startPassage`,
  `splitHere`, the Enhance wiring, the floating bar); `FramesSheetView.tsx` (the overlay, the cursor, the picks, the
  strip, the veil and the reveal). Not read: the lyrics drag code in `FramesSheetView.tsx` (lines ~595 to ~750, Phase 8),
  the toolboxes' bodies, `FramesSheetPage.tsx` lines ~1400 to ~1645 beyond the dialogs' list.
- The assertions of the `check:frames-*` and `check:enhance-dialog` scripts (only their names were checked, in
  `aitu-frontend/package.json`).
- The Sheet step's "never *stale*" (kept from the old text in `projects.md`; the status code was not read).
- Whether the frame label rule still holds where a frame is printed (no such screen found: see disagreement 4).

## Pending edits for shared files

These go in the join of wave C (section 4.4 of the plan).

**E4.1** `context/frontend/projects.md`, section `## 4. The steps`: replace the whole paragraph that starts
`**4. Sheet** (implementation 03, Phase 5)` (it runs to the line before `**Then, Save to library.**`) with:

```text
**4. Sheet.** The new piano sheet, drawn by the backend and shown by the Sheet page ([sheet-page.md](sheet-page.md)):
the title with the AI mark, the buttons, the floating toolbox, the zoom and the recording. It is on screen at once.
The AI writes the sheet only when the user presses **Enhance with AI**; the page starts no run by itself. A sheet the
AI wrote keeps the green AI mark for good, and its button then reads **Enhance it again with AI**. The tools of the
sheet are in [annotations.md](annotations.md), the AI's runs in [`../ai/`](../ai/README.md), and the info button in
[folders-and-metadata.md](folders-and-metadata.md). The Sheet step is *running* while the AI writes, *ready* once a
sheet is stored (`sheet.f1`, or an old `sheet.json`), and *missing* otherwise; it is never *stale* any more. An old
saved sheet (`sheet.json`) is still read for its key, its renamed figure and its marks; nothing writes one.
```

Effect: `projects.md` goes from 293 to about 255 lines. It stays over the about-200 limit: Phase 20 (report of Phase 14).

**E4.2** `documentation/services/frontend/components.md`, section 3, the table of modules: after the row that starts
`| \`frames/FrameRangeFields.tsx\``, add:

```text
| `frames/navigation.ts` | The navigation state of **Enhance with AI** on a version of My library: the run (`songRunOf`), the model and the batches (`runChoiceOf`), and `enhanceWithAi` |
```

**E4.3** `documentation/services/frontend/components.md`, section 3, the table of shared components: after the row that
starts `| \`components/time/FigureGlyph.tsx\``, add:

```text
| `components/piece/AiMark.tsx` | The AI mark before a title: green (**Enhanced with AI**) once the AI enhanced the sheet, faint grey (**Not enhanced with AI yet**) when it could and has not |
```

**E4.4** `context/00-index.md`, the table of `frontend/`: after the row `| [frontend/rendering.md](frontend/rendering.md) | ...`, add:

```text
| [frontend/sheet-page.md](frontend/sheet-page.md) | **The Sheet page**: the header and its buttons, the floating toolbox, the zoom, the cursor and the recording, the veil and the marks the AI leaves on the sheet, the keys |
```

**E4.5** `context/ai/whole-run.md`, line 92: replace the text
`` `context/frontend/sheet-page.md` (Phase 4 writes it): the Sheet step's page and its header `` with
`[sheet-page.md](../frontend/sheet-page.md): the Sheet step's page and its header`.

**E4.6** `documentation/services/backend/sheet-drawing.md`, line 10: replace `` `context/frontend/sheet-page.md` `` with
`[sheet-page.md](../../../context/frontend/sheet-page.md)` (the rest of the line stays).

**E4.7** `context/frontend/annotations.md` (the hub): no edit. Decided: the hub keeps its **Undo and Redo** and **No Save
button** bullets (Phase 5's note). The page now says there is no **Save** button (`sheet-page.md`, section 7), and Phase 8
adds undo to `sheet-page.md`.

## Checks

- `check-links.py`: 539 files, 2 broken links, both in `05-implementation-phase-7.md` (lines 60, 61: `annotations-sheet.md`).
  Not in my files; Phase 7 owns them.
- `check-names.py` on `sheet-page.md`: 0 missing (62 names). On `timestamps.md`: 0 missing after the rewrite.
  On `rendering.md`: 3 missing (`VexflowSheetPage`, `TimeScoreView`, `components/time/TimeScoreView.tsx`): they are
  the old sheet's names in its history section, kept on purpose.

## Left for later phases

- **Phase 8**: add **Undo and redo** to `sheet-page.md`; `endpoints.md`, `paths-and-data.md` as its plan says.
- **Phase 7**: the zoom in the sheet toolbox's **View** tab is the same zoom as section 6 of `sheet-page.md` (70 to 200 %).
- **Phase 19**: `usePlayedNotes.ts` belongs to Play mode (`FallingView.tsx`), not to the sheet.
- **Phase 20**: `projects.md` is still over 200 lines after E4.1 (about 255); the disagreements above for the user.
