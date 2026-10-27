# 04 · Phase 3: simplicity in the AI's sheet, and 7 Years

Technical report, for the agents of the next phases. Plan: [`04-plan.md`](04-plan.md) sections 3.3, 3.4, 4.3 and
Phase 3. Branch `feat/04-phase-3` (from `master` at `b54f1e7`). Backend only: no frontend file, no database change.

State: done (2026-10-27); 7 Years checked by the user in the browser.

# 1. What was done

| Task | Result |
|---|---|
| 3.1 Study | Section 2; `aitu-backend/scripts/simplicity_gallery.py --study` and `--case PART FIRST END` |
| 3.2 Prompt 6 | `sheet/llm/prompt/frames/instructions.md` and `VERSION` (section 3); "Places to check" in the window prompt (section 4) |
| 3.3 The check | `llm/frames.py`: `declared`, `simplicity`, `check_answer(simplify=True)` (section 5) |
| 3.4 Storing | `Part.added`, `placed`, `assemble`, `FramesSong.changes`; `part_sheet/job.commit(changes=)`; `edits.change_notes` (shared with `apply_stretch`), `edits.record_run`; `store.Record.added`, `left_out` (section 6) |
| 3.5 Test | Windows in memory, then the whole song on a temporary copy, twice (section 7); gallery [`gallery/phase-3/index.html`](gallery/phase-3/index.html) |

# 2. Study (task 3.1)

**The images in 7 Years** (My library version `1a16a836`, the AI's sheet of prompt 5, reference figure 480 ms):

- `complex-fast-notes.png`: the left hand's Sol 2 + Sol 3 (G2, G3), a semicorchea at f1822 (1:12.88), 200 ms before
  the negra Si-b 3 + Re 4 (Bb3, D4) at f1827. G2 is 15 semitones under Bb3. The same passage again at f5222 (3:28.88).
  Old rule: a pair of decoration notes; Phase 2: a written semicorchea octava.
- `left-patterns.png`: the left hand at f4497 to f4602 (3:00 to 3:04): octavas D2 + D3, a single D3 at f4535, then
  La 1 and a run of semicorcheas D1 + D2 with single D2 at f4556, f4577 and f4585, then the blanca Eb1 + Eb2.

**How often, My library** (33 parts, as the page draws them, two counting rules of the script): a **broken pattern**
(a run of 6 or more columns of one hand, corcheas or shorter, each less than a negra after the one before, one shape
(single, octava, chord) at 60 % or more, some columns of another shape): 591 runs (346 right, 245 left), 2,441 odd
columns; a **far quick chord** (a quick column, semicorchea or shorter, two figures shorter than the next column of
its hand and less than a corchea before it, with a note more than an octave from every note of that column): 32
that keep a near note, 62 single quick notes. The largest share of one window's notes a fix would change (one per odd
column or far note): 0.7 % to 27 % by song; 6.7 % in 7 Years. The chord shape is noisy (a melody over chords changes
shape by itself), so the core's `places` (section 4) uses only octava and single-note runs.

# 3. Prompt version 6 (task 3.2)

`instructions.md` changes, version 5 to 6:

- The opening lists "the few notes that the rules of simplicity add or leave out"; the matrix paragraph says the sheet
  is for an amateur pianist.
- **Grace notes**: the rule of implementation 04 (thirty-seconds or shorter; a lone short note written two figures
  shorter than a much longer one; a run of three or more keeps its figures).
- **Every onset exactly once**: except the notes of the section "Simplicity", each declared in a comment line after
  the note lines (`# leave out f1822 G2`, `# add f4556 D1`); an undeclared change is an error.
- **beam.9**: two short notes just before a longer note of the same hand are one group (Phase 2's note: the AI never
  writes grace notes, so a written pair would print two flags).
- New section **Simplicity**: simple.1 uniform patterns (both hands; add the missing note, or leave out the extra
  ones, or make the whole passage simpler), simple.2 the amateur pianist (the G2 + G3 example; a quick single note
  stays), simple.3 the notes keep their place (no frame or name moves; the limits of the check in words), simple.4
  change little (at most a tenth).
- **Example 5**, written for the prompt (no song): the quick G2 + G3 before Bb3 + D4 keeps G3; a run of D2 + D3
  octavas with two single D3 gets the two D2; the lead-in A2 stays.
- "How to answer" names the comment lines and the limits.

`frames.PROMPT_VERSION = "6"`; the record's `prompt` is `6` or `6+hands`. The window prompt's Answer section asks for
the comment lines in a whole-song window (not in a stretch).

# 4. Places to check (new, task 3.2)

The first whole-song test (section 7) completed the octavas but kept the far G2, which the windows test had left
out: with the context of earlier windows the AI decided otherwise. The app now finds the places by rule
(`frames.far_quick`, `frames.broken_octaves`, on the base sheet's notes of the window, with the hands they have now)
and `window_prompt(check=places(...))` lists them under "## Places to check (rules of simplicity)", one line each:

```text
- f1822: G2+G3 is quick, just before Bb3+D4 at f1827 in the same hand; G2 is more than an octave from it (simple.2)
- f4527 to f4598: a run of octaves in one hand, with single notes at f4535 D3, f4547 A1, f4556 D2, f4577 D2, f4585 D2 (simple.1)
```

The AI still decides each one ("apply ... when it makes the sheet simpler"; it kept La 1). A single quick note far
from its main note is not listed (it stays by simple.2). In 7 Years the app lists exactly the three places of the
images (windows 5, 12 and 14 of 15); the other windows get no section.

# 5. The check (task 3.3)

`check_answer(reply, target, simplify=True)` (whole-song windows; `write_frames(simplify=True)` is the default):

- `declared(reply)` reads the comment lines anywhere in the reply (inside the block or just after it; a first test
  wrote them outside the fence). The notes missing from the answer **and** declared are left out; the notes not in
  the target **and** declared are added. Anything else is the old error, with a hint to the comment line.
- `simplicity(target, answer, left, added)`: a note left out keeps a note of the answer in its column within an
  octave (`NEAR = 12`); a note added has its hand playing a note of the target at that frame, is within an octave of
  one of them, and has the name (pitch class) of a note of its hand in that column or the `PATTERN_COLUMNS = 8`
  columns of its hand before and after; changes at most `max(CHANGE_MIN = 4, CHANGE_SHARE = 0.1 · notes)`. A change
  of octave is a note left out and one added of the same name.
- The stretch keeps its own mode (`drop`, `free`); the beam guard and the structure checks are unchanged.

Tests (`tests/test_sheet_llm_frames.py`): the five examples pass with `simplify=True`; each limit and the undeclared
changes (`test_the_checker_accepts_the_declared_changes_of_simplicity_within_their_limits`); the places and the
prompt section; a window that adds and leaves out notes and the sheet that draws them (`write_frames(only={0})`).

# 6. Storing (task 3.4)

- `_answer_part` keeps the answer's notes that have no place in the base sheet in `Part.added`. `placed(base, part,
  quarter_ms)` gives each an onset (the first onset of its column in the base, else its frame) and a length (the
  longest note of its hand in that column, else its figure). `assemble` draws them, so the page's sheet of the moment
  (`LiveRun.text`) shows them; a note of the base that no part decided was left out and is not drawn (as before).
- `FramesSong.changes()`: the notes left out (in the AI's windows) and the notes added.
- `job.commit(..., changes=)`: in the path that writes the hands, `edits.change_notes` marks the notes left out
  removed (by drawn column and key, `_notes_at`) and writes the added ones (`NoteEvent` at the column's onset, hand
  of its staff, the median velocity of its column), then the hands as before, in one `save_edit`
  (`notes_changed=True`). The stored text is `reapply` of the sheet on the new notes (a column whose first note went
  may move a frame). The history snapshot is taken only when something changes (as before, only when hands changed).
- Undo: `edits.record_run(part, gone, plain, text)` starts the log again (as before) and records one step "Notes the AI
  added and left out" when there are changes: `removed` toggles of the notes, and the sheet patch from `plain` (the AI's
  sheet laid on the notes without the changes, `reapply` with `edits.starting`) to the stored text. Undo puts the
  notes back and the sheet to `plain`; the record (the mark, the counts) stays. Redo makes the changes again.
- `Record.added`, `Record.left_out` (`added`, `leftOut` in the record line, written only when not 0).
- Not changed: a run whose notes changed meanwhile, a failed run again (the earlier sheet kept) and an algorithm-only
  run store no note change.
- `apply_stretch` now uses `edits.change_notes` (same behaviour; an added note takes the velocity of its column).
- Test: `test_part_sheet.test_the_notes_a_run_leaves_out_and_adds_go_into_the_notes_with_one_step_of_undo` (a
  stand-in AI that adds A1 under A2 and leaves out E4; notes, record, drawing, undo, redo).

# 7. The tests with the AI (task 3.5)

The user agreed to each before it ran. Sonnet 5.5, hands shown (a run again), reference 480 ms given for the windows.

| Test | What | Result | Cost |
|---|---|---|---|
| 1 | Windows 5 and 12 in memory (`write_frames(only=...)`, the library version's notes) | both accepted at the first reply; G2 left out at f1822; D2 added at f4535 and D1 at f4556, f4577, f4585; the left hand's groups even (4, 4, 5) | $0.14 |
| 2 | The whole song through the app on a temporary copy (`POST /projects/{id}/duplicate`, `POST /sheet/{copy}/llm`) | 15 windows, all by the AI, no retry; 3 D1 added; G2 kept at f1822 and f5222 (section 4) | $0.60 |
| 3 | Windows 5, 12, 14 with the places | all accepted at the first reply; G2 left out at f1822 and f5222, the same 4 notes added | $0.15 |
| 4 | The whole song again on a fresh copy | 15 windows by the AI, no retry; **2 left out, 4 added, exactly the six of the images**, nothing else; 0 hands moved, 0 new problems of `frames.check`; reference 500 ms (480 before): 10 of 1,456 figures differ (6 negras now corcheas, 4 redondas now blancas) | $0.67 |

Total $1.56. Both copies were deleted. The gallery (`python scripts/simplicity_gallery.py --out
../context/implementations/04-app-enhancements/gallery/phase-3 --after <copy>`, built from test 4 before its copy
was deleted) has five cases: the two quick chords, the octava run, and the two Phase 2 image passages, prompt 5 above
prompt 6, the list of changes read from the data. Checked zoomed in (Playwright at scale 2): G3 alone before the
chord at both places, every column of the run an octava, the beam groups 4, 4, 5. The line breaks move: earlier lines
are written differently (more beam groups: 520 note lines with a beam against 462).

# 8. The real run (task 3.6)

On the user's answers (the edit copy; "finish Phase 3 first"): `POST /sheet/477086a0.../llm` on the edit copy in the
Personal Vault, 342 s, $0.63, 16 requests, every window by the AI, reference 480 ms. Against the copy's sheet before
(kept in the session's scratch folder), both drawn by today's rules (`build.reapply` of the old text): Sol 2 left out
at f1822 and f5222, D2 added at f4535 and D1 at f4556, f4577, f4585, nothing else (0 hands moved, 0 figures
different, 0 new problems); the user's 4 figures set by hand, the 2 lyrics blocks, the titles and the line space
kept. Record: `prompt 6+hands`, `runs 2`, `added 4`, `leftOut 2`, `edited true`. The steps of undo start again with
"Notes the AI added and left out" (the 50 earlier steps of the copy are gone, as after every whole run). The My
library version is unchanged until the user saves the copy to the library.

# 9. Checks

| Check | Result |
|---|---|
| `pytest` (CPU, GPU hidden) | all pass but the two known Transkun tests (they load their weights only on the GPU) |
| Sheet tests after `black` | 90 passed |
| `black` | the changed files formatted |
| `scripts/docs/check-links.py` | 0 broken links |
| Browser checks | not run: no frontend change; the undo label is new text in the existing button |

# 10. Notes for later

- After the gallery the user asked for the Enhance with AI dialog and Simplify left / right / both (plan sections 3.5
  and 4.4): Phase 4. `write_frames(only=)`, `places`, `declared`, `simplicity` and `edits.change_notes` are the parts
  it builds on.
- Documentation updated: the core's `README.md` (sections 2, 11, 12), `context/backend/README.md`. Phase 5 still has
  `04-context.md` and the frontend pages (the undo label "Notes the AI added and left out").
- The other songs keep prompt 5 sheets until the user runs **Enhance it again with AI** on them.
