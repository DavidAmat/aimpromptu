# 04 · Plan: app enhancements (the sheet page and the AI's sheet)

Status: written 2026-10-27, after the first discussion. **This is the living plan**: the agents update it when a phase
changes direction (section 9 lists the changes). Audience: the AI agents that build it on the Ubuntu machine, and the
user, who checks each phase in the browser. Music terms stay in Spanish where the user uses them (negra, corchea,
semicorchea, fusa, blanca, redonda, octava). The user calls the grace notes of the sheet **decoration notes** (or
ornament notes); the code calls them grace notes (`Note.grace`, `find_graces`). In this plan "decoration note" is
the user's word and the thing on the page.

**Read first.** In this folder: this file, [`04-1-prompt.md`](04-1-prompt.md) (the brief in the user's own words, with
the answers of the first discussion at its end; they win over this file when the two differ), [`04-checklist.md`](04-checklist.md),
the four images in [`images/`](images/), and the report of the previous phase. Then
[`../03-apply-poc-research/03-context.md`](../03-apply-poc-research/03-context.md): how the sheet works now, the
decisions that bind, where the code is. And `context/language/communication-implementation-plans.md` (how to report).

# 1. Context

Implementation 03 (done 2026-10-27) moved the new sheet into the app: no compases, the algorithm's sheet at once, the
AI (Sonnet 5.5) improving it in the background, the backend drawing the SVG. Using it, the user found things to
polish in two places:

- **The sheet page**: zoom with the mouse, the "Enhanced with AI" badge, where the floating toolbox lives, the
  playback cursor, and a hidden floating toolbox that does not come back.
- **The sheet the AI writes**: too many decoration notes, patterns that are not uniform (a run of octavas with some
  single notes in it), and quick chords that an amateur pianist cannot play.

# 2. Objective

At the end of this plan:

1. **Command + scroll** over the sheet zooms it, and the sheet is laid out again to fit the window width (a trackpad
   pinch does the same).
2. The green **Enhanced with AI** badge is gone; the same sparkle symbol as next to the song name on the Projects page
   sits next to the title, and its tooltip says "Enhanced with AI".
3. The buttons of the floating toolbox are also in the header of the sheet page, next to that symbol, always on
   screen. The floating toolbox stays as it is.
4. The blue playback cursor can be dragged and dropped, also from one line of the sheet to another; the mouse shows it
   can be dragged.
5. A hidden floating toolbox can always be brought back.
6. The new **decoration-note rule** (section 3.1) runs on every sheet.
7. The AI's prompt (version 6) has the **rules of simplicity** (uniform patterns) and the **amateur pianist** rule (no
   quick chord that forces a jump), and the AI may add and leave out notes within limits to follow them.
8. **7 Years** (the My library version) is enhanced again with the new prompt, and the user approved the result.
9. **Enhance with AI** opens one dialog (added in Phase 3, section 3.5): a selected stretch with both hands, the
   right or the left, and the user's words; or, with nothing selected, **Simplify left**, **Simplify right**,
   **Simplify both** (the rules of simplicity over the whole song, batch after batch, each batch seeing the
   simplifications made before) and the full run of today.

Not in this plan: running the AI again on any other song (credits). Every other song gets the new decoration-note
rule at no cost; the user can run **Enhance it again with AI** on a song later.

# 3. Decisions of the first discussion (user, 2026-10-27)

The answers are also at the end of [`04-1-prompt.md`](04-1-prompt.md).

## 3.1 The decoration-note rule

Figures are written as their value in the code: 1 redonda, 2 blanca, 4 negra, 8 corchea, 16 semicorchea, 32 fusa,
64 semifusa. "Two figures shorter" means four times shorter (a semicorchea is two figures shorter than a negra).

**Today** (`find_graces`, [`frames.py`](../../../aitu-backend/src/aitu_backend/sheet/proposal/frames.py)): one or two
columns of one hand, each a semicorchea or shorter and two figures or more shorter than the next note, that sound just
before it (the gap is shorter than the next note's figure), become decoration notes of that note. A longer run stays
written.

**New** (the user's rule):

1. **A decoration note** is a note **shorter than a semicorchea** (a fusa or shorter), one or two of them, two figures
   or more shorter than the next note and sounding just before it. A run of three or more stays written, as today.
2. **A lone short note** (one or two columns, not part of a run of three or more even gaps) that sounds just before a
   note **more than two figures longer**, and is not a decoration note by point 1, is written as a real note with the
   figure **two figures shorter than that note**:

   | Short note | Next note | Written as |
   |---|---|---|
   | semicorchea | blanca | corchea |
   | semicorchea | redonda | negra |
   | corchea | redonda | negra |
   | semicorchea | negra | semicorchea (already two figures shorter: no change) |
   | fusa | negra | decoration note (point 1) |

3. **The last note of a run is not lengthened** (user's answer): four semicorcheas before a blanca stay four
   semicorcheas, so the beam group stays whole.
4. **The user's marks win** (rule 5 of the time model): a column marked `asgrace` is a decoration note whatever its
   figure; one marked `nograce` never is; a figure the user set (`fix`) is never lengthened.

Why: the sheet without compases already shows the timing by the space between notes. A decoration note says "very
fast, before the beat", as in classical music; for a short note of the melody or of the left hand before a long one,
that reading is wrong (images `abuse-decoration-notes.png` and `abuse-decoration-notes-right.png`).

## 3.2 Where the rule applies: every sheet, now

The rule is the app's own calculation, run after the AI answers; it costs no credits. It applies to **every sheet,
when the app draws it**: the algorithm's sheets (already computed on the fly) and the sheets the AI wrote or the user
edited, whose stored `sheet.f1` holds the old decoration notes. The stored file is not written again by this change;
the drawing applies the rule. Everything that draws a sheet goes through `part_sheet.build` (the Sheet step, Play mode,
the PDF, the passages, the requests review), so they all change together.

## 3.3 Notes the AI adds or leaves out

The whole-song prompt today says "Do not add notes, do not drop notes". The rules of simplicity need both: making a
left-hand run of octavas uniform adds the missing octave notes, or leaves out the octave notes to make it all single
notes (the AI chooses); the amateur pianist rule leaves out the far note of a quick chord (Sol-2 in
`complex-fast-notes.png`, keeping Sol-3).

They are kept **as Enhance with AI of a stretch keeps them** (implementation 03, Phase 7; `edits.apply_stretch`):
a note left out is marked removed in `notes.pmn` (not deleted), a note added is written into `notes.pmn` at the onset
of its column. The audio does not change: playback is the recording. A check limits what the AI may change (section
4.3), and an answer outside the limits is sent back with feedback, as today.

## 3.4 Which 7 Years

The **My library version**: project `1a16a836-62b9-483b-af46-d89d0ab1b2d8` (`7 Years — Lukas Graham`, user 1), its
sheet written by the AI on 2026-10-25 (prompt 5, $0.68, no edits). Before it, a test on a temporary copy.

Found in the study, to raise when the run comes (Phase 3): that version already has an **edit copy in the Personal
Vault** (`477086a0-b8ac-492f-aeca-2a56805868af`, `based_on` the library version, with the user's edits, changed
2026-10-26). **Enhance it again with AI** on a library version opens the copy that edits it, so the run would most
likely land on that copy, with its edits. The agent checks what the app does and asks the user before spending.

## 3.5 The Enhance with AI dialog (user, 2026-10-27, after the Phase 3 gallery)

The brief and the answers are at the end of [`04-1-prompt.md`](04-1-prompt.md).

- **Enhance with AI** opens a dialog. **A stretch** (a range or notes selected): both hands, only the right or only
  the left, and the user's words, as today's stretch. With one hand chosen, **the other hand stays exactly as it
  is**: the AI sees it, it cannot change it.
- **The whole song** (nothing selected): **Simplify left**, **Simplify right**, **Simplify both**, and **Write it
  all again** (today's full run, kept).
- **Simplify** does **the rules of simplicity only** (simple.1 uniform patterns, simple.2 the amateur pianist, the
  limits of the prompt 6 check); the hands do not move, and the other hand is not touched.
- **Auto-regressive**: Simplify goes over the song batch after batch (longer batches than a full run: one hand is
  less text), and each batch sees the simplifications made before, so a pattern that repeats gets the same
  simplification.

# 4. Design notes

## 4.1 The sheet page (Phase 1)

Code: `aitu-frontend/src/pages/piece/sheet/frames/` (`FramesSheetPage.tsx`, `FramesSheetView.tsx`,
`FramesSheetToolbox.tsx`), `ui/FloatingBar.tsx`, `components/piece/AiMark.tsx`.

- **Zoom.** The page already lays the sheet out again from the zoom (`spaces = width / (PX_PER_SPACE * zoom) -
  MARGINS`, sent to the backend), kept in the browser (`aitu.framesSheet.zoom`), between `MIN_ZOOM` 0.7 and
  `MAX_ZOOM` 2. The Zoom slider's tooltip says "also Command and scroll over the sheet", but **no wheel handler
  exists**. Add one on the sheet: a `wheel` listener with `{ passive: false }`, `metaKey` (Command) or `ctrlKey`
  (a trackpad pinch sends it) → `preventDefault` and a zoom step; a plain scroll still scrolls. The backend draws the
  new width, so steps should be grouped (one request per pause of the wheel, not one per event), and the note under
  the mouse should stay in view.
- **The AI symbol.** Replace the `Pill` of `data-enhanced-badge` with `AiMark` (the Projects page's mark: green filled
  sparkle, tooltip "Enhanced with AI"; the hollow one, "Not enhanced with AI yet", when the AI could and has not).
  The run count of the old pill's title is dropped (the user's words: the tooltip says "Enhanced with AI"). The
  wording stays "AI", never the model's name.
- **The header toolbox.** The header (title, AI symbol) gets the same buttons as the floating toolbox: Play,
  Record a passage, Paste, Print, Undo, Redo, Sheet toolbox, `⋯`, Enhance with AI. One list of buttons, drawn in both
  places (no copied code). The header stays at the top of the screen while the sheet scrolls (`position: sticky`). A
  narrow window wraps the row or moves the rest into `⋯`. Not shown where the floating toolbox is not shown today
  (Play mode, the `current` role of a passage, an empty sheet).
- **Bring back the floating toolbox.** `FloatingBar` already leaves a small round button (a lightning icon) when it
  is hidden. The user says there is no way back: first find out why in the browser (hidden under something, not seen,
  or not working), and fix it. The header toolbox also gets a button that shows the floating toolbox again.
- **Drag the cursor.** The cursor is an SVG line (`data-frames-cursor`) placed by `placeAt` (`geometry.ts`); a click
  on the sheet already seeks. Add: a wider area around the line that catches the mouse, with the `grab` cursor on
  hover and `grabbing` while dragging; while dragging, the line follows the mouse over the columns of any line of the
  sheet (the reverse of `placeAt`: the position to a time, as the click does), the page scrolls near the window's top
  and bottom edges, and the "keep the cursor in view" of playback stops; on release, the recording seeks there (and
  keeps playing if it was playing). A drag that starts on the cursor never picks notes or starts a box selection.
  Works on read-only sheets too (seeking is not an edit).

## 4.2 The decoration-note rule (Phase 2)

- `find_graces` changes as section 3.1; the lengthening of point 2 is a new step right after it, in the same order in
  both paths that call it (`proposal/frames.py` `propose_frames`, `llm/frames.py` `assemble`). Beam groups are cut
  after it (`trim_beams`), so a note that became a negra leaves its group.
- **Every sheet** (section 3.2): `build._compute` today draws a stored `sheet.f1` "as it is" when its
  `handsRevision` is current (case 1). The rule must also run there. The study chooses how (for example: case 1 laid
  again on the notes as case 2 already does with `reapply`, or only the figures and decoration notes recomputed) from
  two measures: the drawing must not change anything else (beam groups, hands, clefs, the user's marks), and the time
  of one drawing (Phase 6 of 03 measured about 0.25 s for an edit).
- The stored files are not rewritten; the cache of drawings (`build._cache`, keyed by file times) is in memory, so a
  backend reload empties it.

## 4.3 The AI's prompt, version 6 (Phase 3)

Code: `aitu-backend/src/aitu_backend/sheet/llm/` (`prompt/frames/instructions.md`, `frames.py`, `guards.py`),
`sheet_llm.py`, `part_sheet/job.py`, `part_sheet/edits.py`.

- **Decoration notes**: the lines "Grace notes are a rule of the app ..." say the new rule.
- **Rules of simplicity** (new section): a passage that repeats one pattern (octavas, chords, single notes, a bass and
  chord figure) is written the same way every time; a column that breaks the pattern (a single note in a run of
  octavas, an octava or chord in a run of single notes) is made to fit, by adding the notes of the pattern or by
  leaving out the extra ones, whichever reads simpler; the AI may also make the whole passage simpler (single notes
  instead of octavas). Small variations of a pattern make the sheet hard to read for the pianist. The notes keep their
  frames and their pitches: no note moves to another key.
- **The amateur pianist rule** (new): the sheets are for an amateur pianist. A quick chord or decoration note before a
  main note that makes one hand jump far (down, then up quickly) keeps only the note near the main note (in
  `complex-fast-notes.png`: Sol-3 kept, Sol-2 left out). No quick jumps of one hand that only a professional plays.
- **The check** (`check_answer` already has `drop=` and `free=` for a stretch): a whole-song window may leave out and
  add notes only within limits, for example: an added note is at a frame where that hand already plays, with the
  pitch class of a note of that column or of the same pattern around it (an octave or a chord note); a note left out
  never empties the column of its hand; at most a small share of the window's notes change (the study measures it).
  The answers beyond the limits go back with feedback (`feedback.md`); the algorithm is still the fallback of a
  window.
- **Storing**: the run's left-out and added notes go into `notes.pmn` as `apply_stretch` does them, so that the next
  run, the edits and undo see one truth. The record of `sheet.f1` says how many notes the AI added and left out.
- `VERSION` becomes 6; the record of each sheet keeps the prompt version it was written with.

## 4.4 The Enhance with AI dialog and Simplify (Phase 4)

Code: `FramesSheetPage.tsx`, `EnhanceStretchDialog.tsx` (becomes the dialog), the header and floating toolbox's
Enhance button; `part_sheet/job.py` (`start_stretch`, a new `start_simplify`), `sheet/llm/frames.py`
(`write_stretch`, a new `write_simplify`), `api/sheet.py`.

- **The dialog**: two tabs. **A stretch** is open when a range or notes are selected (the hand chosen from the
  selection when it is one hand); **The whole song** otherwise. Minimal UI; the wording says "AI".
- **A stretch, one hand**: the target holds only that hand's notes; the other hand is shown as a fixed part of the
  passage; the check refuses an answer that changes it (a note of it moved, left out, added); `splice` keeps it.
- **Simplify**: windows of one hand (or of both with the hands fixed) up to about twice today's length (the study
  measures the size of a prompt and an answer); the answer writes only the notes of the simplified hand(s) with the
  comment lines of prompt 6; the hands and the other hand cannot change. The places to check (`places`) on every
  batch.
- **What each batch sees of the earlier ones** (the auto-regressive part): the end of the previous batch as it was
  simplified (longer than the 4 s of a full run); the list of every simplification made so far in the song (where,
  before and after: "f4556: D2 was alone in a run of D1+D2 octaves: D1 added"); and the earlier passage most like
  this one (a chorus that repeats, found by comparing the notes' sequence) with what was done there. The study picks
  the sizes from a test on 7 Years.
- **Storing**: as a whole run's note changes (`edits.change_notes`); the beams of the simplified hand may change
  where notes change, its clefs stay unless a note needs them. One step of undo per Simplify run ("Simplify the left
  hand with AI"); the record lists each run (where, which hand, notes added and left out, cost), like `stretches`.
- **Cost**: shown in the dialog before the run (about the cost of a full run or less); every test with the AI asks
  the user first.

# 5. Binding rules

From implementation 03 ([`03-context.md`](../03-apply-poc-research/03-context.md) section 2) and the project's
standing rules; all kept, except the decoration-note rule, which this plan changes on purpose.

| Rule | In this plan |
|---|---|
| No compases, tempo, puntillos or silencios; the figure from the note's own length, capped at the next onset of its hand | kept; the decoration-note rule (03 plan 3.3, phase 2 sections 5, 13, 14) **changed** by section 3.1 |
| Hands: one numeric truth in `notes.pmn` | kept: the notes the AI adds or leaves out also go there |
| A run again keeps the user's marks (fingers, figures set by hand, the decoration switch) | kept |
| The page says "AI", never the model's name; the enhanced mark is never lost | kept: the new symbol carries it |
| Minimal UI (`09-minimal-ui-guidelines.md`) | kept: the header toolbox adds no text |
| Credits: every test that calls the AI starts with a few windows and asks the user first | kept (Phase 3) |
| Browser scripts work on temporary copies, never on a real library piece | kept |
| A backend `.py` edit reloads uvicorn and stops a running AI job: check the logs first | kept |
| No `src/` edits while a browser check runs | kept |
| Every drawing is checked zoomed in and against the data before the user sees it | kept (galleries of Phases 2 and 3) |
| Every visible change is checked by the user in the browser at `http://ubuntu:5173` | kept |

# 6. Method

## 6.1 Documents

In this folder: `04-1-prompt.md` (the brief, with the answers), this plan, [`04-checklist.md`](04-checklist.md),
[`README.md`](README.md), one report per phase (`04-implementation-phase-N.md`, technical, for agents), galleries in
`gallery/phase-N/`, screenshots in `screenshots/phase-N/`. Reports and walkthroughs follow
`context/language/communication-implementation-plans.md`.

## 6.2 Every phase

1. **Study first**: read the code the phase changes; list what exists; write it in the report.
2. **Adapt the plan** from what the study found (section 9 says why).
3. **Ask the user** only for product choices the code and data cannot settle.
4. **Build small, then larger**: a few passages, then 7 Years, then My library (for the rule; never the AI on the
   whole library).
5. **Show the result**: the app at `http://ubuntu:5173`, and for a drawing change a gallery (old, new, one sentence
   per case on what to look at).
6. **Keep the checks green**: `pytest` in the container (on the CPU when another project holds the GPU), the golden
   files (changed on purpose and said why), `tsc`, `lint`, `vite build`, the browser checks of
   `context/04-local-development.md`, `scripts/docs/check-links.py`.
7. **Update the documentation** the phase makes stale.
8. **Report**: the phase report and the walkthrough.

## 6.3 Branch

The standing rule: each phase on its own branch `feat/phase-N` made from `master` (`feat/04-phase-N` to keep it apart
from earlier implementations' names); after the user's ok, merge into `master` locally and push `master`. No pull
requests.

# 7. Phases

## Phase 1: The sheet page

The five page items of the brief (section 4.1). Frontend only.

1. Study: the header, the floating toolbox and its hidden state in the browser (why it does not come back), the
   cursor and the click to seek, the zoom path; list them in the report.
2. Command + scroll and the trackpad pinch zoom the sheet over the sheet; the sheet is laid out again to the window;
   the requests are grouped.
3. The AI symbol (`AiMark`) next to the title instead of the badge; tooltip "Enhanced with AI".
4. The header toolbox: one list of buttons in both places; the header stays at the top while scrolling.
5. The hidden floating toolbox comes back (the fix, and the header button).
6. The cursor is dragged and dropped, across lines; `grab` and `grabbing`; seeking on release.
7. Checks: a browser check of the new hooks on a temporary copy (zoom by wheel, header buttons, hide and show, drag
   of the cursor across a line break), the existing checks, the screenshots; the user checks in the browser.

## Phase 2: The decoration-note rule

The rule of section 3.1 on every sheet (sections 3.2 and 4.2). Backend only; no AI call.

1. Study: the decoration notes of My library today (count per song, per hand, by figure), and what the new rule makes
   of them: how many stay, how many become written notes, how many are lengthened. The passages of the two images in
   7 Years.
2. The rule in `find_graces` and the lengthening step, with the user's marks winning; unit tests of each row of the
   table of section 3.1; the golden files updated on purpose.
3. Every sheet: the rule also on the stored sheets (case 1 of `build`), with the measures of section 4.2.
4. Gallery `gallery/phase-2/`: the passages of the two images and others from My library, old and new, drawn by the
   engine and checked zoomed in; the user checks it, and 7 Years in the browser.

## Phase 3: Simplicity in the AI's sheet, and 7 Years

Prompt version 6 and the limits on note changes (sections 3.3, 3.4 and 4.3).

1. Study: the passages of `left-patterns.png` and `complex-fast-notes.png` in 7 Years (their frames and notes); how
   often a broken pattern and a far quick chord occur in My library (a count, to pick the gallery cases and the
   check's limits).
2. Prompt version 6: the decoration-note text, the rules of simplicity, the amateur pianist rule, with an example.
3. The check of note changes for a whole-song window, and the feedback; tests with recorded answers (no credits).
4. Storing the left-out and added notes in `notes.pmn` at the end of a whole run, like `apply_stretch`; the record
   counts them; undo; a run again reads the new notes.
5. A test on a temporary copy of 7 Years: first the windows of the two images (ask the user, cents), then the whole
   song (ask, about $0.70). Gallery `gallery/phase-3/`: the AI's sheet with prompt 5 and with prompt 6, the four
   image passages first; checked zoomed in.
6. The real run on 7 Years (My library version), after the user's ok: first the question of section 3.4 (the edit
   copy in the Personal Vault). About $0.70.
7. The user checks 7 Years in the browser.

## Phase 4: The Enhance with AI dialog and Simplify

Sections 3.5 and 4.4. Backend and frontend.

1. Study: the stretch path today (`EnhanceStretchDialog`, `start_stretch`, `write_stretch`), the size of one-hand
   windows, how to find the earlier passage like the current one; the list of what each batch sees.
2. The dialog: the two tabs, the hand of a stretch, the four whole-song choices, the cost.
3. A stretch with one hand: the other hand fixed (prompt, check, splice); tests with recorded answers.
4. Simplify: `write_simplify` batch after batch with what the earlier batches did; the check; storing, the record,
   one step of undo; tests with recorded answers.
5. Tests with the AI on a temporary copy (the user asked before each): a stretch of one hand, then Simplify left on
   a song that has not been run with prompt 6; gallery `gallery/phase-4/`.
6. Checks: a browser check of the dialog on a temporary copy (no AI request: a stand-in or the dialog only), the
   existing checks; the user checks in the browser.

## Phase 5: Documentation and closing

1. The documentation made stale and not yet updated by Phases 1 to 3: the core's
   [`README.md`](../../../aitu-backend/src/aitu_backend/sheet/README.md) (the decoration-note rule, prompt version 6,
   the note changes of a whole run), `context/frontend/rendering.md` and the other frontend pages that describe the
   sheet page, `context/implementations/README.md`, `context/00-index.md`.
2. `04-context.md`: what this implementation changed, for later ones (as `03-context.md`), and the row of the
   decoration-note rule in `03-context.md` section 2 pointed at it.
3. The final checks; the open points.

# 8. Risks

| Risk | What to do |
|---|---|
| The rule on stored sheets changes more than the decoration notes (beam groups, the user's marks) | Phase 2 compares the drawing before and after on every stored sheet of My library: only the decoration-note columns and their beams may differ |
| Applying the rule at draw time is slow | measured in Phase 2; the cache of drawings stays |
| The AI changes too many notes, or the melody | the check's limits (section 4.3), measured on the test copy; the gallery shows every changed note |
| Credits | a few windows first, the user asked before each run; only 7 Years runs with the AI |
| The real 7 Years run lands on the edit copy and its edits | Phase 3 asks first (section 3.4) |
| A Command + scroll that the browser also uses (the page zoom) | `preventDefault` on a non-passive listener over the sheet only; checked on the Mac's browser by the user |

# 9. Changes made by the phases

**Phase 1** (2026-10-27; report [`04-implementation-phase-1.md`](04-implementation-phase-1.md)):

- The hidden floating toolbox did come back, but its round button sat at the toolbox's left end, about 600 px from
  the hide button, white on the notes, with a lightning icon: the user did not see it. It now sits where the hide
  button was, with a border and an eye icon.
- The floating toolbox's hidden state is kept in the browser (its buttons are in the header now); the header's
  extra button hides and shows it.
- On a sheet the AI has not enhanced, the header shows the hollow symbol ("Not enhanced with AI yet"), as the
  Projects page does.
- A press on the cursor that does not move stays a click (it picks the notehead under it, or seeks): after a click
  on a note the cursor stands on that note's column, and a cursor that always won would hide those notes from the
  pick. A drag that starts on the cursor still never picks notes or draws a box.
- New browser check `npm run check:frames-page` (the header, the floating toolbox hidden and shown, the wheel zoom,
  the cursor dragged), listed in `context/04-local-development.md` with the others.

**Phase 2** (2026-10-27; report [`04-implementation-phase-2.md`](04-implementation-phase-2.md)):

- "A run of three or more" is today's chain (semicorcheas or shorter, two figures or more shorter than the next
  note, sounding just before it). The lengthening walks back only over notes more than two figures shorter, and it
  does nothing when that run has three columns or more, so the end of a run (semicorcheas, then a semifusa and a
  fusa before a negra) is never lengthened. A pair that is not all fusas (a fusa and a semicorchea before a negra)
  is written with its own figures.
- Every sheet (section 3.2): the drawing lays every stored sheet again on its notes (`build.reapply`, case 1 as case
  2). Measured first: with the old rule this gives every stored sheet back, note for note, in 0.04 to 0.13 s. A text
  an edit just stored (already laid again) is drawn as it is, so one edit stays at about 0.28 s.
- New, small: two written notes that a stored sheet held as one pair of decoration notes get one beam (the AI never
  grouped a decoration note, so they printed two flags side by side; 27 pairs). Only once: an edit stores them as
  written notes, and a beam the user takes away stays away.
- The prompt's sentence on decoration notes stays as it is until prompt version 6 (Phase 3); the AI's input does not
  change with the rule.

**Phase 3** (2026-10-27; report [`04-implementation-phase-3.md`](04-implementation-phase-3.md)):

- The answer **declares** each note it leaves out or adds in a comment line (`# leave out f1822 G2`, `# add f4556
  D1`), so the check tells a change made on purpose from a note forgotten by mistake (still an error).
- The limits of the check (measured on My library and the test): a note left out keeps a note of its column within
  an octave; a note added joins a column where its hand plays a note of the target, within an octave of it, with the
  name of a note of that column or of the 8 columns of its hand around it; at most a tenth of the window's notes
  (4 at least).
- **Places to check** (new): the first whole-song test completed the octavas but kept the far Sol 2 that the window
  test had left out. The app now finds the far quick chords and the broken octava runs by rule and lists them in the
  window's prompt; the AI still decides each one. In 7 Years it finds exactly the three places of the images.
- **Undo**: a whole run still starts the steps again, with one step, "Notes the AI added and left out": its undo
  puts those notes back and lays the AI's sheet on them; the AI's mark, hands and reading stay. A whole run is not
  undone as a whole.
- A run again asks the reference figure again, as before: the test chose 500 ms (480 before), 10 figures of 1,456
  changed.
- The real run goes on the edit copy in the Personal Vault (`477086a0`), the user's answer of 2026-10-27; the My
  library version changes when the user saves the copy to the library. Done: the same six notes as the test, $0.63,
  the user's figures, lyrics and titles kept.
- After the gallery, the user asked for the **Enhance with AI dialog** and **Simplify** (section 3.5): a new Phase 4;
  the documentation and closing become Phase 5.

**Phase 4** (2026-10-27; report [`04-implementation-phase-4.md`](04-implementation-phase-4.md)):

- A Simplify batch **answers only the change lines**, each with its reason (`# add f4556 D1: D2 alone in a run of
  D1+D2 octaves`), or `# no change`, not the notes of the hand (section 4.4 said the notes): the output is what costs,
  the hands, beams and clefs cannot drift, and the reasons are what the later batches read. The rules lay the sheet on
  the changed notes (beam groups, clefs).
- Batches of 24 to 32 s (7 Years: 8 per hand, against 15 windows of a whole run). Each sees every change before it with
  its reason, the earlier passage most like it as simplified, with its changes (runs of 4 columns with the same keys),
  and the last 8 s of the previous batch as simplified.
- Measured cost: $0.10 for the left hand of 7 Years, $0.21 for Moonlight Shadow; the dialog shows an estimate per run
  (`GET /sheet/{uuid}/llm/costs`). The record keeps each Simplify run with its change lines (`Record.simplified`).
- A stretch's **Right** / **Left** (the range toolbox, the dialog) now means that hand only, the other fixed; before,
  it only told the AI which hand the user had picked.
- New browser check `npm run check:enhance-dialog` (a stand-in answers the requests that would start the AI).
- The AI changed a note's name (La 3 to Fa 3 at 2:09.56 of 7 Years) to match the other times the chorus plays. The
  user's decision (2026-10-28): keeping the name is a recommendation; Simplify may change it when the earlier passage
  like this one has the new note at the same place (found by the 2 columns around it), and the check refuses it
  otherwise (report section 8).
- After the user's check: a run of one hand veils only that staff on the page (the segments carry `staff`).

