# 03: The context of the new sheet, for every later implementation

Audience: the agent of any later implementation in aimpromptu. Read this file first when a task touches the piano
sheet, the AI that writes it, the hands, the lyrics, the PDF or a change of a part's length. It says what
implementation 03 built, which decisions now bind, where the code is, and which phase report tells how each part was
done and measured. The details are in the files it links; this page is the map.

**Implementation 04 changed some of it** (the decoration notes, prompt version 6, the notes the AI adds and leaves
out, the Enhance with AI dialog, the sheet page): read
[`../04-app-enhancements/04-context.md`](../04-app-enhancements/04-context.md) after this page.

State: done on 2026-10-27, merged into `master` (`57a15a2`). Eleven phases (0 to 10), one branch
(`feat/migrate-new-logic`). Folder index: [`README.md`](README.md). Status of every task: [`03-checklist.md`](03-checklist.md).

# 1. What implementation 03 did

Before it, aimpromptu drew the sheet in the browser with vexflow-v2 (`@aimpromptu/grid-notation`, a sibling checkout),
from a score payload the backend built (`TimeScorePayload`, the `/time` routes). The project had five steps (Source,
Audio, Notes, Hands, Sheet), the reader named the negra from a histogram of gaps (D-09), and the sheets had long
shapeless beams, even spacing, wrong `#` and `b`, and many hand errors.

Research plan 01 (the folder `/home/david/Documents/projects/music/poc-aitu-research` on Ubuntu) built a new chain:
an algorithm, an LLM step with Sonnet 5.5, and an SVG engine with the look of the classical editions. Implementation
03 moved that chain into the app and adapted it to the user's decisions of 2026-10-23:

- the sheet has **no compases, no tempo, no puntillos and no silencios**; a blank space means the hand plays nothing;
- the space between notes follows their timing and their density, in either hand;
- **the Hands step is gone**: four steps now (Source, Audio or Video, Notes, Sheet);
- the algorithm's sheet is on screen at once, and **the AI improves it in the background**, segment by segment;
- the backend lays the sheet out and draws it as SVG; the browser only shows it, plays it and edits it;
- vexflow-v2, the `/time` routes, `notation/`, the negra ladder and Predict hands are removed (Phase 10).

The brief in the user's own words (Spanish) is [`03-prompt.md`](03-prompt.md). The plan, with every decision, the
binding rules and the changes each phase made (its section 11), is [`03-plan.md`](03-plan.md).

# 2. The decisions that bind later work

| Decision | Where it is told |
|---|---|
| No compases, meter, tempo, puntillos or silencios on the sheet; rule 3 of the time model confirmed | plan 3.1; [`context/backend/time-model.md`](../../backend/time-model.md) |
| The figure of a note comes from its own length (split 0.7 below the negra, the middle point above), capped at the next onset of its hand; no tuplets; one figure per chord and per run of even gaps | plan 3.3; [phase 2](03-implementation-phase-2.md) sections 4 and 12 |
| Grace notes: a semicorchea or shorter that sounds just before its main note; any note two figures shorter than the next is an acciaccatura. **Changed by implementation 04, Phase 2**: only one or two fusas or shorter are decoration notes, and a lone short note before a much longer one is written longer | plan 3.3; [phase 2](03-implementation-phase-2.md) sections 5, 13, 14; now [`04-context.md`](../04-app-enhancements/04-context.md) section 2 |
| The reference figure (D-09 changed): the AI names it from the gaps in words, the algorithm from its pulse estimate; **Transpose figures** is the user's override | plan 3.3 and 4; [phase 4](03-implementation-phase-4.md) section 2 |
| Alteraciones: the user's rules 1 to 7 (a sign every time, a becuadro only to cancel the armadura, no double signs, the other name before a becuadro, sostenidos or bemoles by the armadura, an armadura per passage, a courtesy sign after a becuadro); Do mayor: Do#, Mib, Fa#, Sol#, Sib | plan 3.4; [phase 2](03-implementation-phase-2.md) sections 6 and 15 |
| Beam groups: one figure per group (one odd note at an edge at most), at most 8 notes, cut at a jump, a turn or a broken pattern | plan 3.11; [phase 4](03-implementation-phase-4.md) section 3 |
| Spacing: one x per onset frame for both hands; empty time beyond a blanca keeps 30 % of its width; line breaks never inside a beam group when a free place exists | plan 3.2; [phase 3](03-implementation-phase-3.md) sections 3 and 4 |
| Clef rules version 4 for the left hand (bass, then treble, then treble + 8va); no 8va in the bass clef, an 8vb allowed | plan 4; [phase 7](03-implementation-phase-7.md) section 4 |
| Hands: one numeric truth, the hand of each note in `notes.pmn`; the AI writes it first; a run again may change any hand, reading the current hands as a suggestion; no edit while the AI writes | plan 3.7; [phase 6](03-implementation-phase-6.md) section 3 |
| A run again keeps the user's marks (fingers, figures set by hand, the grace switch) and writes the AI's kinds again (beams, clefs, 8va, armaduras, ornaments) | plan 3.7; [phase 7](03-implementation-phase-7.md) section 3 |
| The page says "AI", never the model's name (**Enhance with AI**, **Enhanced with AI**, **Enhance it again with AI**); the mark is never lost, and a failed run keeps the earlier AI sheet | plan 11 (phase 5); [phase 5](03-implementation-phase-5.md) section 8 |
| Existing songs keep their data and get **Enhance with AI**; new transcriptions go to the AI by themselves | [phase 5](03-implementation-phase-5.md) section 3 |
| Tools dropped by the user: even spacing, the room of a stretch, speed changes, print smaller, the unplayed decoration, hiding or dragging an 8va bracket, Find trills, Remove all, Bring back; Layout keeps Zoom and Space between lines | plan 8; [phase 7](03-implementation-phase-7.md) section 3; [phase 8](03-implementation-phase-8.md) section 3 |
| The old clefs and octave lines of `sheet.json` are dropped; the new clef rules apply everywhere | [phase 9](03-implementation-phase-9.md) section 3 |
| Credits: the API key of the user's subscription (about 100 USD a month, about $0.9 per song, about 110 songs a month); when they end, the algorithm's sheet stays, with nothing alarming on the page | plan 3.8; [phase 4](03-implementation-phase-4.md) section 6 |

# 3. How the sheet works now

## 3.1 The files of a part

| File | What it holds |
|---|---|
| `notes.pmn` | The piece: every note with its onset, length and hand. The only truth of the hands |
| `sheet.f1` | The reading the AI or the user decided: the F1 frames text, with one `# aitu-sheet {...}` record line on top (source `algorithm`, `llm` or `mixed`, the `handsRevision` it was written for, the windows, the reference figure, the model, the prompt version, the cost, the runs). A sheet the algorithm wrote and nobody edited is not stored: it is a function of the notes |
| `sheet.edits.json` | The part's undo and redo log (50 steps), kept by the backend through a reload |
| `sheet.pending` | The part's new notes ask the AI to write the sheet (a transcription or a video read writes it) |
| `sheet.json` | The old vexflow-v2 reading. Still read for its armadura, a renamed figure and the user's marks (`part_sheet/legacy.py`), never written by the new sheet |

## 3.2 The backend

```text
notes.pmn ── sheet.proposal.frames.propose_frames (the algorithm, at once)
          ── sheet.llm.frames.write_frames + sheet_llm.ClaudeComplete (the AI, in the background, window by window)
          ── part_sheet.build (stored, laid again on changed notes by build.reapply, or the algorithm)
          ── sheet.engrave.frames.render_frames ── SVG (data-note ids) + columns + systems + segments
          ── api/sheet.py ── the page
```

- **The core** `aitu_backend/sheet/` is the research's `aitu_notation` with the backend's names. Its
  [`README.md`](../../../aitu-backend/src/aitu_backend/sheet/README.md) is the reference: sections 1 to 8 the copied
  core and the licenses, 9 the format without compases, 10 the engine, 11 the LLM step, 12 the sheet in the app,
  13 editing, 14 the note and range tools, 15 the toolbox, lyrics and paper, 16 a change of length, 17 the old marks.
- **The part's sheet** `aitu_backend/part_sheet/`: `store` (`sheet.f1`), `build` (the sheet at any moment and its
  drawing), `job` (the AI run), `edits` (every edit and its undo step), `reading` (the reading edits as pure
  functions), `lengths` (the sheet through a paste, a promotion, a split, a join), `legacy` (the old marks).
- **The AI** `aitu_backend/sheet_llm.py`: the `anthropic` SDK, `claude-sonnet-5-5`, prompt caching, time limits,
  retries. The prompt is version 5, in `sheet/llm/prompt/frames/` (version 6 since implementation 04, Phase 3); the reference figure is its own request before the
  windows; the checker and the guards hold the format, and the algorithm is the fallback of any window.
- **The routes** `api/sheet.py`: `GET /sheet/{uuid}`, `POST .../hands`, `/reading`, `/transpose`, `/add`, `/paste`,
  `/remove`, `/undo`, `/redo`, `/llm`, `/llm/stretch`, `GET .../stretch`, `/pages`, and `GET`/`PUT .../words`. The
  whole HTTP surface: [`documentation/services/backend/endpoints.md`](../../../documentation/services/backend/endpoints.md).
- **The hand split** `aitu_backend/hands/` stays: the algorithm and a first AI run start from it
  (`transcription/pipeline.starting_hands`, the cache of `inferred_split(keep_saved=True)`).

## 3.3 The frontend

- `aitu-frontend/src/pages/piece/sheet/frames/`: `FramesSheetPage` (the page), `FramesSheetView` (the SVG, the cursor,
  the lit notes, click to seek), `useFramesSheet` (the data and every edit), the note, range, sheet and lyrics
  toolboxes, the PDF and preview dialogs, `EnhanceStretchDialog` (`EnhanceDialog` since implementation 04, Phase 4). `SheetPage.tsx` only holds the step types and
  shows `FramesSheetPage`.
- Every screen that shows a sheet uses it: the Sheet step, Play mode, Recording in Sheet, the passage page, From other
  projects, the requests review, the PDF.
- The PDF writer (`src/print/`) turns the backend's pages into PDF operators with the base fonts only.
- Overview: [`context/frontend/rendering.md`](../../frontend/rendering.md); the tools:
  [`context/frontend/annotations.md`](../../frontend/annotations.md) and its siblings; the components:
  [`documentation/services/frontend/components.md`](../../../documentation/services/frontend/components.md).

# 4. Rules for a new change

- **A new editing tool** is three parts: a function of `part_sheet/edits.py` that changes `notes.pmn` or `sheet.f1`
  under the part's lock and records one `_Step`; a route of `api/sheet.py` that answers the sheet drawn again; a row
  of a toolbox that calls it through `useFramesSheet`. A reading edit on an algorithm sheet stores it as edited by the
  user (`Record.edited`). Pattern: [phase 6](03-implementation-phase-6.md) section 9, [phase 7](03-implementation-phase-7.md)
  section 4.
- **A change of a part's length** must go through `editing/paste.py` (`paste`, `cut`), which moves `sheet.f1`
  (`part_sheet/lengths.py`) and the old marks (`editing/marks.py`) in the same write. See
  [phase 8](03-implementation-phase-8.md) section 10.1.
- **A change of the format** keeps `frames.check` holding and the golden files of the bars path unchanged; a format
  change on purpose says why in its report.
- **The engine stays in the backend**: one edit takes about 0.25 s from the click to the page
  ([phase 6](03-implementation-phase-6.md) section 6).
- **A version of My library is never written in place**: an edit or **Enhance with AI** opens the edit copy first (the
  rights table, `auth/`).
- **A backend reload stops a running AI job and loses it** (the job lives in memory; `sheet.f1` is written at the end).
  Look for a running job in the logs before any edit of a backend `.py` file.
- **Credits**: any test that calls the AI starts with a few windows and asks the user first. The checks that
  transcribe (`check:flow`, `check:journey`, `time:flow`) start the AI too.
- **Every visible change** is checked by the user in the browser at `http://ubuntu:5173`, and a drawing change also in
  a gallery (plan 6.2).

# 5. Where to find how a part was done

| Topic | Phase report | Also |
|---|---|---|
| The inventory of everything vexflow-v2 drew, the baseline screenshots | [phase 0](03-implementation-phase-0.md) sections 4 and 5 | [`screenshots/phase-0/`](screenshots/phase-0/) |
| The core copied into the backend, the golden tests, the time per song | [phase 1](03-implementation-phase-1.md) | `scripts/draw_sheet.py` |
| The format without compases, figures, grace notes, alteraciones, the algorithm on the library | [phase 2](03-implementation-phase-2.md) | [`gallery/phase-2/`](gallery/phase-2/index.html) |
| The engine: spacing, line breaks, signs, the cursor map, one segment, speed | [phase 3](03-implementation-phase-3.md) | [`gallery/phase-3/`](gallery/phase-3/index.html) |
| The LLM step: the design, prompt version 5, the checker, cost and accuracy on 10 songs | [phase 4](03-implementation-phase-4.md) | [`gallery/phase-4/`](gallery/phase-4/index.html) |
| The Sheet step in the app: four steps, the AI in the background, `sheet.f1`, playback, the "AI" wording | [phase 5](03-implementation-phase-5.md) | |
| The edit model: hands, undo and redo in the backend, clefs around a moved note, the time of one edit, the audio after a jump | [phase 6](03-implementation-phase-6.md) | |
| The note and range tools, the user's marks, Enhance with AI of a stretch with the user's words | [phase 7](03-implementation-phase-7.md) | [`gallery/phase-7/`](gallery/phase-7/index.html) |
| The sheet toolbox, Transpose, lyrics (free blocks, fonts), the chord keyboard, the PDF, copy and paste, Recording in Sheet | [phase 8](03-implementation-phase-8.md) | sections 4 to 8 (half 8A), section 10 (half 8B) |
| The old `sheet.json`: what it held, the marks carried, the migration | [phase 9](03-implementation-phase-9.md) | `scripts/migrate_sheets.py` |
| What was removed, the final checks, the documentation, the licenses | [phase 10](03-implementation-phase-10.md) | [`screenshots/phase-10/`](screenshots/phase-10/) |

The galleries are a record: the Phase 3 one cannot be built again, because its vexflow-v2 column came from a script
removed with the old sheet.

# 6. Checks

- **Backend**: `pytest` in the container (1,251 tests at the end; 2 known failures need the GPU). The sheet's tests
  are `tests/test_sheet_*.py`, `test_part_sheet.py` and the golden files in `tests/golden/sheet/`. When another
  project holds the GPU, run them on the CPU (`context/04-local-development.md`).
- **Frontend**: `tsc`, `lint`, `vite build`; the browser checks on the `data-*` hooks of `scripts/frames-page.mjs`:
  `check:frames-sheet`, `check:frames-edit`, `check:frames-tools`, `check:frames-toolbox`, `check:play`,
  `check:paste`, `check:compose`, `check:passage -- --played`, and the others listed in
  [`context/04-local-development.md`](../../04-local-development.md). Browser scripts work on temporary copies only.
- **Screenshots**: `scripts/baseline-sheets.mjs` takes the 22 screens with a sheet.
- **Documentation**: `scripts/docs/check-links.py`.

# 7. Licenses

Nothing is owed while the app stays on the home machines. Before any release, section 8 of the core's
[`README.md`](../../../aitu-backend/src/aitu_backend/sheet/README.md) lists what needs action: the Verovio rules of
`engrave/vrv.py` (LGPL-3.0), the prompt examples (a Beethoven encoding with no license file, short transcriptions of two
pop songs), the pulse weights, and the notices of the Leipzig glyphs and the lyrics fonts.

# 8. Open points

- The AI run is not saved window by window: a backend restart loses the windows already paid for
  ([phase 5](03-implementation-phase-5.md) section 8).
- Edits stay closed while the AI writes ([phase 6](03-implementation-phase-6.md) section 9).
- `editing/marks.py` and the reader of `sheet.json` can be removed together when the user decides the old marks no
  longer need to be read ([phase 9](03-implementation-phase-9.md) section 7).
- `split_of`, `hands_of`, `run_pipeline` and `placed_note_ids` serve only tests; the `hands` value of the
  `projects.step` check can go with the next database revision ([phase 10](03-implementation-phase-10.md) section 8).
- Recording from an address that is not secure: `http://ubuntu:5173` has no microphone or MIDI piano; the ways
  around it are an SSH tunnel to `localhost:5173` or the browser's setting ([phase 8](03-implementation-phase-8.md)
  section 10.9).
- Not in this implementation, still available in the research folder: the difficulty grade, easier or richer versions
  of a passage, reading a printed page from an image, fingering (plan 2).
