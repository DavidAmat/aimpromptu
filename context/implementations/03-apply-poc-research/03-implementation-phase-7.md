# 03: Phase 7 report: the note and range tools

Plan: [`03-plan.md`](03-plan.md) section 7, Phase 7. Checklist: [`03-checklist.md`](03-checklist.md). Branch
`feat/migrate-new-logic` (level with `master` at the start: nothing to merge). Written 2026-10-25 on the Ubuntu
machine. **Built 2026-10-25**; the user checked the gallery ([`gallery/phase-7/index.html`](gallery/phase-7/index.html),
served at `http://ubuntu:8715/phase-7/`): "all good". **Done 2026-10-26**: the user checked the tools in the browser ("all good") after the two reworks of section 9; the
branch was merged into `master`.

# 1. Summary

| Task | Result |
|---|---|
| 7.1 Study and inventory | Section 2: every tool of the old note and range toolboxes, its use in the 46 saved `sheet.json`, and its place in the new sheet. Four questions to the user (section 3), all answered with the recommendation. Transpose figures and notes, Copy, Record this passage and Start a new part moved to Phase 8 (they belong to the sheet toolbox and the screens of Phase 8) |
| 7.2 The tools on the edit model | `part_sheet/reading.py` (pure edits on a frames sheet), `edits.edit_reading` (change, lay again on the notes, check, store, one step), `edits.remove_notes`; routes `POST /sheet/{uuid}/reading`, `/remove`, `GET /sheet/{uuid}/stretch` (section 4) |
| 7.3 Engine features | None needed: the engine already drew fingers, the five ornaments, 15ma and 15mb. The core gained the user's marks (`fg3`, `fix`, `asgrace`, `nograce`) in F1, `assign_figures` and `find_graces`, and `assemble(join=False)`; `frames.check` allows an 8vb in the bass clef |
| 7.4 The range selection | The strip above the upper staff of each line (click, drag, Shift-click), a lavender band over the staves in scope (Both / Right / Left), `FramesRangeToolbox.tsx` (Key, Clef, Octave); the two selections hand over to each other |
| 7.5 Enhance with AI of a stretch | `llm.frames.write_stretch`, `stretch_request`, `splice`; `job.start_stretch`; `POST /sheet/{uuid}/llm/stretch`; the ✨ of both toolboxes and `EnhanceStretchDialog.tsx`. One real request on 7 Years: 9 s, $0.0144, one step of undo |

# 2. The study (task 7.1)

## 2.1 The old toolboxes, their use, and their place in the new sheet

Use = the saved `sheet.json` that carry the field, of 46 (projects, library versions, public and request parts; a
project and its library version count twice). Read only, 2026-10-25.

| Tool (old) | Use | New sheet |
|---|---|---|
| Figures (7 + back to the sheet's) | 2 sheets, 14 chords | Kept: `fix` + the figure; the rule keeps it, never a grace note |
| Finger 1 to 5 | 0 | Kept: `fg3`; on one chord, from the thumb in the right hand and from the little finger in the left (the old sheet gave the lowest note the smallest number in both hands) |
| Hand Right / Left | (notes.pmn) | Phase 6 |
| Beam join 🔗, break ✂ | 2 + 2 sheets | Kept: join (a toggle: on one group already, the beam goes away), cut or join to the group before. A group must hold one figure (the user's rule of Phase 2) and at most 8 notes |
| Even spacing = + − | 2 sheets (1 song) | **Dropped** (the user) |
| Decoration (unplayed grace note on a keyboard) | 0 | **Replaced** by the grace note switch (the user) |
| Print smaller (cue) | 2 sheets (1 song) | **Replaced** by the grace note switch (the user); the engine draws only grace notes small |
| Trill | 0 (Find trills: none saved) | Kept, with mordent and turn (the format's `orn` model: the first onset carries the ornament, the others are played inside it), plus arpeggio and fermata on chords |
| Take off the page 🗑 | 2 sheets, 14 notes | Kept: marked removed in `notes.pmn` at once (the old sheet waited for Save), undone by the log |
| Copy the frames of these notes | | Phase 8 (copy and paste) |
| Select the frames / notes | | Kept |
| Range: Key (+ fewest accidentals) | 2 sheets | Kept |
| Range: Clef (+ clef rule) | 12 sheets, 92 changes (most from the first write's rule) | Kept, with **Clefs by the rule** |
| Range: Octave (4 kinds, hide, remove) | 42 sheets, 359 brackets (8vb 139, 15mb 65, 8va 115, 15ma 40), 0 hidden | Kept the four kinds and remove; **hide dropped** (the user) |
| Range: Spacing (25 to 400 %) | 1 sheet | **Dropped** (the user) |
| Range: Speed | 0 | **Dropped** (the user) |
| Bracket ends dragged on the page, corner marks | | **Dropped** (the user): the range selection does the same |
| Record this passage, Start a new part, Copy | | Phase 8 (Recording in Sheet, parts, copy and paste) |
| Sheet toolbox: Transpose figures and notes | | Phase 8 with the sheet toolbox (the plan listed them in Phase 7 too) |

## 2.2 What the new sheet had

The edit model of Phase 6 (`part_sheet/edits.py`): a hand move writes `notes.pmn` and stores `sheet.f1` laid again on
the new hands, one step of `sheet.edits.json` with a line patch of `sheet.f1`. The figures, grace notes, beam cuts
and spelling are rules run by `assemble` after the decisions (Phase 4), so a figure set by the user had no place:
`assemble` cleared every figure. `Note.finger` existed (drawn by the engine since the research's phase 10) but was
not in F1. An algorithm sheet was never stored: a stored `algorithm` record was computed again when the hands moved.

# 3. The user's answers (2026-10-25)

The four questions (one product choice each, recommendations first); every answer was the recommendation:

1. **Spacing and speed**: drop even spacing, the room of a stretch and speed changes. The measured spacing of
   Phase 3 stays the only spacing.
2. **Small notes**: a grace note switch on played notes ("write as a grace note" / "write as a normal note",
   overriding the rule); print smaller and the unplayed decoration are dropped.
3. **8va brackets**: drop hiding a bracket and dragging its ends.
4. **Enhance it again with AI after reading edits**: the AI may change its own kinds (beams, clefs, 8va, armaduras,
   ornaments), as it may the hands (Phase 6); the user's fingers and figures set by hand (and the grace switch)
   stay.

# 4. The backend

## 4.1 The core (`aitu_backend.sheet`)

- `Note.fixed`, `Note.grace_rule` (data.py); F1 tags `fg1`..`fg5`, `fix`, `asgrace`, `nograce` (written after the
  other tags, part of the chord grouping so notes of one chord with different fingers are separate tokens).
- `assign_figures` keeps the figure of a chord with a `fix` note (after the run mode). `find_graces`: a column with
  `asgrace` is a grace note of the next non-forced column of its hand whatever its figure (a chain of them too, past
  `MAX_GRACES`); `nograce` or `fix` columns are never graces and break a chain. With no marks both behave exactly as
  before (the golden files and the Phase 2 to 6 tests pass unchanged).
- `assemble` carries `finger`, `fixed` (with its figure) and `grace_rule` from the decided notes; `join=False` skips
  `join_ottavas` (used by `build.reapply`: a stored sheet's lines were joined when it was written, and the user's
  removed line must not come back).
- `frames.check`: "8va in the bass clef" now means `ottava > 0` (8va, 15ma). An 8vb under low notes is allowed; the
  LLM checker `_structure` keeps its own rule (no octave line in the bass clef).
- `llm.frames.window_prompt(request=...)`, `stretch_request`, `write_stretch`, `splice` (section 4.4).

## 4.2 `part_sheet/reading.py`

Pure edits on the sheet the page shows now; each returns the step's label or raises `Refused` (the reason for the
page). Chords: picking one note names the whole chord of that hand for figures, beams, the grace switch and
ornaments; fingers are per note. A stretch is `[start, end)` in frames; the armadura, the clef and the octave line
in force at `end` come back there (or the header changes when the stretch starts at the first note).
`plan(action, ...)` maps one request of the page to `(change, holds)`; `holds(settled)` says why the settled sheet
does not hold what was asked (a beam group the figure rule cut; a forced grace note with no note after it).

## 4.3 `part_sheet/edits.py`, `store.py`, `build.py`, `job.py`

- `edit_reading(part, change, holds)`: under the part's lock, `change(f1.read(drawn.text))`, then
  `build.reapply(sheet, starting_hands)` (the rules run again; `same` matches keep every decision), `holds`, and a
  safety net: no problem of `frames.check` that the sheet did not have before. Stored with `Record.edited = True`
  (an algorithm sheet becomes a stored record), one step (`_Step` with only the sheet patch).
- `Record.edited`, `Record.stretches`, `Record.decided` (enhanced or edited): `build._compute` and `move_hands` lay a
  decided sheet again on new notes; only a plain algorithm record (a run that wrote no window) is computed again.
- `remove_notes(part, refs)`: `event.removed = True`, `save_edit(notes_changed=True, hands_changed=False,
  sheet_follows=True)`, a decided sheet laid again; `_Step.removed` (`id -> (before, after)`), walked by `_walk` like
  the hands (a note changed since by something else stays).
- `job.start` keeps the user's marks of the sheet before the run (`build.user_marks`, `build.with_marks` on the parts
  before `assemble`, in `LiveRun.text()` too, so they do not blink during the run); the new record is `edited` when
  marks were carried.
- `job.start_stretch` (same job key as a whole run: `job_of` finds it, so every edit answers 409 meanwhile and the
  page shows its lock): the notes with the hands of the sheet now, a `LiveRun` whose one provisional segment is the
  stretch (`working`), `write_stretch`, then `edits.apply_stretch` (hands into `notes.pmn` for the notes the sheet
  holds, all of them first when the hands were never saved as a whole; the spliced sheet laid again; record: an
  algorithm source becomes `mixed`, `usd`, `requests`, `stretches += [start, end, words, usd, written]`; one step
  "Enhance a stretch with AI"). The job's summary: `stretch` `ok`, `failed` (no reply accepted, nothing stored) or
  `stale` (the notes changed meanwhile).

## 4.4 The stretch request

Changed after the user's check (section 9): the target is now the stretch as it is, the user's words come first,
and the answer may leave notes out. As first built: one window conversation: title "A stretch of song ... to write again", the decided context = the sheet before the
stretch (4 s) as it is now (user marks stripped), the target = the algorithm's notes of `[start, end)` on the current
hands, shown with those hands (the Phase 6 suggestion line), the look-ahead (4 s), then "## The user's request" (what
was picked: the whole target, one hand's notes, or the picked notes named `f120 C5`, at most 40; the words, at most
1,000 characters; "do what they ask as far as your rules allow: the format, the onsets of the target, the limits of
a beam group and of the ledger lines stay hard rules"), then the usual answer section. `check_answer` and the beam
guard as for a window, up to 3 replies. `splice` replaces the notes, clefs and armadura of the stretch with the
answer's (beam numbers shifted to stay unique; the user's marks kept by `(frame, midi)`). The cached instructions
(version 5) did not change.

## 4.5 Routes (`api/sheet.py`)

`POST /sheet/{uuid}/reading` (400 with the reason when refused), `POST /sheet/{uuid}/remove`,
`GET /sheet/{uuid}/stretch`, `POST /sheet/{uuid}/llm/stretch` (202; 409 busy or not set up; 403 without the right to
write). `GET /sheet/{uuid}` adds to each note `figure`, `beam`, `grace`, `fixed`, `graceRule`, `finger`, `ornaments`,
`ottava`, and the sheet's `reading` (armaduras and clefs); its `segments` list the stored stretches after the
windows. `documentation/services/backend/endpoints.md` section 4.1.

# 5. The frontend

- `FramesNoteToolbox.tsx`: rows Figures (7 + ⌫), Finger (1 to 5 + ⌫), Hand, Beam (🔗 join / remove, ✂ cut / join to
  the group before), Grace (switch + ⌫), Marks (tr, mord, turn | arp, ferm), 🗑; title bar ✨ (Enhance these notes
  with AI) and *Select the frames of these notes*. Pressed states from the drawn notes' reading.
- `FramesRangeToolbox.tsx`: Both / Right / Left, tabs Key (select of the 15 armaduras with the old labels, ✓, 🗑,
  *Use D major here (n fewer signs)* from `GET /stretch`), Clef (per hand in scope, 🗑, **Clefs by the rule**),
  Octave (8va, 15ma, 8vb, 15mb per hand, pressed again to remove; 8va and 15ma disabled over a bass clef); dots on the
  tabs; title bar ✨ and *Select the notes in this stretch*.
- `FramesSheetView.tsx`: the strip (`STRIP_SPACES` = 3.5 staff spaces above the upper staff, or the ink above it,
  never above the line before), shown faintly under the pointer (`data-range-strip`); a press there that is not on a
  notehead marks a stretch (drag across columns and lines; Shift extends); the band per line over the staves in
  scope (`data-range-band`). The reveal now prefers the segment with the same start and end as the one that was
  `working` (a stretch), then a window with the same start.
- `FramesSheetPage.tsx`: one selection at a time; the range toolbox opens left of the band (`clearOfRange`, two
  animation frames after the band is drawn); Delete takes the picked notes off; Escape drops both selections.
- `EnhanceStretchDialog.tsx`: the words (optional, 1,000 characters), ⌘Enter sends.
- `useFramesSheet.ts`: `enhanceStretch`, and `notice` from the job's `done` summary (`failed`, `stale`).
- `readingTools.ts`: figures as numbers, armaduras as fifths, ornaments, the chord and column helpers.

# 6. Measurements

| What | Value |
|---|---|
| The reading edits in memory on 12 stored AI sheets (40 random edits each, `build.reapply` included, no drawing) | median 39 to 70 ms per edit (clef 39, figure 49, clef rule 68, a spliced stretch 70), max 137 ms; no error; 0 rule broken once the 8vb rule was fixed |
| One hand move, click to new drawing (`check:frames-edit`, 4 moves) | median 315 ms (backend 222, page 106); Phase 6 measured 231 ms over 10 moves. The answer grew from about 540 to 690 KB (each note now carries its reading); the machine was also busy (another project on the GPU) |
| A stretch with words, live (`check:frames-tools --live`, 7 Years, about 4.5 s of music, both hands) | 9 s and 11 s from the click to the stretch written; $0.0144 for one request |
| The user's stretch (left-hand octaves made single notes), two wordings (section 9) | one reply each, $0.0098 and $0.0106 |

# 7. Checks

| Check | Result |
|---|---|
| `tests/test_sheet_reading.py` (new, 16 tests) | Figures (stored, edited record, undo, back to the rule), fingers (one note, a chord, removed; left-hand order in a pure test), beams (cut, join again, join two, take away, refusals), the grace switch (on, off, back, refused at the last note), a trill (hidden onsets, round trip exact, printed as notes again), arpeggio, notes taken off and undone, an armadura for a stretch and its hint, clefs and the clef rules, octave lines and the bass-clef refusal, a reading edit kept through a hand move, a new AI run keeping fingers and figures and writing beams again, a stretch with words (the prompt, only the stretch changed, one step, `mixed`, undo), a failed stretch (nothing changes), no edit and no second stretch while it runs |
| Golden files and the sheet tests of Phases 1 to 6 | unchanged, all pass |
| Backend, full run in the image on the CPU | 1,366 tests: 1,362 passed, 1 skipped (needs a GPU), 3 failed: `test_the_worked_example_at_00_46_prints_three_equal_corcheas` (failing since Phase 0) and the two `test_transcription_transkun.py` tests, which load the model's checkpoint saved on CUDA and fail when the GPU is hidden (not touched by this phase) |
| `black`, `flake8` on the changed files; `npx tsc -b`, `npx eslint src` | clean |
| `npm run check:frames-tools` (new) | all passed, with and without `--live` (section 6) |
| `npm run check:frames-edit` | all passed after one change: its box now starts inside the upper staff (above it is the strip that marks a stretch) |
| `npm run check:frames-sheet`, `npm run check:play` | all passed |
| The drawings | the 13 cases of the gallery and the browser check's pictures looked at zoomed in and compared with the notes (section 8) |
| `scripts/docs/check-links.py` | passed |

# 8. The gallery and what the drawings showed

`scripts/tools_gallery.py` applies each tool in memory (the same `reading` functions and `build.reapply`) to the AI's
sheet of 7 Years and draws the passage before and after with the engine; nothing is written. The first version used
poor passages for three range cases (an 8va over a low chord, an 8vb over a left hand already in the staff, a
treble clef over low notes; and 2 sostenidos in a passage in 2 bemoles, which put a sign on every note): each drawing
was correct for its data but read as a mistake, so the cases now use a high run (8va), the lowest run of the song
(8vb), a high left-hand passage (treble clef) and 1 bemol.

Found by the zoomed look and fixed: a trill kept its first note in the beam group across the hidden onsets (the
safety net refused it: `frames.check` "beam group broken"); a trilled note now leaves its group. The 8vb refusal in
the bass clef (section 4.1).

# 9. After the user's first check: a stretch that asks to remove notes (2026-10-25)

The user marked a left-hand stretch of an AI sheet (Mi 1 / Mi 2 octaves mixed with single Mi 2) and asked "simplify
this left hand, keep the current rythm but make all the notes be single notes instead of the current octave notes".
The run was accepted and stored ($0.036) but changed nothing visible. Two causes in the first design: the checker
demanded every onset of the target back ("the onsets of the target stay hard rules"), so the AI could not take the
lower notes away; and the target showed bare notes, so "keep the beam groups" had nothing to refer to.

What changed (the user asked that their words be of the utmost importance):

- `write_stretch`: the target is the stretch as it is now (`current`'s notes with hands, beams, clefs, 8va,
  ornaments; the user's marks stripped). `window_prompt(request=...)` titles it "this stretch of the sheet as it is
  now: write it again as the user asks" and leaves out the Phase 6 suggestion line.
- `stretch_request`: "The user's request: it comes before everything else"; the instruction is "of the utmost
  importance" and overrides the usual choices and general rules; the list of what the answer may do (hands, beams,
  clefs, 8va, ornaments, **take notes off the sheet** by leaving them out, with the octave example) and may not do
  (add a note, move one to another frame or pitch); only the format and three hard limits stay. Without words, the
  request keeps every note as before.
- `check_answer(drop=True)` (a stretch with words): missing onsets are allowed, not an empty answer.
- `edits.apply_stretch`: the notes of the stretch the answer left out are removed in `notes.pmn` in the same step
  (`_Step.removed`), so Undo brings them back.

Tested on the user's stretch with real requests, nothing stored: with their words and with the words of their run,
one reply each, accepted at the first check, $0.0098 and $0.0106; the AI left out the four Mi 1 of the octaves and
kept every beam group, the hands and the rhythm. The cached instructions (version 5) did not change. Test:
`test_a_stretch_with_words_may_leave_notes_out_and_undo_brings_them_back`.

## 9.1 The second check: simpler, with pitches and figures (2026-10-26)

With the first fix the AI made every octave a single Mi 2 but left a lone low Mi 1 as it was, because it could not
change a pitch; and it could not change figures at all. The user: the purpose of an edit is almost always a sheet
simpler to read and to play, so the AI must favour uniform solutions (a "single note" is the same note everywhere),
and it must be able to change figures ("make all the octaves negras").

- `stretch_request` adds "The purpose behind it": simpler to read and to play, uniform repeating patterns, the
  instruction applied to every note it is about, the same pitch for the same role (the Mi 1 / Mi 2 example), a
  named figure written everywhere it applies. With words the answer may also change a pitch (a note left out and
  one written at the same frame), add notes anywhere in `[start, end)` (`check_answer(free=...)`), and set figures
  (the figure written is the one printed).
- `edits.apply_stretch`: an added note becomes a `NoteEvent` (a new id; the onset of the drawn column it joins, or
  its frame; a length of its figure at the reference figure; the median velocity of the stretch; its hand), in the
  same step (`removed` before `True`, after `False`, so Undo takes it off). After settling, every figure the AI
  wrote that the rule would print otherwise is set as by hand (`fix`), even against the grace rule unless the note
  was a grace note already; notes are looked up a frame or two away.
- `build.reapply`: a stored note whose drawn column moved by one or two frames is found there (the first note of an
  uneven octave taken off moves the column to the other note's onset); before, it lost its beam group.
- Measured with real requests on the user's stretch (in memory, then end to end on two temporary copies, deleted):
  the user's words: every note Mi 2 (the lone Mi 1 too), the same figures and beam groups, $0.0316 in memory; the
  wording given to the user: the same, $0.0071; "Mi 1 + Mi 2 octaves as negras, one on each beat": six octave
  negras, 15 frames apart, $0.0127. Each accepted at the first check. The first end-to-end run showed two faults
  the unit tests had not (figures of single notes shortened by the rule, a moved column losing its beam), fixed
  above. Tests: `test_a_stretch_with_words_may_change_pitches_add_notes_and_set_figures`,
  `test_a_stretch_answer_may_add_notes_only_inside_the_stretch`.

# 10. Notes for later phases

- **Phase 8.** Transpose figures changes `quarterMs`, which the spacing model reads too (`gap(t / quarter_ms)`): the
  page will be wider or narrower after it, unlike the old sheet (D-18 "nothing moves"). Transpose notes changes
  every midi, and `build.reapply` matches notes by column and key: the stored sheet must be transposed with the notes
  (`splice`-like, or match by note id), or every decision is lost. Copy, Record this passage and Start a new part
  belong in the range toolbox's title bar; Find trills can write `tr` + `orn` with `reading.set_ornament`.
- **Back to the figures of the rule** gives the figure back, not a beam group the fixed figure broke (beams are
  decisions, not rules); Undo gives both back. Said in `annotations.md`.
- **Undo of a stretch the AI wrote** takes back its hands and its sheet, not the record: an algorithm sheet stays
  `mixed` (and **Enhanced with AI**) and keeps the stretch in `Record.stretches`. The cost of a stretch that failed
  is not recorded anywhere (the job's summary has it).
- **The strip** is at most 3.5 staff spaces above the upper staff; over high notes a press picks the notehead
  first. Lines very close together leave a thin strip.
- **The answer of an edit** is about 690 KB of JSON for 7 Years (gzipped on the wire): the per-note reading could
  leave out its default values if the size matters.
- **Phase 9.** The old `sheet.json` marks that have a place now: overrides (`fix`), fingers (`fg`), beam breaks and
  joins, key changes, clef changes, ottavas (all four kinds), trills (`tr` + `orn`), hidden notes (removed in
  `notes.pmn`). Spacing, even spacing, speed changes, cue ranges, decorations and hidden brackets have none (dropped).
- The scratch scripts (the stress run, the finders, the screenshots) are not kept; their numbers are in sections 6
  and 8.

# 11. Documentation

- `aitu-backend/src/aitu_backend/sheet/README.md` sections 9 and 14; `part_sheet/__init__.py`, `build.py`;
  `context/backend/README.md`.
- `context/frontend/annotations.md` ("The new sheet"), `annotations-notes.md`, `annotations-stretches.md`,
  `rendering.md`; `context/07-database.md`; `documentation/services/backend/endpoints.md` (routes table, section 4.1).
- [`03-plan.md`](03-plan.md) sections 3.7, 4, Phase 7 and Phase 8 tasks, 8, 11; [`03-checklist.md`](03-checklist.md),
  [`README.md`](README.md), `../README.md`, `../../00-index.md`.
