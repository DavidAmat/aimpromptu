# 04 · Phase 2: the decoration-note rule

Technical report, for the agents of the next phases. Plan: [`04-plan.md`](04-plan.md) sections 3.1, 3.2, 4.2 and
Phase 2. Branch `feat/04-phase-2` (from `master` at `1966224`). Backend only: no frontend file, no AI call, no
database change, no stored file written.

# 1. What was done

| Task | Result |
|---|---|
| 2.1 Study | Section 2; the script `aitu-backend/scripts/grace_gallery.py --study` |
| 2.2 The rule | `proposal/frames.py`: `find_graces` (fusas or shorter) and the new `lengthen_lone`, in both paths (`propose_frames`, `llm/frames.py` `assemble`); 4 new unit tests and 2 new tests of the part's sheet (section 3) |
| 2.3 Every sheet | `part_sheet/build.py` case 1: a stored sheet whose hands are current is laid again on its notes (`reapply`), as case 2 already was; the stored file is not written (section 4) |
| (new) Pairs beamed | `llm/frames.py` `beam_pairs`: two written notes that a stored sheet held as decoration notes get one beam (section 5) |
| 2.4 Gallery | [`gallery/phase-2/index.html`](gallery/phase-2/index.html), 9 cases, each checked zoomed in against the data (section 6); the user's check is pending |

# 2. Study (task 2.1)

`docker exec -w /work/aimpromptu/aitu-backend aimpromptu-backend-1 python scripts/grace_gallery.py --study` (My
library, layer `private`, 33 parts; `--layers private,vault` for more). Each part is drawn three times by
`build._compute` (nothing stored): the old rule (a copy of `find_graces` as it was, kept in the script), the new
decoration notes without the lengthening (the figure of each note by its own length), and today's code.

| | Right | Left | All |
|---|---|---|---|
| Decoration notes, old rule | 825 | 836 | 1,661 |
| Still decoration notes (fusas or shorter) | 459 | 356 | 815 (49 %) |
| Written with their own figure (mostly a semicorchea before a negra) | 295 | 363 | 658 (40 %) |
| Written longer (a semicorchea before a blanca: a corchea; before a redonda: a negra) | 71 | 117 | 188 (11 %) |
| Other notes written longer (mostly a corchea before a redonda: a negra) | 68 | 22 | 90 |

The largest groups, by the old decoration note's own figure and its main note: a semicorchea before a negra
(written as a semicorchea), a fusa before a corchea (stays), a semicorchea before a blanca (now a corchea).

Per song (the stored sheets are the AI's, or edited by the user):

| Song | Sheet | Old (R / L) | Stay | Own figure | Longer | Others longer |
|---|---|---|---|---|---|---|
| 7 Years — Lukas Graham | stored | 43 / 84 | 0 | 66 | 61 | 4 |
| Birds of a Feather | stored | 5 / 28 | 0 | 31 | 2 | 0 |
| Moonlight Shadow | stored | 56 / 17 | 49 | 21 | 3 | 2 |
| The One That Got Away | stored | 2 / 3 | 1 | 2 | 2 | 26 |
| Can't Stop the Feeling | algorithm | 80 / 91 | 143 | 17 | 11 | 0 |
| 99 Red Balloons | algorithm | 59 / 42 | 30 | 60 | 11 | 10 |

(The whole table, every song: run the script.) 7 Years (the AI's sheet, reference figure 480 ms) has no fusa
before a note, so it keeps no decoration note at all. No sheet has the user's decoration switch (`asgrace` 0,
`nograce` 0); 25 notes have a figure set by hand (`fix`).

**The two images in 7 Years** (the AI's sheet, `1a16a836`): `abuse-decoration-notes.png` is the line of frames
1802 to 2039 (1:12 to 1:22, at a width of 110 staff spaces), the left hand's short notes before blanca chords;
`abuse-decoration-notes-right.png` is frames 2180 to 2302 (Fa 5 at 2235 before the negra Do 5, Si-b 4 at 2197
before a chord). Gallery cases 1 and 2.

**Anything else that changed** (the measure of plan section 4.2), on the 10 stored sheets of My library: nothing
(no beam group outside the changed columns' groups, hand, 8va, spelling, mark, clef or armadura). On the algorithm's
sheets: 19 beam-group changes outside the changed groups, in three songs (2002, Bonfire Heart, Stay the Night): a
note next to a changed note moves into the changed note's group, by the algorithm's beam rules (gallery case 9);
and one clef change that moved by 6 columns in Airplanes, next to two corcheas now negras (the clef rule costs a
change inside a beam group more, and the groups changed there).

# 3. The rule (task 2.2)

`proposal/frames.py`, step 3 of the algorithm, also run by `assemble` (the AI's sheet and every stored sheet laid
again); `trim_beams` and `beam_groups` run after it, so a note written longer leaves or joins its groups.

- **`find_graces`**: the chain is as before: walking back from a note, the columns that are semicorcheas or shorter
  (`RUN_FIGURE = 16`), two figures or more shorter than it, each sounding before the next one by less than its
  figure. It becomes grace notes only when it has one or two columns **and all of them are fusas or shorter**
  (`GRACE_FIGURE = 32`), or when a column is marked `asgrace` (as before: the user's switch makes the whole chain
  grace notes). A column marked `nograce` or `fix` stops the chain, as before.
- **`lengthen_lone`** (new, right after): for each note, `chain` = the columns just before it more than two figures
  shorter (`fig > 4 · main`), and `run` = the chain of `find_graces` (semicorcheas or shorter, two figures or more
  shorter). When both have at most two columns, the columns of `chain` get the figure `4 · main` (two figures
  shorter). The `run` test keeps **the end of a run** as it is: semicorcheas, then a semifusa and a fusa before a
  negra stay written as they are (the first version of the study lengthened the last two; the user's answer says the
  end of a run is never lengthened). A grace note or a `fix` column stops both walks. A `nograce` column may be
  lengthened (it is a written note; no sheet has one today).
- Some results that follow (each in a test): a fusa and a semicorchea before a negra are written with their own
  figures (they are not all fusas; the walk of `chain` stops at the semicorchea, already two figures shorter); two
  semicorcheas before a blanca become two corcheas; two corcheas before a redonda two negras; corchea, corchea,
  semicorchea, blanca: only the semicorchea becomes a corchea.
- `info["lengthened columns"]` counts them in both paths.

Tests (`tests/test_sheet_frames.py`): every row of the table of plan 3.1, two lone notes, two fusas, the mixed pair;
a run of three and of four keeps its figures and its one beam group; the end of a quick run; the user's marks
(`fix` never lengthened nor a grace note, `asgrace` before a blanca, `nograce` on a fusa: written as a
semicorchea). The old test of the two-step rule passes unchanged (its cases are fusas or shorter). The golden files
are of the bars path and did not change.

# 4. Every sheet (task 2.3)

`build._compute` case 1 (a `sheet.f1` written for the `handsRevision` that `notes.pmn` has now) drew the file as it
was. It now goes through `reapply` like case 2: the stored decisions (hands, beams, clefs, 8va, armaduras,
ornaments, the user's marks, the titles and lyrics) laid on the notes, and the rules of today run on them. `stale`
stays `False` for case 1. The file is not written; the next edit stores the sheet drawn now (every edit already
stores `reapply`'s result).

Measured before the change (study, old rule): `reapply` of each of the 16 stored sheets (My library and the
Personal Vault) gives the stored sheet back note for note (figures, grace notes, beam groups, 8va, spelling, marks,
clefs, armaduras). Time of one drawing of a stored sheet on a cache miss (`_compute`, with `starting_hands`):
0.04 to 0.13 s, against about 0.01 s for reading the file before; the cache of drawings (by the files' times) is
unchanged, so it is paid once after a change of the files or a backend reload. The 60 ms of the engine (Phase 1) is
on top, as before.

**One edit.** `check:frames-edit` then measured 10 hand moves at a median of 442 ms (backend 311 ms), against 239 ms
in 03 Phase 10: an edit lays the sheet again and stores the result, and the drawing right after laid that stored
text again. `build.mark_settled(part, text)` now records (in memory, 64 texts) a text an edit stored as `reapply`'s
own result (move hands, take notes off, the reading edits, add a note); case 1 draws such a text as it is, which is
what case 1 did for every stored sheet before this phase. Measured again: median 280 ms (backend 172 ms). Transpose
and a stretch of the AI do more after `reapply` and keep the full path.

One test changed on purpose: `test_sheet_lengths._marked` wrote armadura changes into a stored file without
spelling the notes again, a file the app never stores; drawn through `reapply`, a Do 3 became Si# 2 (the user's
rule 4 in that armadura), and the undo test compared the files. The helper now stores what an edit stores
(`build.reapply` of the changed sheet).

# 5. Two written notes, one beam (new)

Found in the gallery (Moonlight Shadow): two notes that were one pair of decoration notes, now written, printed two
flags side by side: the AI's beam groups never held a grace note (`trim_beams` takes them out). 27 such pairs on the
16 stored sheets, all without a beam. The algorithm's sheets do not have it (`beam_groups` groups them).

`lengthen_lone(..., pairs=)` reports each two columns it handled before one note (the `run` pair, or the `chain`
pair); `assemble` collects the notes the stored sheet held as grace notes (`graces`, from the decisions of the
parts) and `beam_pairs(sheet, pairs, graces)` gives such a pair one beam when both are corcheas or shorter, of one
figure or one figure apart, and neither is in a group. **Only notes stored as grace notes** are beamed: once the
sheet is stored again (any edit) they are written notes, so a beam the user takes away later stays away, and a new
AI run decides its own beams (its answers never carry grace notes). Test:
`test_part_sheet.test_two_grace_notes_of_a_stored_sheet_are_written_as_one_beam_group`.

# 6. Gallery (task 2.4)

`python scripts/grace_gallery.py --out ../context/implementations/04-app-enhancements/gallery/phase-2` (in the
backend container). Nine cases, old rule above, new rule below, as the page draws them (width 110), the passage on a
band, one sentence on what to look at and the list of changed columns read from the data: the two images of
7 Years; Moonlight Shadow (fusas stay, semicorcheas written; a run of fast notes unchanged); Birds of a Feather
(left hand); The One That Got Away (two corcheas before a redonda: negras); 99 Red Balloons (a semicorchea before a
redonda: a negra); Can't Stop the Feeling (a beamed pair written); 2002 (a beam group next to a written note).
`frames.check` finds no new problem in any of them.

Checked zoomed in (Playwright at a device scale of 2, crops at 3 to 8 times): flags of the written notes do not
touch the next chord (about one staff space between them); the beamed pairs, the partial beams (semifusa against
fusa: three beams and a stub) and the regrouped beams of 2002 are right; every listed change was compared with the
drawing. Two things to know: the line breaks move (a written note takes more room than a grace note), and a written
short note stands close to its main note (it sounds just before it).

# 7. Checks

| Check | Result |
|---|---|
| `pytest` (CPU, GPU hidden) | all pass but the two known Transkun tests, whose weights load only on the GPU (03-context section 6) |
| Sheet tests (`test_sheet_frames`, `test_part_sheet`, `test_sheet_llm_frames`, `test_sheet_reading`, `test_sheet_lengths`, `test_sheet_edits`) | 86 passed |
| Golden files | unchanged (bars path) |
| `black --check` on the changed files | clean |
| `check:frames-sheet`, `check:frames-edit` (on copies) | all passed; 10 hand moves, median 280 ms (section 4) |
| `scripts/docs/check-links.py` | passes |

# 8. Notes for later phases

- **Prompt (Phase 3)**: `prompt/frames/instructions.md` lines 17 to 18 still say the old rule ("A sixteenth or
  shorter ... becomes a small grace note"). Not changed here: it is the text of prompt version 5, and plan 4.3 puts
  the new text into version 6. The AI's input does not change with this phase (`_own_figures` shows each note's
  own figure, before the grace rule).
- `beam_pairs` acts only on notes stored as grace notes. A new AI run (Phase 3) that leaves two written short notes
  before a long one without a beam prints two flags: the prompt of version 6 can ask for one beam there.
- The real 7 Years (My library) keeps its file; it is drawn with the new rule now, and the Phase 3 run writes it
  again.
- The documentation updated: the core's `README.md` (section 9, the rule; section 12, case 1). `03-context.md`
  section 2 is pointed at `04-context.md` in Phase 4 (plan).
- The user added `04-2-prompt.md` (a new logo, and that logo as the AI symbol) and `images/the-logo.png` during this
  phase; not part of Phase 2, left for the user to place in the plan.
