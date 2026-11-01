> Context: [context/backend/time-model.md](../../../context/backend/time-model.md) ·
> [aitu-backend/src/aitu_backend/sheet/README.md](../../../aitu-backend/src/aitu_backend/sheet/README.md) (sections 9, 12, 16, 17)

# The new sheet: the files of a part, the F1 text, and how the sheet is made

This page is the detail of the new sheet's data: the files a part holds, the text they hold, and the steps that turn
the notes into a sheet. The drawing is told in `sheet-drawing.md`, written by Phase 3 of implementation 05.

The notes are the music. The sheet is a reading of the notes: where each note sits, how long it is written, which
hand plays it, and which key and clefs it uses. The rule of the time model applies: a column never moves
([`time-model.md`](../../../context/backend/time-model.md), rule 2).

## 1. The files of a part

All paths come from `aitu_backend/storage/paths.py`. The part's folder is `part_dir(part_id)`, inside the project
bundle.

| File | Path function | What it holds |
|---|---|---|
| `notes.pmn` | `part_notes_path` | The piano matrix notation of the part: the notes, their hands, `handsRevision`. The only stored music. |
| `sheet.f1` | `part_frames_path` | The new sheet: one `# aitu-sheet {...}` record line, then the F1 frames text (section 2). |
| `sheet.pending` | `part_frames_pending_path` | A marker: a new transcription asks the AI to write the sheet. The Sheet step starts the run and removes it. |
| `sheet.edits.json` | `part_frames_edits_path` | The steps of undo and redo of the sheet (`edits.py`). Not copied with the part: a copy starts without steps. |
| `sheet.json` | `part_sheet_path` | The old sheet's file (vexflow-v2). Nothing writes it now. It is still read for its marks (section 8). |

The hands live in `notes.pmn` and only there. `sheet.f1` keeps a copy of the reading of the hands
(`handsRevision` in its record). When the notes change, the stored sheet is laid again on the new notes
(section 7).

## 2. The F1 frames text

The text is the F1 frames view of `sheet/sheet/f1.py`: `write(sheet, mode="frames")` makes it, `read(text)` reads it.
`read` raises `F1Error` (a `ValueError`) with the line number when a line is wrong. Its module docstring is the
full format.

```text
# aitu-sheet {"source":"algorithm","handsRevision":4,"windows":[],...}
F1 frames frameMs=40 quarterMs=500
key=3# clefs: R=treble L=bass
f8       L: E3:4  R: C#5:8 b1
[]x3
f12      R: A4:16 b2 grace/
f13      L: C2:2 8va
```

- **Header** (`F1 frames`): `frameMs=40` (the column, `FRAME_MS`); `quarterMs=` (one negra in ms, the reference figure,
  `Sheet.quarter_ms`); `spaceMs=` (the reference figure of the spacing, when Transpose figures renamed the figures);
  `lineSpace=` (the space between lines, in staff spaces). The last two are read only by the frames view.
- **Second line**: `key=` (the armadura, `key_text`) and `clefs: R=... L=...`. The clef names are `treble`, `bass`,
  `alto`, `tenor` (`CLEF_NAMES`).
- **One line per drawn column**: `f<column>`, then each hand as `R:` or `L:`, then its notes. Notes of one hand that
  share their figure and tags are one chord: `A2,C#3,E3:8`.
- **Empty columns**: a run of empty columns is `[]x<count>`.
- **Key and clef changes** come on their own line at their column: `f<column> key=...`, `f<column> clef=...`.
- **Note**: `<pitch>:<figure>`, for example `C#4:16`. A figure is `1` to `64` (1 redonda, 2 blanca, 4 negra, 8 corchea,
  16 semicorchea, 32 fusa, 64 semifusa). No dots and no tuplets in the new sheet.
- **Tags** after a note (`_apply_tag`): `b<n>` beam group; `grace` or `grace/` (a grace note, slashed or not);
  `arp`, `tr`, `trem`, `ferm`, `mord`, `turn` (ornaments); `8va` and `8vb` (written an octave up or down); `fg<n>`
  (finger); `fix` (the figure was set by the user); `asgrace` and `nograce` (the grace note switch the user set);
  `sp` (the spelling was set by the user); `orn` (played inside the ornament of the note before it: kept for the
  matrix, not drawn).
- **Title and lyrics lines** (frames view only, after the clefs line): `title "..."`, `artist "..."`, and
  `lyric f356 f373 "Me ve" size=1.6 lift=0.5`. A block moved by hand has `at=f412 dx=... dy=... width=...` and its font
  look. The words are a JSON string.

The AI prompts never see the user's marks (`fg`, `fix`, `asgrace`, `nograce`, `sp`, the lyrics and the titles).

## 3. The record line

`part_sheet/store.py` writes the record above the text (`MARK = "# aitu-sheet "`). `store.save` writes it, `store.load`
reads it into a `Stored` (the record and the text). `Record` holds:

| Field | Meaning |
|---|---|
| `source` | `llm` (every window by the AI), `mixed` (some windows kept the algorithm), `algorithm` (none). |
| `handsRevision` | The `notes.pmn` revision the sheet was written for. Another value means the notes changed since. |
| `windows` | The segments of the piece-by-piece view: `[first frame, end frame, "llm" or "algorithm"]`. |
| `quarterMs`, `reference` | The reference figure, and who chose it (for example `song` or `user`). |
| `model`, `prompt`, `usd`, `requests`, `written`, `note` | The AI run: the model, the prompt version, the cost, the requests, the time, and why it stopped early. |
| `runs` | How many AI runs wrote this sheet. |
| `edited` | The user changed the reading (a figure, a finger, a beam, a clef). |
| `decided` | The sheet holds decisions (the AI's or the user's) that laying again must keep. |
| `stretches`, `simplified` | The stretches written again with the user's words, and the Simplify runs (each with its cost). |
| `key` | The armadura the algorithm uses, when the song or the user chose it. |
| `added`, `leftOut` | The notes a whole AI run added to the notes or left out of them. |
| `legacy` | What the migration carried from an old `sheet.json` (section 8), by kind. |

A sheet whose `source` is `llm` or `mixed` counts as **enhanced with AI** (`store.enhanced`). That mark stays through
every later change of the notes or the hands. Only a new transcription (new notes) clears it.

## 4. The data: `Note` and `Sheet`

`sheet/sheet/data.py` holds the two classes the code works in.

- **`Note`**: `time` (`None` in a frames sheet), `staff` (1 right hand, 2 left hand), `step`, `alter`, `octave` (the
  sounding octave), `figure`, `dots`, `tuplet`, `beam`, `grace` (`acc` or `unacc`), `gslot`, `ornaments`, `ottava`,
  `frame` (the 40 ms column), and the marks `fixed`, `grace_rule`, `spelled`, `finger`. `on_ms` and `len_ms` are measured
  from the notes and are not written in the text. `covered` is the `orn` tag. `midi` is the sounding pitch.
- **`Sheet`**: `notes`, `clefs` (the first clef of each staff), `clef_changes` (`(frame, staff, clef)`), `key` and
  `key_changes` (`(frame, key)`), `quarter_ms`, `titles`, `lyrics` (`Lyric` pieces), `space_ms`, `line_space`. `bars` is
  empty in a frames sheet. `Sheet.sort()` puts the notes in order.

## 5. From the notes to the sheet: the algorithm

`sheet/proposal/frames.py`, `propose_frames(notes, *, key=None, key_changes=None, quarter_ms=None)`, makes the sheet
with no AI. It returns a `FramesProposal` (`.sheet`, `.quarter_ms`, `.info`). Its steps:

1. **Drawn column.** `sheet/sheet/frames.py`, `from_notes`: notes of one key, hand and column are one note (the longer
   kept). Notes struck together (40 ms from the first onset of the group, no chaining, both hands) are one chord, drawn
   at the column of its first onset (`drawn_columns`, `GROUP_MS = 40`, decision D-04). A note without a hand takes
   one by middle C.
2. **Reference figure.** `quarter_ms`, the length of one negra. Without it, `sheet/proposal/beat.py`, `estimate`
   gives the pulse. The AI or the user can give it (section 6).
3. **Figures.** `assign_figures`: a note's own length from `len_ms`, but not past the next onset of its hand. Each
   figure is the nearest plain figure (`figures.figure_of_ms`). A chord takes the figure most of its notes have. A run
   of three or more even gaps (`RUN_MIN = 3`, `RUN_TOLERANCE = 0.12`) takes one figure. A figure the user set (`fixed`)
   stays.
4. **Grace notes and lone short notes.** `find_graces`: one or two fusas or shorter, two figures shorter than the next
   note and just before it, become grace notes (`MAX_GRACES = 2`, `GRACE_FIGURE = 32`). `lengthen_lone`: one or two
   notes more than two figures shorter than the note after them are written two figures shorter than it. A
   `asgrace` or `nograce` mark of the user wins.
5. **Beam groups.** `beam_groups`: consecutive corcheas or shorter of one hand, one figure, not farther apart than a
   corchea. A group is cut at a jump of more than an octave (`JUMP = 12`), at a turn after three steps (`TURN_RUN = 3`),
   and into parts of at most 8 notes (`MAX_BEAM = 8`, in `sheet/sheet/frames.py`).
6. **Armadura.** `choose_keys`: the armadura that prints the fewest signs for each passage. A change costs
   `KEY_SWITCH = 12.0` signs, and a change needs `KEY_STAY = 48` columns after the one before. It is skipped when a key
   is given.
7. **Spelling.** `respell` (rules in section 6).
8. **Clefs and 8va.** `clefs_and_ottavas`: the clef with the fewest ledger lines, with a cost for each change
   (`CLEF_SWITCH = 3.0`, more inside a beam, `CLEF_IN_BEAM`). The left hand never stays in the bass clef four ledger
   lines or more above the staff (`BASS_LIMIT = 4`).

Two uses of the same steps: the algorithm alone (the sheet of a part the AI did not write), and the fallback of the AI
run (a window the AI could not get right keeps the algorithm's notes).

## 6. Figures and spelling

**Figures** (`sheet/sheet/figures.py`). `FIGURES` are `1, 2, 4, 8, 16, 32, 64`; `NAMES` gives their names. From the
negra up, the boundary between two figures is the middle point of their lengths. For the corchea and shorter, the
boundary is `SPLIT = 0.7` of the way from the shorter figure to the longer one. `nominal_ms(figure, quarter_ms)` is
`quarter_ms * 4 / figure`; `figure_of_ms` gives the figure of a length.

**Spelling** (`sheet/sheet/spelling.py`). One name for each note, given its key and the armadura in force. The rules
(the user's, plan section 3.4):

1. A note outside the armadura prints its sign every time it appears.
2. A becuadro only cancels a note of the armadura.
3. No double sharps or double flats.
4. A white key is written natural, except where its natural name is in the armadura and would need a becuadro. Then
   its other name with one sign is used, when there is one.
5. A black key outside the armadura takes a sostenido in an armadura with sostenidos, a bemol in one with bemoles.

`spell(midi, key)` gives the name; `sign(step, alter, key)` the printed sign or `None`; `printed_signs(sheet)` what the
engine prints (rule 7 of plan section 3.4: after a becuadro, the first return of the note prints its sign again when it
is in the same beam group or the next note). `check_rules()` proves the rules on all 15 armaduras.

## 7. Laying the sheet again: the part-level build

`part_sheet/build.py` is the one place that decides which sheet a part shows. Its module docstring has the three cases.

- **`current(part_id)`** returns a `Drawn` (`text`, `source`, `windows`, `stale`, `quarter_ms`, `record`). It is cached
  by the modification times of `notes.pmn`, `sheet.f1` and the old `sheet.json` (`_cache`, 24 parts).
- **`_compute(part_id)`** chooses:
  1. a stored sheet whose `handsRevision` is current and that was marked settled: read as it is;
  2. a stored sheet that is stale, or that holds decisions: laid again on the notes with `reapply`, the file is not
     written;
  3. a stored algorithm sheet that is not current: computed again (`_algorithm_sheet`);
  4. no stored sheet: the algorithm on the starting hands (`_algorithm_sheet`).
- **`reapply(stored, notes)`** runs `propose_frames` on the current notes and gives the stored decisions to every note
  that kept its hand and column: beam group, ornaments, 8va and the user's marks. A new note gets the beam group of the
  rule. `fit_clefs` gives clefs and 8va to a note that moved to the other staff.
- **`mark_settled(part_id, text)`** remembers a text that an edit has just stored as the result of `reapply` (`_settled`,
  64 entries), so that `_compute` does not lay it again. Called by `part_sheet/edits.py` after each edit.
- **`forget(part_id)`** drops a part's cached answer.
- **Starting hands.** `pipeline.starting_hands(part_id)` (`transcription/pipeline.py`): the saved hands, and the hand
  split for the notes that have none. Every new sheet starts from it.

The app writes a sheet with `store.save`, which adds the titles (`with_titles`), writes the record line with the text,
and marks the bundle step as changed.

## 8. The old sheet's marks

`part_sheet/legacy.py` lays what an old `sheet.json` held on an algorithm sheet: the titles, the lyrics, the space
between lines, the figures set by hand, the fingers, and the beam breaks and joins. It does not carry the clef changes,
the octave lines or the decorations. `with_legacy` settles the result, and `Record.legacy` says what was carried. The
details are in the core README, section 17. The reading that the algorithm needs (the armadura and a renamed reference
figure) is `build.reading_of`, which reads `sheet.json` through `pipeline.load_rhythm`.

## 9. Tests

- `tests/test_sheet_frames.py`: figures, spelling, grace notes, beam groups, the armadura, the round trip of the frames text.
- `tests/test_part_sheet.py`: a part's sheet through the routes: the algorithm with no stored sheet, a stored sheet drawn
  with the grace rule of today, the old `sheet.json` key and renamed figure, a new set of notes that forgets the sheet.
- `tests/test_sheet_lengths.py`: the sheet through a change of a part's length (core README section 16).
- `tests/test_sheet_legacy.py`: the old marks (core README section 17).
- `tests/test_sheet_core_golden.py`: the bars path of the research (the golden files are frozen).

## Where to look deeper

- [`events-to-sheet.md`](events-to-sheet.md): from the stored notes to the hand split the sheet starts from
- [`time-matrix.md`](time-matrix.md): the frame and the figure names that stayed of schema 2.0
- [`rhythm-and-annotations.md`](rhythm-and-annotations.md): the old `sheet.json`, still read for its marks
- [`paths-and-data.md`](paths-and-data.md): where these files sit on disk
- [`../../../context/backend/time-model.md`](../../../context/backend/time-model.md): the rules the sheet obeys
- [`../../../aitu-backend/src/aitu_backend/sheet/README.md`](../../../aitu-backend/src/aitu_backend/sheet/README.md): sections 9 (the new sheet), 12 (the app), 16, 17
