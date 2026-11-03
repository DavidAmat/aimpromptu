# 04-7 Phase 2: The clef rule

Plan [`04-7-plan.md`](04-7-plan.md) sections 4.1 and 5 (and its section 8, the Phase 2 changes); checklist
[`04-7-checklist.md`](04-7-checklist.md). Branch `feat/04-7-open-points`. 2026-11-03.

# 1. The checks before the first edit of `src/`

- `ps aux`: the frontend's vite, the backend's container, other projects (a Playwright driver of another project's
  container); no pytest or browser check of this project.
- `docker logs aimpromptu-backend-1`: only `GET /health` since the reload of 04-6.
- The logs `ai-runs/*.json`: 2 left after Phase 1, both `done`. None `running`.

# 2. What changed

## 2.1 The rule (`sheet/proposal/frames.py`)

- `STATES`: the left hand has a fourth state, `("F4", 1, OTTAVA_COST)`, the bass clef under 8va; the right hand a
  fourth, `("G2", -1, OTTAVA_COST)`, the treble clef under 8vb.
- `_fits` (the limit of a column in the hand's own clef): the left hand never reads a note written `BASS_LIMIT` (4)
  ledger lines or more above the bass staff (as before, now also under 8va); the right hand never one that far below
  the treble staff without a line (new: D3 or lower); under the own clef's line (left 8va, right 8vb) no note that
  far on the other side either (a wide chord).
- `short_clefs(sheet)` (new, `CLEF_MIN = 5`, `READABLE = 1`): for each hand, each stretch of its other clef with
  fewer than 5 of its columns (grace columns do not count) goes back to its own clef. The clef changes between the
  column before the stretch and the column after it go; each column takes the line (left 8va, right 8vb) only when a
  note would otherwise stand 4 ledger lines or more outside the staff; the columns between two marked columns join
  the line when their notes are written at most one ledger line out on its far side. A stretch stays as it is when
  a column reads neither way (counted `short stretches kept`) or when it holds a column inside a mark of a clef set
  by hand. Ornament onsets take the line of the note before them. Returns `short clef stretches`, `short stretches
  kept`, `notes under a new line`.
- `clefs_and_ottavas` runs `short_clefs` at its end; its counts are now taken after it (`clef changes`, `8va notes`,
  new `8vb notes`). So the sheets never enhanced, the level batches (`levels.drawn`), **Clefs and 8va by the rule**
  (`reading.clef_rule`) and `fit_clefs` all follow it.

## 2.2 Every stored sheet (`part_sheet/build.py`, `edits.py`)

- `reapply`: after `fit_clefs`, `short_clefs(sheet)`, with the stored marks copied first. Every stored sheet (a
  whole run of the AI, a level run, the user's edits) is drawn through it; the stored files are not written by the
  step (an edit stores `reapply`'s result, as for the decoration-note rule of 04 Phase 2).
- Transpose: `short_clefs` also after `fit_clefs(far_notes)`.

## 2.3 The clefs the user set by hand (plan 4.1 point 3)

- `Sheet.user_clefs: list[(start, end, staff, clef)]` (`sheet/sheet/data.py`), with `cut_clef_marks(marks, start,
  end, staffs)` (a mark keeps its outer pieces).
- F1 (`sheet/sheet/f1.py`): one line per mark after the lyrics, `clefset L f1998 f2033 treble`; read back by
  `_read_clefset`. No F1 parser in the frontend.
- Who writes and cuts the marks: `reading.set_clef` (the hand's other clef: a mark; the own clef: the marks there cut),
  `reading.clef_rule` (cut over its stretch), `llm/frames.splice` (a stretch run: cut where the answer wrote the clefs;
  the fixed hand keeps them), `levels.splice` (kept: a level batch keeps the sheet's clefs), `build.reapply`
  (carried). A whole run drops them (`job.py` builds a new sheet and `carry_extras` does not copy them): the AI writes
  every clef again, the rule of 03 Phase 7. `levels._bare` drops them, so the line never reaches a prompt.
- The clefs set before the mark (three parts, plan 3.3): **no one-time step was needed** (plan section 8). Read from
  the undo logs: My Way (`c33860b5`) steps 6 and 7 set the right hand's own clef (treble); `946c21f2` step 4 sets the
  left hand's own clef (bass); `7b9a41e4` step 11 sets the treble clef for the left hand at f1998, a stretch of 6
  columns (f1998 to f2023, bass again at f2033), which the rule keeps.

## 2.4 "Never 8va in the bass clef" ended

| Where | Now |
|---|---|
| `sheet/sheet/frames.check` | no "8va in the bass clef"; "15ma in the bass clef" stays a problem |
| `sheet/llm/frames._structure` (the AI's check) | an 8va in the bass clef is accepted; a 15ma is refused; a note written 4 ledger lines or more above the bass staff is refused also under 8va ("write it under 8va in a short stretch, or in the treble clef for a passage") |
| `join_ottavas` (`sheet/llm/frames.py`) | joins 8va lines in the bass clef too (`OTTAVA_LOWEST` by clef: C5 treble, E3 bass) |
| `reading.set_ottava` | 8va over a bass clef stretch allowed; 15ma refused ("A bass clef takes no 15ma: use 8va, ...") |
| `reading.set_clef` | a bass clef keeps the 8va; a 15ma becomes an 8va |
| `FramesRangeToolbox.tsx` | the 8va chip works in the bass clef; the 15ma chip is off there, with the reason |
| the engraver | no change: the same octave-line code draws both staves (checked zoomed, section 4) |

## 2.5 The prompts

- `prompt/frames/instructions.md`, **version 8** (`VERSION`, `frames.PROMPT_VERSION = "8"`): clef.L1 to clef.L6 and
  clef.2 say the user's rule (5 onsets or more for the other clef; a short high stretch of the left hand in the bass
  clef, with 8va when needed; a short low stretch of the right hand in the treble clef, with 8vb); the tag `8vb` in
  the format; Example 2 without its two-chord treble stretches; the checker's paragraph without "8va is never in the
  bass clef". No real run (credits): `short_clefs` writes the rule on every drawn sheet whatever the AI writes.
- The stretch prompt (`frames.py`, the hard rules): "no 15ma in the bass clef" and the shortest stretch.
- The older `prompt/instructions.md` is read only by the bars chain (`write_song`), which no app run uses
  (`git grep`): not changed.

# 3. Tests

- New: `tests/test_sheet_clefs.py`, 12 cases: a lone high note (bass clef, 8va), a note readable with ledger lines
  (no line), four high columns (bass, 8va) and five (treble), one line joined over three columns, a chord too wide for
  the line (kept), the right hand (8vb for a lone C3, the bass clef for a low passage), a stored AI sheet laid again
  (only the short stretch goes; nothing but clefs and lines changes; laid again it stays the same), a clef set by hand
  (its mark in F1, kept by `reapply`, cut by **Clefs and 8va by the rule**), a bass clef set inside a treble mark,
  `cut_clef_marks`, 8va allowed and 15ma refused in the bass clef, a bass clef set by hand keeps the 8va.
- Changed: `test_sheet_llm_frames.py` (the checker: 8va in the bass clef accepted, 15ma refused);
  `test_sheet_edits.py`, the high run moved to the left hand: its first seven columns are a passage (treble clef),
  the eighth, a lone B4 after a pause, stays in the bass clef under 8va (renamed
  `test_a_high_passage_moved_to_the_left_hand_gets_the_treble_clef_a_lone_high_note_8va`).
- The whole backend suite on the CPU: **1362 passed, 1 skipped, 0 failed** (two more tests of the old rule were changed
  after the first run: the prompt test, version 8 and the new clef.L1; `test_sheet_reading.py`, 8va over the left hand
  in the bass clef now accepted and 15ma refused).
- `npx tsc -b`: 0 errors.
- `npm run check:frames-tools` (with a new step: the 8va chip over a bass clef stretch of the left hand, on the
  temporary copy of 7 Years): **all passed**; its picture `08b-8va-bass` looked at zoomed: the line above the bass
  staff, clear of the right hand, the notes an octave lower. `npm run check:frames-page`: **all passed**. After them,
  7 Years of My library unchanged (`sheet.f1` of 2026-10-25) and no copy left.

# 4. The drawn cases, checked zoomed in

Six cases drawn by the app's engraver (`engine.render_frames`, width 60), screenshot by Playwright, each looked at
zoomed in against its F1 data:

1. A lone D5 in the left hand: bass clef, written D4 (one ledger line) under an "8" with its hook. Data `f60 L: D5:4
   8va`.
2. D5, C4, E5: one dashed 8va line over the three; C4 written C3 inside the staff; E5 written E4 on two ledger lines.
3. Four high columns (D5, Eb5): one line over the four, in the bass clef.
4. Five high columns: `clef=treble` at the first, `clef=bass` at the column after the last.
5. The right hand's lone C3: treble clef, written C4 (one ledger line below) with "8" and its hook below the staff.
6. C2 with D5 in one left-hand column: stays in the treble clef with eight ledger lines for C2 (as the old rule drew
   it). Plan risk 7.2: the gallery of Phase 3 shows the real cases to the user.

A smoke run of `build._compute` (read-only) on three real parts: Superestrella (`f4c4de9a`, an AI sheet) 0.08 s, its
left hand from 154 clef changes to 10, with 320 notes under 8va in the bass clef; Halleluyah (`43faf78e`) 0.04 s, 16 to
4; My Way (`c33860b5`) 0.03 s, no left-hand change. `frames.check` finds no problem on the three. These are not the
measure of Phase 3, only a check that real sheets draw.

# 5. Findings for later

- `sheet/llm/frames.assemble` names its argument `clefs` ("llm" or "rule") and then reuses the name for the dict of
  first clefs, so `clefs == "rule"` is never true. No caller passes `clefs="rule"`, so nothing breaks; left as it is.
- `levels._bare` builds the prompt's sheet with `replace(sheet, ...)`, so a sheet's titles and lyrics lines would go
  into a level prompt (the F1 writer prints them). Only the clef marks were taken out here (04-7's own data); the
  titles and lyrics are a question for a later task.

# 6. For the next phase

- Phase 3 measures every part of the `private` layer old against new (`scripts/clef_study.py --study`), shows the
  gallery to the user and checks the three parts with clefs set by hand by name. The old rule for the study: the old
  `STATES` (three each), `short_clefs` off, the old `_fits` (only the left hand's limit), and the old checks.
- Superestrella is the sheet that changes most (section 4): its passages should be in the gallery.
