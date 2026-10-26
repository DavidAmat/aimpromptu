# 03: Phase 9 report: the saved data

Plan: [`03-plan.md`](03-plan.md) section 7, Phase 9. Checklist: [`03-checklist.md`](03-checklist.md). Branch
`feat/migrate-new-logic` (fast-forwarded to `master`'s merge commit of Phase 8 at the start). Written 2026-10-26 on the
Ubuntu machine. **Built and migrated 2026-10-26**; the user's check in the browser is next.

# 1. Summary

| Task | Result |
|---|---|
| 9.1 Study | Section 2: 53 parts on disk outside the histories, 47 `sheet.json`, 14 `sheet.f1`. 36 of the 47 `sheet.json` were written by a script from the old page's automatic first write; the user's own marks are few. One question to the user (section 3), answered: the new clef rules everywhere |
| 9.2 The mapping | `part_sheet/legacy.py` and `build.with_legacy` (section 4): titles, lyrics, space between lines, figures set by hand and fingers on every sheet; beam breaks and joins only on a sheet the AI did not write. Old clefs and octave lines dropped. A part with no stored sheet is drawn with its old marks |
| 9.3 The migration | `scripts/migrate_sheets.py`; backup `/mnt/ssd2/aimpromptu/.database-20261026-193801.tar.zst` (1.4 GB); dry run, then `--write`: 5 parts stored, 40 with nothing to carry, 6 with no `sheet.json`; a second run changes nothing (section 5) |

# 2. The study (task 9.1)

## 2.1 What the database holds (read only, 2026-10-26)

| | Parts | With `sheet.json` | With `sheet.f1` |
|---|---|---|---|
| My library (user 1: 32, user 2: 1) | 33 | 33 | 10 (the AI's, Phase 5) |
| Projects (user 1) | 17 | 11 | 4 (2 the AI's and edited, 2 the algorithm's and edited) |
| Public, requests | 3 | 3 | 0 |
| Histories (snapshots) | | 22 | 2 |

The app lists 51 of the 53 parts on disk (`bundle.list_parts`): the two parts of a passage's takes (Elefants) and one
request copy are not listed; none has a mark to carry.

## 2.2 Who wrote the old sheets

The `savedAt` of the 47 `sheet.json` splits them in two groups:

- **36 were written by a script** on 2026-10-16 between 13:59:43 and 14:02:01, about 3.5 s apart:
  `aitu-frontend/scripts/sheet-library.mjs` (implementation 02, Phase 12) opened every version of My library, pressed
  **Predict hands**, let the old Sheet step draw "from the defaults" and saved it. On a first write the old page took
  three automatic answers as its baseline (`SheetPage.tsx` `takeKeyHint`, `takeOttavaHint`, `takeClefHint`): the key
  with the fewest accidentals, the octave brackets the renderer suggested, and the left hand's clef rule. So every
  clef change and octave bracket of these 36 sheets is the old rules, not a choice of the user. Their 7 Years copies
  (user 2's library, the public version, two requests) carry the same marks.
- **11 come from the user's own work**: the AITANA tutorial (its project, its library version, and an untitled
  project of 21 notes, 2026-09-17), Elefants and its copies (2026-10-01 and 10-15), Cara de cul (2026-10-07),
  Halleluyah (project and library version, 2026-10-16 11:18).

## 2.3 The fields in use

| Field | Sheets (outside the histories) | Where | New sheet |
|---|---|---|---|
| `keySignature`, `keyChanges` | 47, 2 (4 changes) | everywhere; Elefants, Cara de cul | already kept (Phase 5, `build.reading_of`) |
| `anchorFigure` other than negra | 7 | AITANA, Elefants | already kept as the reference figure (Phase 5) |
| `ottavas` | 44 (359 brackets) | everywhere | **dropped** (section 3) |
| `clefChanges` | 12 (92 changes) | 8 songs | **dropped** (section 3) |
| `lyrics` | 4 (6 pieces) | Halleluyah, AITANA (project and library each) | carried |
| `lineSpacing` other than 72 | 3 (60 px) | AITANA ×2, the untitled project | carried (4 staff spaces) |
| `overrides` | 2 (7 each) | AITANA | carried as figures set by hand (`fix`) |
| `beamBreaks`, `beamJoins` | 2 (3 and 12 each) | AITANA | carried on the algorithm's sheet only |
| `hiddenNotes` | 2 (7 each) | AITANA | nothing to do: all 14 notes are already removed in `notes.pmn` (the old Save wrote them through) |
| `cueRanges`, `evenSpacings`, `spacings`, `noteSpacing`, `dropDecorative` | 2, 2, 1, 1, 3 | AITANA, Cara de cul | dropped (the user's answers of Phases 7 and 8) |
| `fingers`, `trills`, `graceNotes`, `title`/`subtitle`/`artist`, `staffGaps`, `speedChanges` | 0 | nowhere, histories included | fingers and titles carried by the code anyway; the others have no place |

## 2.4 The old automatic marks against the new clef rules

Measured by laying each old bracket and clef change on the sheet the page draws today (the algorithm's for the parts
without an AI sheet), read only:

| | Parts without an AI sheet | The AI's parts |
|---|---|---|
| Octave brackets | 267 | 92 |
| Notes under an old bracket | 6,873 | 2,521 |
| ... with the same line from the new rules | 1,428 (21 %) | 470 |
| ... where the new sheet reads a bass clef under an old 8va or 15ma (forbidden on the new sheet) | 268 | 249 |
| Clef changes | 67 | 25 |
| Notes read in another clef than the old sheet's | 1,130 | 449 |

The old brackets were mostly 8vb and 15mb under the left hand (Phase 7: 139 and 65 of 359), which the new rules never
write: the new rules give the left hand the treble clef, then the treble clef with 8va, for its high passages.

## 2.5 What the new sheet did with the old data before this phase

A part with no `sheet.f1` was drawn by the algorithm with two decisions of its `sheet.json` (the armadura, a renamed
reference figure); every other mark was ignored, so the lyrics of Halleluyah and AITANA, the figures and beams of
AITANA, and the closer lines were not on the new sheet. The 10 songs the AI wrote (Phase 5) showed the AI's sheet
only, also without their lyrics.

# 3. The user's answer (2026-10-26)

The question: what the new sheet does with the old clefs and octave lines, given section 2.2 (36 of 47 sheets from the
script) and section 2.4 (21 % agreement). Options: keep only the 11 sheets of the user's own work (recommended), the
new rules everywhere, or keep all of them. **The answer: the new rules everywhere.** Every old clef change and octave
line is dropped, the user's own ones too (AITANA's 17 lines, Cara de cul's 6 8vb lines, Elefants', Halleluyah's 12
clef changes); the range toolbox sets them again where wanted.

The agent's choices, from the code and the earlier answers:

- **The user's marks go on every sheet, the AI's sheets too**: titles, lyrics, the space between lines (what the user
  wrote about the whole sheet, Phase 8), figures set by hand and fingers (the marks a new AI run keeps, Phase 7).
- **Beam marks only on a sheet the AI did not write**: beams are the AI's kind; a new AI run writes them again (Phase
  7), and the AI's 10 songs show the AI's sheet (Phase 5).
- **Lazy and stored**: the page draws a part with no stored sheet with its old marks (a history version or an old
  `.aitu` can bring a `sheet.json` back), and the migration stores them so they no longer depend on `sheet.json`.

# 4. The mapping (task 9.2)

## 4.1 `part_sheet/legacy.py`

- `has_marks(rhythm)`: whether an old sheet holds anything to carry; `dropped(rhythm)`: the kinds not carried, counted.
- `Cells.of(notes)`: an old mark names a note by its onset cell (the 40 ms column of its onset, `dense.columns_of`);
  the new sheet draws it at the column of its chord (`drawn_columns`, D-04), at most one frame before. Three maps: by
  cell and key (a finger), by staff and cell (a figure override names a chord of one hand; its `row` is always 0 in the
  data), by cell (a lyrics piece's first frame).
- `carry(sheet, rhythm, notes, *, ai, beams=True)` changes the sheet and counts what it did:
  - titles, lyrics and the space between lines only when the sheet has none of that kind (a stored sheet keeps what
    the user wrote on the new sheet);
  - lyrics: frames kept, size and lift converted as `useFramesLyrics.ts` does (12 px = 1.4 staff spaces; `offsetY`
    up is a positive lift), an old `width` becomes the width the words wrap to (Phase 8A++); `offsetX` is not carried
    (the old page dropped it at a piece's first move); a piece over the frames of the one before it is left out;
  - the space between lines keeps its ratio to the old default (72 px is the new 5 staff spaces; 60 px is 4);
  - figures: the old name (a dotted figure keeps its plain figure, no puntillos) set by hand on the chord (`fix`);
  - fingers on their note (the other staff when the note moved hand);
  - beams (not with `ai`): a break cuts where the chord is inside a group; a join puts the chord with the group of the
    chord before it, through `reading.break_beam` (one figure, at most 8 notes). `held` when the new groups already
    do it, `lost` when they cannot.

## 4.2 `build.with_legacy` and the drawing

`with_legacy(sheet, notes, rhythm, *, ai)` copies the sheet, carries the marks, settles it with `reapply` (the rules
run again, as for an edit) and checks that `frames.check` finds no new problem; if it does, it tries again without the
beam marks, then gives the sheet back unchanged. `build._compute` uses it for a part with no stored sheet and for a
plain algorithm record (`_algorithm_sheet`); nothing is stored by drawing. A stored sheet is drawn as stored.

## 4.3 `store.Record.legacy`

What the migration carried, by kind (`{"lyrics": 2, "figures": 6, "space between lines": 1}`); written only when set,
so every older record is unchanged. A part whose record has it is skipped by the migration.

# 5. The migration (task 9.3)

`aitu-backend/scripts/migrate_sheets.py`, with `.env` loaded: a dry run by default, `--write` to store. For each part
the app lists, with a `sheet.json` that has marks to carry, under the part's lock:

- no stored sheet, or a plain algorithm record: the algorithm's sheet (its record's figure and armadura when it has
  one) with the marks, stored with `edited` (so it is laid again on new notes, never computed again), the current
  `handsRevision`, and `reference: user` when the old sheet renamed the reference figure (a new AI run then keeps it,
  as after Transpose figures);
- a stored sheet with decisions (the AI's, or one the user edited): the same record, the kinds it lacks, laid on the
  current notes.

Run on 2026-10-26 after `make db-backup` (`/mnt/ssd2/aimpromptu/.database-20261026-193801.tar.zst`):

| Part | Sheet | Carried | Left out |
|---|---|---|---|
| AITANA tutorial, library version | the AI's | 2 lyrics pieces, 6 figures, space between lines 4 | 1 figure (its left-hand chord is now in the right hand); 15 beam marks (the AI's kind) |
| AITANA tutorial, project | algorithm | 2 lyrics pieces, 6 figures, space between lines 4, 2 beam breaks, 1 beam join | 1 figure; 3 beam joins (the chord before has no beam on the new sheet); 1 break and 8 joins already held |
| Halleluyah, library version | the AI's | 1 lyrics piece | |
| Halleluyah, project | algorithm | 1 lyrics piece | |
| The untitled project (21 notes) | algorithm | space between lines 4 | |

Dropped over the 51 parts: 359 octave lines, 92 clef changes, 2 even spacings, 1 spacing, 1 note spacing, 2 print
smaller ranges, 3 "hide decorative notes". 40 parts had nothing to carry (the 30 script sheets of the library, their 7
Years copies, Cara de cul and the Elefants projects, whose armadura and figure were already kept), 6 have no
`sheet.json`. The second run (dry) says "migrated already" for the 5 and changes nothing. The histories are not
touched: a restored version is drawn with its old marks by section 4.2.

# 6. Checks

| Check | Result |
|---|---|
| `tests/test_sheet_legacy.py` (new, 4 tests) | an old sheet drawn with its titles, lyrics (the overlapping one left out, lift and width converted), space between lines, figure, finger and beam break, without its clef and 8vb, nothing stored; the migration stores once (dry run first, `reference: user`, `legacy`, the same drawing, the second run skipped, the marks kept without `sheet.json`); an AI sheet gets the lyrics and the figure, not the beam break or the clef, and keeps its source; beam joins held or carried |
| `test_part_sheet`, `test_sheet_edits`, `test_sheet_reading`, `test_sheet_toolbox`, `test_sheet_lengths`, `test_paste`, `test_passages` (host) | pass unchanged |
| Backend, full run in the image on the CPU | 1,397 tests: 1,393 passed, 1 skipped (needs a GPU), the same 3 failures as in Phases 7 and 8 (section 6.1) |
| `black`, `flake8` on the changed files | clean |
| The drawings | AITANA (project, then the stored library version drawn by the engine) and Halleluyah (project), zoomed in around each lyrics piece: the words above the upper staff, the long AITANA piece wrapped onto two lines as on the old sheet, clear of the AI's 8va line; the octave lines of the AITANA project are the algorithm's own (636 notes, the same with and without the old marks) |
| `scripts/docs/check-links.py` | passed (416 files) |

## 6.1 The full backend run

In the image, on the CPU (another project holds the GPU): 1,397 tests, 1,393 passed, 1 skipped. The 3 failures are the
ones of Phases 7 and 8: `test_the_worked_example_at_00_46_prints_three_equal_corcheas` (failing since Phase 0) and the
two `test_transcription_transkun.py` tests, which load a checkpoint saved on CUDA. No browser check was changed or
needed: the frontend did not change, and the checks work on copies of 7 Years, which has nothing to carry.

# 7. Notes for Phase 10

- `editing/marks.py` still moves the old marks of `sheet.json` in every paste. After the migration no listed part needs
  them, but a part with no stored sheet is drawn with them (section 4.2), so a paste must keep moving them while
  `legacy.py` reads `sheet.json`. Removing both together is the simple end: then a history version or an old `.aitu`
  from before 2026-10-26 opens with the armadura and figure only.
- `schemas/rhythm.py` (`SavedRhythm`) and `pipeline.load_rhythm` stay while `build.reading_of` and `legacy.py` read
  `sheet.json`. The `PUT /time/{uuid}/rhythm` route has no caller since Phase 8B.
- The AITANA project's high right-hand run (frames 19 to 910) had the user's own 8va line; it is drawn with the new
  rules now (the user's answer).

# 8. Documentation

- `aitu-backend/src/aitu_backend/sheet/README.md` section 17; `part_sheet/__init__.py`, `build.py`, `store.py`.
- `context/backend/README.md`, `context/07-database.md`, `documentation/services/backend/rhythm-and-annotations.md` (a
  note at the top: the file is the old sheet's, what the new sheet reads of it).
- [`03-plan.md`](03-plan.md) Phase 9, sections 8 and 11; [`03-checklist.md`](03-checklist.md).
