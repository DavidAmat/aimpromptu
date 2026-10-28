# 04 · Phase 4: the Enhance with AI dialog and Simplify

Technical report, for the agents of the next phases. Plan: [`04-plan.md`](04-plan.md) sections 3.5, 4.4 and Phase 4.
Branch `feat/04-phase-4` (from `master` at `2deeefb`). Backend and frontend; no database change, no prompt change
(the system prompt stays version 6).

State: built and tested (2026-10-27); waiting for the user's check in the browser and one decision (section 8).

# 1. What was done

| Task | Result |
|---|---|
| 4.1 Study | Section 2; scratch scripts (sizes, places per song) |
| 4.2 The dialog | `aitu-frontend/src/pages/piece/sheet/frames/EnhanceDialog.tsx` (was `EnhanceStretchDialog.tsx`), `FramesSheetPage.tsx`, `useFramesSheet.ts` (`simplify`, the end notice), `api/sheet.ts` (`simplify`, `llmCosts`, `SongRun`), `navigation.ts` (`enhanceWithAi(run)`, `songRunOf`), `SheetTab.tsx`, `SheetPage.tsx` (`enhanceInCopy(run)`) (section 3) |
| 4.3 A stretch of one hand | `llm/frames.py`: `window_prompt(fixed=)`, `stretch_request(staff=)`, `check_answer(hand=)`, `write_stretch(staff=)`, `splice(keep=)`; `edits.apply_stretch(staff=)` (section 4) |
| 4.4 Simplify | `llm/frames.py`: `simplify_windows`, `like_before`, `simplify_prompt`, `check_simplify`, `write_simplify`, `Change`, `Simplified`; `part_sheet/job.py`: `start_simplify`, `costs`, `LiveRun.advanced`; `edits.apply_simplify`, `SIMPLIFY_LABELS`; `store.Record.simplified`; `api/sheet.py`: `POST /sheet/{uuid}/llm/simplify`, `GET /sheet/{uuid}/llm/costs` (section 5) |
| 4.5 Tests with the AI | Section 6; gallery [`gallery/phase-4/index.html`](gallery/phase-4/index.html) (`aitu-backend/scripts/simplify_gallery.py`) |
| 4.6 Checks | Section 7; new browser check `npm run check:enhance-dialog` |

# 2. Study (task 4.1)

- **The stretch path today**: `EnhanceStretchDialog` (the words) → `POST /sheet/{uuid}/llm/stretch` → `job.start_stretch`
  → `write_stretch` (one window conversation, both hands, `check_answer(drop, free)`) → `splice` → `edits.apply_stretch`
  (one step). The `staff` the range toolbox sent only told the AI which hand the user had picked; both hands could change.
- **The size of one-hand windows** (My library, 33 parts, the sheets as drawn): with batches of 24 to 32 s
  (`windows_of(span=(24000, 32000), max_onsets=300)`) one hand has 5 to 12 batches (7 Years: 8 per hand, against 15
  windows of a whole run); the largest target is about 5,000 characters (both hands) and 300 onsets. Input is cheap
  (the instructions are cached); the output (thinking and the answer) is what costs.
- **The answer**: a whole-run window writes back every note (1 to 2 thousand tokens). Simplify changes few notes, so a
  batch answers only the change lines of prompt 6, with a reason (section 5). The plan said "the answer writes only
  the notes of the simplified hand(s)"; changed (plan section 9).
- **Finding the earlier passage like this one**: a chorus repeats with the same keys in the same order, so the n-grams
  of 4 columns (the keys of the hand in each column) of the batch are looked for in the earlier columns; the earlier
  stretch of the same number of columns with the most matched columns wins (30 % at least, the latest on a tie,
  ending before the context). In 7 Years it finds the earlier chorus for batches 4, 5, 7 and 8 of the left hand.
- **Places per song** (the app's `places`, left hand, sheets of prompt 5): Moonlight Shadow 14, Poker Face 4, 7 Years 3,
  the others 0 to 2: Moonlight Shadow was the second test song.

# 3. The dialog (task 4.2)

- **Enhance with AI** (the header and the floating toolbox; **Enhance it again with AI** on an enhanced sheet) opens
  `EnhanceDialog`; the note and range toolboxes' buttons too. With notes or a stretch selected it opens on **A
  stretch**, else on **The whole song**; **A stretch** is off with nothing selected.
- **A stretch**: `Segmented` Both / Right / Left (from the selection: the hand of the picked notes when it is one, the
  range toolbox's hand), the words (optional), the status line ("The right hand stays as it is. About $0.06. Undo takes
  it back."), **Enhance with AI** (`stretch-confirm`). Sent as `StretchRequest.staff`.
- **The whole song**: a radio list, **Simplify the left hand**, **the right hand**, **both hands**, **Write it all
  again**, each with its cost (`GET /sheet/{uuid}/llm/costs`); chosen first: Simplify the left hand on an enhanced
  sheet, Write it all again otherwise. The button says **Simplify** or **Write it all again** (`song-confirm`).
- A version of My library: the stretch tab is off (no write right); the whole song opens the edit copy and starts the
  run chosen there (`enhanceInCopy(run)`, the navigation state `{enhanceWithAi: run}`; the old `true` is gone).
- The old `ConfirmDialog` of a whole run is gone (its words are the status line of **Write it all again**).
- The end of a Simplify run says one line (`notice`): "The AI added 4 notes and left out 2 in the left hand.", "The
  AI found nothing to simplify in both hands.", or why nothing changed. The hand comes in the job's summary.

# 4. A stretch of one hand (task 4.3)

`write_stretch(staff=1|2)`: the target holds that hand's notes of the stretch; the other hand goes after the target as
"## The left hand in this stretch (fixed: do not write it, it stays exactly as it is)"; `stretch_request` says the user
chose that hand only and the "may do" list says "write every note in the right hand" instead of "move notes from one
hand to the other". `check_answer(hand=)` adds the problem "N notes are written in the left hand ...: the left hand is
fixed in this stretch; write only R: notes". `splice(keep=)` leaves the kept staff's notes (beams, marks), its clef
changes and its starting clef as they were. `apply_stretch(staff=)` sets as by hand only the figures of the AI's hand.
A stretch with no note of that hand is refused (`ValueError`, the job fails before a request).

Changed meaning: the range toolbox's **Right** / **Left** now reaches the AI as "that hand only". The old test that
moved every note of a stretch picked as left hand into the right hand is now a both-hands stretch.

# 5. Simplify (task 4.4)

**Batches**: `simplify_windows(sheet, staff)`: `windows_of` on the notes of the hand (or both), `SIMPLIFY_MS = (24000,
32000)`, `SIMPLIFY_ONSETS = 300`. Each batch is the sheet as it is now (`build.current`), with the hands it draws.

**The prompt** (`simplify_prompt`, the system prompt unchanged): the task (the rules of simplicity only; the hands,
beams, clefs and figures stay; the other hand does not change); from batch 2 **the simplifications so far** (every
change line with its reason, "Make the same choices again ..."; or "None"); **an earlier passage like this one**
(`like_before`, drawn from the sheet as simplified so far, with its changes or "It needed no change"); **decided
context** (the last `SIMPLIFY_CONTEXT_MS = 8000` of the previous batch, as simplified); the **target**; the **places to
check** (`places`, as in prompt 6); the **look-ahead**; and the answer: change lines only.

**The answer and the check** (`check_simplify`): lines `# leave out f1822 G2: why` and `# add f4556 D1: why` (the
reason after a colon or a dash), anywhere in the reply, or `# no change`. A note left out must be a note of the target;
a note added must join a column of the target and not be there already; its hand is the hand of the nearest note of
that column (one hand: that hand). Then the limits of prompt 6 (`simplicity`: a column never emptied, an added note
within an octave and with a name of its column or of the 8 columns around, at most a tenth of the target). A reply
without lines or `# no change` is an error. A rejected reply gets `simplify_feedback` (the problems; "Write the
corrected change lines again"), at most `MAX_CHECKS` replies; a batch that fails changes nothing; an exception that is
not `SkipWindow` stops the later batches (the changes so far are stored).

**The sheet of the moment**: after each batch `_changed` writes its changes into the working sheet (an added note
copies the nearest note of its hand in its column: figure, beam group, 8va; its length is the longest note of its hand
there); `LiveRun.advanced(text)` makes it the page's sheet and its segments `llm` (done), `working`, `waiting`, so the
page veils the batch at work and reveals each one that comes back. Edits are closed meanwhile (same job key).
With one hand (Simplify left or right, a stretch of one hand) `LiveRun.staff` names it and each segment the page
gets carries `staff`: the veil and the reveal cover only that staff, the other hand stays as it is to see.

**Storing** (`edits.apply_simplify`, under the part's lock): `change_notes` (the notes left out removed, the added ones
written into `notes.pmn`), `save_edit(notes_changed=True, hands_changed=False)`, the working sheet laid on the new notes
(`build.reapply`: figures, beam groups cut, clefs fitted around new notes), `sheet.f1` saved, one step of undo
("Simplify the left hand with AI", "... the right hand ...", "Simplify both hands with AI"). The record:
`simplified.append([hand, added, left out, usd, written, change lines])`, `usd` and `requests` added; an algorithm
sheet becomes `mixed` (Enhanced with AI) when something changed. A run that changed nothing stores only its record
line. Notes changed meanwhile: nothing stored (`stale`).

**The job's summary**: `simplify` (`ok`, `none`, `stale`, `failed`, `gone`), `hand`, `added`, `leftOut`, `usd`, `note`.

**Cost estimates** (`job.costs`, `GET /sheet/{uuid}/llm/costs`): `USD_CACHE = 0.04` (the first request of a run writes
the instructions into the cache) plus `USD_WINDOW = 0.038` per request of a whole run, `USD_BATCH = 0.008` per batch
(twice for both hands), `USD_STRETCH = 0.02`. 7 Years: whole run $0.65 (measured $0.63 to $0.67), Simplify left $0.10
(measured $0.104). Moonlight Shadow measured $0.21 for an estimate of $0.10: its batches are denser (more thinking).

**Tests** (`tests/test_sheet_simplify.py`, stand-ins, no credits): the one-hand check and splice; the prompt of a
one-hand stretch and the left hand kept through it, with undo; the checker of change lines and its limits;
`like_before`; batch after batch, each prompt holding the changes before it; an earlier passage like the batch with its
changes; Simplify left through the job (notes, record with the lines, one step, undo, redo, the right hand untouched);
a run that changes nothing; the routes.

# 6. The tests with the AI (task 4.5)

The user agreed to the three before they ran (about $0.60 asked; $0.40 spent). Sonnet 5.5.

| Test | What | Result | Cost |
|---|---|---|---|
| 1 | In memory, 7 Years (My library version, prompt 5): Simplify left, batches 3 and 7 only; then a stretch of the left hand f4497 to f4603, "Make the octaves single notes." | Both batches accepted at the first reply: Sol 2 left out at f1822, D2 added at f4535, D1 at f4556, f4577, f4585, each with its reason (the same notes as prompt 6). The stretch: the left hand's octaves single notes (34 notes to 20), the right hand identical | $0.077 |
| 2 | Simplify left through the app on a temporary copy of 7 Years | 43 s, 8 batches; the six notes of prompt 6 (Sol 2 at f1822 and f5222; D2 at f4535; D1 at f4556, f4577, f4585) and one more (section 8); 0 hands moved, 0 new problems of `frames.check`; one step of undo | $0.104 |
| 3 | Simplify left through the app on a temporary copy of Moonlight Shadow | 91 s, 8 batches; 16 notes left out and 1 added, in 11 passages: the octaves that broke the left hand's single-note arpeggios lost their top note (G#4, F#4, B3), the same note each time the passage repeats; a quick A2+A3 before B3 kept A3 (simple.2); a lone C#3 in a run of C#2+C#3 octaves got its C#2. 0 hands moved, 0 new problems | $0.215 |

Tests 2 and 3 ran before the record kept the change lines (added after them), so the gallery lists their changes from
the data; test 1's reasons are in the scratch log. Both copies were deleted after the gallery was built.

The gallery (`docker exec -i aimpromptu-backend-1 python scripts/simplify_gallery.py --out
../context/implementations/04-app-enhancements/gallery/phase-4 --stretch <test 1 JSON> 1a16a836-... 4497 4603 2
--song "7 Years" 1a16a836-... <copy> --song "Moonlight Shadow" c0edc9b0-... <copy> --note "7 Years" 3239 "..."`):
the stretch of one hand (drawn with the rule's figures; the app also keeps the AI's figures), then each passage of each
song, before above after with a band, and the changes. Checked zoomed in (Playwright, scale 2): G3 alone before the
chord at f1822; La 2 + Fa 3 at f3239; the single-note arpeggios of Moonlight Shadow; A3 alone at f936 (a grace note).

# 7. Checks

| Check | Result |
|---|---|
| `pytest` (CPU, GPU hidden) | 1,267 passed; 2 failed, the two known Transkun tests (they load their weights only on the GPU) |
| Sheet tests (`tests/test_sheet_*.py`, `test_part_sheet.py`, `test_paste.py`) | 284 passed, before the AI tests |
| `black` | the changed files formatted |
| `tsc -b`, `eslint .`, `vite build` | pass |
| `npm run check:enhance-dialog` (new) | all passed |
| `check:frames-tools`, `check:frames-sheet`, `check:frames-page`, `check:frames-edit`, `check:frames-toolbox` | all passed |
| `scripts/docs/check-links.py` | 428 files, 0 broken links |

# 8. Open: a note that changed its name (a decision of the user)

At f3239 (2:09.56) the AI's Simplify left out A3 and added F3 in the left hand: the transcription has A2 + A3 there,
and the four other times this chorus plays (f1839, f2039, f2239, f2439) the left hand has A2 + F3. The AI made it match
them, which is what the user asked ("uses the same simplification"), but simple.3 says never to change a pitch to
another name, and the check let it pass: F is a name of the 8 columns around, and the column keeps A2 within an
octave. The walkthrough asks the user whether to allow it (formally: a name taken from the same place of the earlier
passage like this one) or to forbid it (a note left out and one added in one column of a hand keep the name).

# 9. Notes for later

- Documentation updated: the core's `README.md` (section 14: a stretch of one hand, Simplify), `context/backend/README.md`,
  `context/frontend/rendering.md`, `documentation/services/frontend/components.md`,
  `documentation/services/backend/endpoints.md`, `context/04-local-development.md` (the new check).
- Phase 5 still has `04-context.md`, `context/implementations/README.md`, `context/00-index.md`.
- A Simplify run is not saved batch by batch, like a whole run: a backend reload loses it.
