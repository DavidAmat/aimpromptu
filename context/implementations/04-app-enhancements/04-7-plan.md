# 04-7: The open points of implementation 04: plan

The brief, with the user's words, is [`04-7-prompt.md`](04-7-prompt.md). The status of every task is in
[`04-7-checklist.md`](04-7-checklist.md). Each phase writes `04-7-implementation-phase-N.md`. The guidelines:
[`guidelines-implementation-plan.md`](../../guidelines/guidelines-implementation-plan.md) and
[`guidelines-communication-with-user.md`](../../guidelines/guidelines-communication-with-user.md). Read
[`04-context.md`](04-context.md) sections 4, 8 and 9 first. 04-4 ("Copy this style") is not part of this.

# 1. Context

Implementation 04 stays open until six points are done or decided (the user, 2026-11-03). When they are, 04 is
closed: the state lines of [`README.md`](README.md), [`../README.md`](../README.md) and
[`../../00-index.md`](../../00-index.md) say so.

| # | Point | Work |
|---|---|---|
| 1 | The clef of the left hand (04-5 checklist, Decisions) | The main work: a new clef rule, measured on every stored sheet |
| 2 | Hard and the figure check (04-context 8.5) | Hard refuses figures shorter than a fusa |
| 3 | A Stop keeps the batches it accepted (04-context 8.5) | Kept; the docs say it clearly |
| 4 | The temporary copies of 20 de Enero (04-context 8.5) | Six TEMP projects deleted |
| 5 | The octaves of the user's words (04-context 8.5) | Already decided; the line of 8.5 closed, no code |
| 6 | From 04-6 (04-context 9.3) | The image rebuild left to the user; the two Transkun tests pass on the CPU |

# 2. The user's answers (the first discussion, 2026-11-03)

| Point | Answer |
|---|---|
| 1. "A whole passage" | **5 columns or more** of the hand. A stretch of the hand's other clef with 1 to 4 columns goes back to the hand's own clef |
| 1. The right hand | **The same rule, the same length**: a short low stretch of the right hand stays in the treble clef |
| 1. Sheets written by the AI (their clefs are stored) | **Remove only the short stretches**: when the sheet is drawn, a short stretch of the other clef goes back to the hand's own clef; every other clef the AI or the user wrote stays |
| 1. 8va in the bass clef | **Allowed.** The rule of 03 "never 8va in the bass clef" (clef rules version 4) ends. A short high stretch of the left hand stays in the bass clef under an 8va line |
| 2. Hard's shortest figure | **Refuse figures shorter than a fusa (32)** at Hard |
| 3. A Stop of a level run | **Keep the accepted batches** (as today). Revert removes the whole run |
| 4. The copies | **Delete all six TEMP projects**: the five of the 04-5 report and a sixth found on 2026-11-03 (section 3.4) |
| 6. The backend image | **The user runs the rebuild** (a HUMAN INTERVENTION step at the end); the agent checks the image after |
| 6. The Transkun tests | No question: a fix of the tests only (section 4.6) |

# 3. What the code and the data hold now (checked 2026-11-03)

## 3.1 Who draws the clefs

The brief says "every stored sheet is laid again when it is drawn, so a change of this rule changes every sheet".
That is true only in part:

| Sheet | Its clefs come from | Changes with `clefs_and_ottavas`? |
|---|---|---|
| Never enhanced (no `sheet.f1`, or `source=algorithm`) | `propose_frames` → `clefs_and_ottavas` | yes, at once |
| A level batch, when it is written | `levels.drawn` → `propose_frames` | yes, for new batches; a stored level sheet keeps the clefs of its time |
| A stored sheet (a whole run of the AI, a level run, the user's edits) | the clefs stored in `sheet.f1` (`build.reapply` keeps them) | only around a note that moved hand (`build.fit_clefs`) |
| The range toolbox: **Clefs and 8va by the rule** | `reading.clef_rule` | yes, on that stretch |
| Transpose | `build.fit_clefs(reading.far_notes)` | around the far notes |

So a change of `clefs_and_ottavas` alone would not reach the stored sheets written by the AI. The user's answer
(section 2) asks it to: a new step on every drawn sheet (section 4.1).

## 3.2 The rule today (`sheet/proposal/frames.py`)

- `STATES`: right hand `G2`, `G2`+8va (`OTTAVA_COST` 2.5 a column), `F4` (`CLEF_PREFER` 0.25 a column); left hand
  `F4`, `G2` (`CLEF_PREFER`), `G2`+8va. No state "`F4`+8va": the 03 rule.
- `BASS_LIMIT = 4`: a left-hand column with a note 4 ledger lines or more above the bass staff (B4 or higher) cannot
  be in the bass clef: one high note forces the treble clef.
- `_path(cost, CLEF_SWITCH, 1, ...)`: the cheapest path, `CLEF_SWITCH` 3.0 a change, `CLEF_IN_BEAM` 3.0 more in a
  beam group; no shortest stretch.
- "Never 8va in the bass clef" is also in: `sheet/sheet/frames.check` ("8va in the bass clef"),
  `sheet/llm/frames.py` (the AI's check, about line 608, and the prompt text about line 1500),
  `prompt/frames/instructions.md` (clef.L1 to clef.L6, line 673), `prompt/instructions.md`, `reading.set_ottava`
  (refused), `reading.set_clef` (a bass clef takes the 8va off), `build.fit_clefs`'s docstring, the frontend
  `FramesRangeToolbox.tsx` (the 8va chips off in the bass clef), the docs `context/ai/stretch.md`,
  `context/frontend/annotations-stretches.md`, `03-context.md` section 2 (a binding decision of 03).
- The level prompts already have the user's rule (`prompt/levels/shared.md`, "The register").

## 3.3 The measure before (read-only, the drawn sheets of the `private` layer, 44 parts)

- The left hand has **89 treble stretches drawn by the rule** (sheets never enhanced): 43 of 1 or 2 columns, 18 of 3
  or 4, 7 of 5 to 8, 21 of 9 or more. **61 of the 89 are 1 to 4 columns long**; 56 of those 61 hold a note B4 or
  higher (they need the 8va line in the bass clef).
- The sheets written by the AI (prompt 5) have **85 left-hand treble stretches**, 77 of 1 to 4 columns, 74 of them
  with a note B4 or higher. Most are in Superestrella (`f4c4de9a`, 77 stretches) and Halleluyah (`43faf78e`, 8).
- The level sheets (`source=mixed`) have no left-hand treble stretch.
- The user set clefs by hand (the undo logs `sheet.edits.json`: "Treble clef for a stretch of the left hand" 1,
  "... right hand" 2, "Bass clef for a stretch of the left hand" 3) in four parts: My Way (`c33860b5`, My library),
  two level copies of 20 de enero (`7b9a41e4`, `946c21f2`, Personal Vault), and TEMP D's level copy (`39d92dbe`,
  deleted in Phase 1).

## 3.4 The TEMP projects (point 4)

| Copy | Id | Where |
|---|---|---|
| TEMP 04-5 A: Strict easy 1 with words | `47999e53-d36c-43e9-8fdb-080fe9bdda98` | Personal Vault |
| TEMP 04-5 A2: Strict easy 1, the pattern's register | `952d4480-8805-46c8-b4a3-3c03dcdb8d2c` | Personal Vault |
| TEMP 04-5 B: Suggested easy 1 | `8e1c50a8-854d-4ff7-9ee1-939172f2341d` | Personal Vault |
| TEMP 04-5 C: Strict easy 5 | `07b1c431-e15f-45b1-ab74-ba11ae33ecd2` | Personal Vault |
| TEMP 04-5 D: first batch, answer, go on | `3ed5bde6-b198-4755-a4c3-26663fe7a9dd` | Personal Vault |
| TEMP 04-5 D: ... · Easy, left hand (a level copy of D, not in the 04-5 report) | `39d92dbe-b897-4ceb-b71c-e98660d8dae7` | My library |

The original song and the user's own level copies of 20 de enero (`7603ca29`, `d6211999`, `7b9a41e4`, `0df15e84`,
`b13cbcde`, `946c21f2`) are not touched.

## 3.5 The other points

- **Hard**: `levels.LIMITS["hard"]` has `shortest` 64; the check (`levels.py` about line 1311) refuses a new note
  only when `n.figure > lim.shortest and not lim.steady`, so at Hard nothing is refused.
- **Stop**: `job._level_work` keeps the batches accepted; `context/ai/level-run.md` line 32 says so. A level run
  works on a level copy, so the original song does not change.
- **Transkun**: `TranskunEngine.__init__` already loads with `map_location=device`. The device is
  `config.device()`, and the container sets `AITU_DEVICE=cuda` (`compose.yaml`). With `CUDA_VISIBLE_DEVICES=` the
  tests ask for `cuda` with no GPU, and `torch.load` fails.

# 4. Design

## 4.1 The clef rule (point 1)

**The rule (the user's words):** a hand changes to its other clef only for a whole passage, that is **5 of its
columns or more** (`CLEF_MIN = 5`). A shorter stretch stays in the hand's own clef: ledger lines, and an octave line
for the notes too far for them.

1. **New states** in `STATES`:
   - left hand: `("F4", 1, OTTAVA_COST)`, the bass clef under an 8va line. `BASS_LIMIT` stays a limit on the
     written note: under the 8va line a B4 is written B3, so the column is allowed.
   - right hand: `("G2", -1, OTTAVA_COST)`, the treble clef under an 8vb line, for a short low stretch with a note
     4 ledger lines or more below the treble staff (D3 or lower). The same limit is added for the right hand in the
     treble clef without the line, so a very low note does not take 5 ledger lines.
2. **The shortest stretch.** A new step `short_clefs(sheet) -> dict` in `proposal/frames.py`: for each hand, each
   stretch in the hand's other clef with fewer than `CLEF_MIN` columns of the hand goes back to the hand's own
   clef (its two clef changes go). Its columns get the octave line (left: 8va; right: 8vb) when a note of the
   column would stand `BASS_LIMIT` ledger lines or more outside the staff; columns of one short stretch that need
   the line share one line when the notes between stay readable under it (as `join_ottavas` does in the treble
   clef). Returns the counts (stretches removed, notes under a new line).
   - It runs at the end of `clefs_and_ottavas` (the sheets never enhanced, the level batches, the range toolbox's
     clef rule, `fit_clefs`), and in `build.reapply` after `fit_clefs` (every stored sheet when it is drawn, the
     AI's clefs included). One step, so the rule's sheets and the stored ones follow one truth.
   - Phase 2 may instead put the shortest stretch inside the cheapest path (`_path` with a shortest stay for the
     other clef only), if the measure of Phase 3 shows the step makes worse sheets. That change is written in
     section 8.
3. **The user's clefs win** (the rule of 04: the user's marks win over the rule). A clef the user set by hand
   (`reading.set_clef`) is never removed by `short_clefs`. Phase 2 chooses the mark (for example a mark of the clef
   change in `sheet.f1`, as `fix` marks a figure) and how the three parts with clefs set before the mark keep them
   (section 3.3: My Way, two level copies of 20 de enero; for example a one-time step that reads their undo logs).
   The measure of Phase 3 checks those three parts by name.
4. **"Never 8va in the bass clef" ends** (the user's answer):
   - `frames.check` no longer reports "8va in the bass clef" (an 8va with a note written 4 ledger lines or more
     above the staff stays a problem);
   - the AI's check (`sheet/llm/frames.py`) no longer refuses it; `reading.set_ottava` allows an 8va over a bass
     clef stretch; `reading.set_clef` keeps the 8va of the notes when it writes a bass clef (if they stay readable);
   - the frontend range toolbox: the 8va chips work in the bass clef (`FramesRangeToolbox.tsx`);
   - the engraver: check that the 8va line over a bass staff is drawn right (the bracket above the staff, the notes
     an octave lower), zoomed in on the drawn pages;
   - the whole-run prompt (`prompt/frames/instructions.md`, clef.L1 to clef.L6, and the text of
     `sheet/llm/frames.py`): the user's rule; `prompt/frames/VERSION` 8 and `frames.PROMPT_VERSION = "8"` (the rule
     of 04-context section 4). The older `prompt/instructions.md` (not used by the app's runs) is checked with
     `git grep` and changed only if a run still reads it. No real run (credits): the step of item 2 writes the
     user's rule on every drawn sheet whatever the AI writes.
5. **Only the clefs and the 8va may change.** The measure (section 4.2) checks it.

## 4.2 The measure of point 1 (read-only)

A script `aitu-backend/scripts/clef_study.py`, made like `scripts/grace_gallery.py --study` (run in the running
container, `docker exec -i -w /work/aimpromptu/aitu-backend aimpromptu-backend-1 python scripts/clef_study.py`):

- **Old and new rule in one run.** A context manager puts back the old `STATES`, turns `short_clefs` off and the
  old checks on (as `grace_gallery.rule("old")` does); the "old" counts must equal the counts of section 3.3.
- **`--study`**: for every part of the `private` layer (the TEMP projects are deleted first), drawn by
  `build._compute` with the old and the new rule: per sheet the clef changes (right, left), the notes under 8va or
  8vb (right, left), the short stretches removed, the seconds it took; and the check that nothing else changed (the
  notes, their hands, figures, beam groups, decoration notes, spelling and armaduras: the `sheet.f1` text without
  the clefs and octave lines is the same). Any other difference is a stop: it is reported, not hidden.
- **The gallery**: the passages that change, drawn by the app, old above new, the clef stretch marked, at most a few
  per song and every kind (a rule sheet, an AI sheet, a right-hand stretch, a column with a wide chord, the user's
  clefs kept). Written to `gallery/04-7/` (as `gallery/phase-2/`), served over HTTP at `http://192.168.0.112:8099/`
  for the Mac, each drawing checked zoomed in against the data before the user sees it.
- It reads only: it never writes a stored file (the rule runs on the drawn sheet, `build._compute`).

## 4.3 Hard's figure check (point 2)

- `LIMITS["hard"]`: `shortest` 32. The check refuses a new note of Hard shorter than a fusa, with the message the
  other levels give ("shorter than the level allows").
- Phase 4 checks which figures the check sees: a decoration note is a fusa or shorter by the app's rule
  (`GRACE_FIGURE = 32`), so a semifusa that the app draws as a decoration note must not make a batch fail. If the
  check sees it, it is left out of the figure check (and a test says so).
- The level prompt: if a text says Hard may write any figure, it says "no figure shorter than a fusa"; a change of the
  prompt gets a new `prompt/levels/VERSION` (8).
- Tests with stand-ins for the AI (no credits): a Hard answer with a semifusa (not a decoration note) is refused; a
  fusa and a decoration note are accepted.

## 4.4 A Stop of a level run (point 3)

No code. `context/ai/level-run.md` and `context/ai/run-history.md` say: Stop keeps the batches already accepted and
saved, on the level copy; **Revert** removes the whole run. A comment in `job._level_work` says the same, with the
user's answer and the date.

## 4.5 The TEMP projects (point 4)

Phase 1, before any edit of `aitu-backend/src`: `ps aux`, `docker logs aimpromptu-backend-1`, no log `ai-runs/*.json`
in `running`. The six projects of section 3.4 are deleted the way the app deletes a project (`api/projects.py`
`delete_project`: `flow.release_levels`, then `bundle.delete_project`, which also removes the history and the
temporary files), in the running container, the level copy `39d92dbe` first. The report lists each id, its title
and that it is gone; the original song and the six level copies of section 3.4 are listed as still there.

## 4.6 From 04-6 (point 6)

- **The Transkun tests**: the two tests (`test_it_satisfies_the_engine_protocol`,
  `test_a_missing_file_is_a_file_error_not_a_model_error`) build the engine with `device="cpu"`. The engine's code
  does not change, so a transcription on the GPU does not change. The whole backend suite on CPU then has 0 failed.
- **The image**: a HUMAN INTERVENTION step of the closing report: when the app is idle, `docker compose build
  backend` and `docker compose up -d backend`. After the user's word, the agent checks `python -c "import openai"`
  in a fresh container (`docker compose run --rm backend ...`) and closes the point in 04-context 9.3.

## 4.7 The docs

- `aitu-backend/src/aitu_backend/sheet/README.md`: the clef rule (the shortest stretch, 8va in the bass clef, 8vb
  in the treble clef, the user's clefs, `short_clefs` on every drawn sheet).
- `context/ai/stretch.md` ("no 8va in the bass clef"), `context/frontend/annotations-stretches.md` (the 8va chips),
  `context/ai/level-run.md` (Hard's figures, Stop), `context/ai/run-history.md` (Stop and Revert),
  `documentation/services/backend/ai-levels.md` if it lists the limits.
- `04-context.md`: 8.5 and 9.3 closed (each line says how), a section 10 for 04-7 (what changed, the decisions that
  bind: `CLEF_MIN`, 8va in the bass clef, the 03 rule changed; Hard's shortest; where the code is). `03-context.md`
  section 2: its row "no 8va in the bass clef" says it was changed by 04-7.
- The 04-5 checklist's clef line marked done, with a link.
- The state lines of `README.md`, `../README.md` and `../../00-index.md`: 04 closed (only when every point is done,
  the image rebuild included or left with the user as said in 9.3).
- `python3 scripts/docs/check-links.py`; `scripts/docs/check-names.py` on each doc changed.

# 5. Phases

| Phase | Work | Checks |
|---|---|---|
| 1 | Housekeeping (no edit of `src/`): the six TEMP projects deleted; the Transkun tests on CPU; 8.5's line on the octaves closed in `04-context.md` | the whole backend suite on CPU, 0 failed; the six ids gone |
| 2 | The clef rule, backend and frontend: the states, `short_clefs`, the user's clefs kept, "never 8va in the bass clef" ended in the checks, the range toolbox, the prompt (version 8); tests | backend suite on CPU; `npx tsc -b`; `npm run check:frames-tools` (the 8va chips), `npm run check:frames-page` |
| 3 | The measure and the gallery: `scripts/clef_study.py --study`, the gallery `gallery/04-7/`, served for the Mac. **The user looks at the drawn passages**; `CLEF_MIN` or the step may change on the user's word (back to Phase 2 for that, written in section 8) | the old counts equal section 3.3; nothing but clefs and 8va changed; each drawing checked zoomed in |
| 4 | Hard's figure check; Stop in the docs and a comment | the level tests with stand-ins; backend suite on CPU |
| 5 | The docs (section 4.7), `04-context.md` 8.5, 9.3 and section 10, the closing report with the HUMAN INTERVENTION of the image rebuild; after the user's rebuild, the image checked and 04 closed | `check-links.py`, `check-names.py` |

Phases 1 and 4 are small; one agent may do 1 and 2 together, or 4 and 5. Phase 3 ends with a decision of the user
(the drawn passages), so it is a phase of its own.

# 6. Rules

- One branch, `feat/04-7-open-points`, from `master`. Merge into `master` only at the user's ok; no PR.
- The app runs in containers that mount this working tree: the backend reloads on every `.py` edit of `src/`, which
  stops a running AI run. Before the first edit of `aitu-backend/src` in a session: `ps aux`, `docker logs
  aimpromptu-backend-1`, and no log `ai-runs/*.json` in `running`.
- Never print or copy a key from `.env`. A host script loads `.env` first (else it opens an empty `.database/`); the
  scripts of this plan run in the running container.
- Tests on CPU (another project often holds the GPU): `docker exec -e CUDA_VISIBLE_DEVICES= -e
  NVIDIA_VISIBLE_DEVICES=void -w /work/aimpromptu/aitu-backend aimpromptu-backend-1 python -m pytest`. No AI request
  in the tests.
- No browser check or script writes on a real library piece: temporary copies only. The measure only reads. No edit
  of `src/` while a browser check runs (both services reload).
- The drawn passages go to the user zoomed in, checked against the data, over HTTP for the Mac
  (`http://192.168.0.112:<port>`), never a file path.

# 7. Risks

- **Every drawn sheet changes at once** (the step runs on every stored sheet). The measure of Phase 3 counts each
  sheet before and after and fails on any change that is not a clef or an octave line. The stored files are not
  written by the step, so going back is a code change only.
- **An 8va over the bass staff with a wide chord**: a column with a low bass note and a high note would put the low
  note very low under the line. The step leaves such a column in the other clef if the low note would stand 4 ledger
  lines or more below the staff, or the gallery shows it to the user; Phase 3 shows every kind.
- **The user's clefs set before the mark**: only three parts (section 3.3); checked by name.
- **The whole-run prompt changes with no real run**: the AI may write a short treble stretch that the step then
  removes; no harm to the sheet, a small waste in the answer. The user may ask for a real run later (credits).
- **Speed**: `short_clefs` runs at every draw; it is linear in the columns. The study gives the seconds per sheet
  (an edit stays near 0.28 s, 04 Phase 2).

# 8. Changes during the work

(Each phase adds its changes here.)

- **Phase 1, the sixth TEMP copy (2026-11-03).** `39d92dbe` is not a project of My projects: it is in My library
  (layer `private`) as the only version (`easy`, version 40) of a song "20 de enero" (song 21108, artist La Oreja de
  Van Gogh) in the user's folder **Karaoke Viernes**, saved on 2026-10-31 at 11:24, and its undo log holds clefs set
  by hand. The app deletes a version of My library with `flow.delete_version` (or the song with `flow.delete_song`),
  not `delete_project`. The user's answer (2026-11-03): delete the whole song; done with `flow.delete_song`. Deleting them did not touch `39d92dbe`: its `levelOf` is in `origin` only, and `release_levels` and
  `bundle.dependents` do not read it.
