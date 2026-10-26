# 03 · Migration plan: the new sheet in aimpromptu

Status: written 2026-10-23, at the end of research plan 01, from the answers of the second discussion (in Spanish).
It was written in the research folder as `context/implementation-plans/01-research-format-llm/05-final-report.md`;
Phase 0 (2026-10-23) copied it here, and **this copy is the living plan** that the agents update (section 6.1).
Section 11 lists what the phases changed. Audience: the AI agents that run the migration on the Ubuntu machine, and
the user, who checks each phase in the browser. Music terms stay in Spanish where the user uses them (negra, corchea,
semicorchea, fusa, blanca, redonda, armadura, sostenido, bemol, becuadro, compás).

**Read first.** In this folder: this file, [`03-prompt.md`](03-prompt.md) (the user's own words, a copy of the
research's `05-final-report-prompt.md`; they win over this file when the two differ), [`03-checklist.md`](03-checklist.md)
and the report of the previous phase. In aimpromptu: `context/language/communication-implementation-plans.md` and
`context/language/communication-style.md` (how to report; identical to the research's `guidelines/`, checked
2026-10-23). Inside the research folder, `/home/david/Documents/projects/music/poc-aitu-research` on Ubuntu:

- `src/aitu_notation/README.md` (the product core: modules, contracts, frozen files);
- `synthesis/01-f1-format.md` (the text format), `synthesis/04-engine.md` (the engine), `synthesis/06-modules.md`
  (the port map), `synthesis/02-llm-step.md` (the LLM step);
- `reports/phase-14.md` and `reports/phase-15.md` (the viewer and the core);
- and, back in aimpromptu: `context/backend/time-model.md` (the five rules), `context/frontend/projects.md`,
  `context/frontend/annotations*.md`, `context/frontend/play-mode.md`, `context/frontend/rendering.md`.

# 1. Context

aimpromptu turns an audio file into a piano matrix notation (`notes.pmn`: one row per note with its onset, length and
hand) and draws a piano sheet from it with vexflow-v2, a separate library (`@aimpromptu/grid-notation`). The sheets
it draws have many problems: long beams of corcheas with no shape, the same space between every note, the wrong `#`
or `b`, notes given to the wrong hand, and many manual corrections that the user has to make in the Sheet step.

Research plan 01 (this folder) built a new chain and measured it on classical scores and on the 32 songs of the
private library:

1. **the algorithm**: from the notes it estimates the pulse, the figures, the beam groups, the spelling and the clefs,
   with no LLM, in about 1 s per song;
2. **the LLM step**: Sonnet 5.5 reads the notes window by window (about 8 compases, at most 200 onsets) and writes the
   whole sheet: hands, figures, beams, clefs. It was the best method on every measure (for example, the hand of 98.8 %
   of the notes as in the printed score, against 93.1 % for today's hand split);
3. **the engine**: it draws the sheet as SVG with the look of the classical editions (Verovio's drawing rules and the
   Leipzig glyphs), in about 140 ms per song, with a cursor map for playback and an id on every notehead.

Phase 15 put this chain into one package with no research code, `src/aitu_notation/`, with golden files that any port
must reproduce. The phase 14 viewer (`viewer/`) shows whole songs with the audio cursor, and it is the reference for
the new view in the app.

# 2. Objective

Replace vexflow-v2 in aimpromptu with the new chain, adapted to the decisions of the second discussion (section 3):
a sheet **without compases, tempo, puntillos or silencios**, where the space between notes follows their timing and
their density, and where Sonnet 5.5 decides the hands and the reading of the sheet in the background while the user
already sees the algorithm's sheet.

At the end of this plan:

- every screen that draws a sheet today (the Sheet step, Play mode, Recording in Sheet, the PDF print, and the others
  found by the inventory) uses the new engine;
- every editing tool that exists today is kept, or the user agreed to drop it;
- the Hands step and the choice of the negra are gone from the flow;
- the frontend no longer depends on `@aimpromptu/grid-notation`, and the backend no longer builds `TimeScorePayload`.

Not in this plan: the difficulty grade, the easier or richer versions of a passage (the 1 to 5 ladder), the reading of
a printed page from an image, and fingering. These parts of the research stay available for later plans.

# 3. Decisions of the second discussion (user, 2026-10-23)

## 3.1 No compases, no tempo, no puntillos, no silencios

The research recommended adding the pulse, the meter and the compás lines back to the sheet (`synthesis/05-
recommendations.md`, R1), because classical beams follow them and the bars engine needs them. The user decided
against it, for this product:

- Classical tempi and compases existed so that a pianist could play a score they had never heard. In aimpromptu every
  sheet can be heard, so the sheet does not need to say everything about the rhythm. The sheet should be simple and
  fast to draw in a web page.
- **No compás lines, no meter, no tempo** on the page. This matches rule 3 of aimpromptu's time model ("no BPM, no bar
  lines, no time signature, no metre"), which therefore stays.
- **No puntillos.** A negra con puntillo is written as the nearest plain figure.
- **No silencios.** A blank space means that the hand plays nothing. Each note sounds when the cursor reaches it.
- **The figure of a note comes from its own length** (its sustain in `notes.pmn`), relative to the reference figure
  (section 3.3). The figure does **not** grow to fill the silence after it. Example: in the left hand a short chord
  is a negra even when the next left-hand note comes much later; the space after it stays blank.

The consequence for the chain: the product sheet is the **F1 frames view** with hands, figures and tags
(`01-f1-format.md` §1.3.1 already allows figures and tags on frame lines), not the bars view. The engine needs a new
layout without compases (phase 3). The algorithm may still estimate a pulse internally to help its own beams and
figures, but nothing of it is printed or stored.

**What the research measured, and what changes.** With pulse and compases, the printed beam breaks of classical
scores were found at about 0.945 (F1 score, 1 = all), against 0.85 with a pulse and no compases. Those numbers
describe classical editions. Without compases, the place where a beam group ends becomes a judgement of the LLM, with
the criteria and limits of section 3.11.

## 3.2 The space between notes

- Both hands share one horizontal position for each onset frame: what sounds together is drawn on one vertical line.
- The width given to a stretch of time depends on how many notes need room in it, in **either** hand. When the right
  hand plays many fast notes and the left hand plays one note, the stretch grows for the right hand, and the left hand
  gets blank space.
- When **neither** hand plays for a while (for example after a redonda), the gap is drawn shorter than its time would
  ask. Empty time does not need empty width.
- The consequence is that the playback cursor moves at different speeds in different passages. This is expected.
- *Phase 3 (the engine):* one x per drawn column; the gap after a column follows the measured spacing model of the
  time to the next column in either hand (the reference figure as its negra), so many short notes in one hand widen
  the stretch for both. Empty time is the time beyond a blanca between two columns (no hand starts a note in it,
  also after a redonda: the user's example); it keeps 30 % of the width it would add. Figures are not read.

## 3.3 Figures and the reference figure

- The user no longer chooses which gap is the negra (today: the histogram of the gaps between onsets, decision D-09 of
  aimpromptu). **The LLM decides it** on the first window: it receives the histogram of the gaps between onsets
  described in words (the peaks and their sizes in ms) and chooses which figure each peak is, so that the sheet reads
  well. The algorithm makes the same choice from its pulse estimate when there is no LLM. The "transpose figures"
  tool of the Sheet step (all negras become corcheas, and so on) stays as the user's override of that choice, which
  respects rule 5 of the time model ("the reader's answer beats the rule").
- A note's figure is the nearest plain figure to its length (no puntillos). Starting values, to tune on real songs in
  phase 2:
  - from the negra and longer figures: the middle point (negra = 200 ms, blanca = 400 ms: 300 ms is still a negra,
    310 ms is a blanca);
  - for the corchea and shorter figures: a point at about 70 % of the way from the shorter figure to the longer one
    (corchea = 100 ms, semicorchea = 50 ms: 90 ms is a corchea, 75 ms is a semicorchea). The user leaves the exact
    split (70/30 or 80/20) to the agent, decided from real songs and shown in a gallery.
- **Grace notes.** A note whose figure is two or more steps shorter than the note that follows it (a fusa before a
  corchea: fusa, semicorchea, corchea) is drawn as a small grace note (acciaccatura or short appoggiatura), so that the
  eye goes to the main note.
- Trills, turns (grupetto) and mordents may be written when they are clear.
- *Phase 2 (measured on the 10 viewer songs):* the split is 0.7. The length is capped at the next onset of the same
  hand, because under the pedal the measured length runs past it (kept when Phase 2 closed); a note followed by
  silence keeps its own figure. Chords and runs of even gaps take one figure. A grace note is a semicorchea or
  shorter that sounds just before its main note. Tuplets are not in the new sheet.
- *Phase 2, the user's review of the gallery:* a beam group holds one figure. One single note of another figure may
  open or close it, never sit inside it, and a group never holds several sub-groups. Any note two figures shorter
  than the next one (a fusa before a corchea) is an acciaccatura.
- *Phase 4:* the reference figure is one request before the windows: the peaks of the gaps between the measured
  onsets in words, and the first 16 s of the song. On the 10 viewer songs Sonnet chose 420 to 700 ms. The figures,
  grace notes and spelling stay rules of the app, computed after the LLM's hands (the cap needs the hand).

## 3.4 Alteraciones (the user's rules)

The classical rule "an accidental lasts until the end of the compás" disappears with the compases. The new rules:

1. Every note outside the armadura carries its sign **each time** it appears. There is no memory of earlier notes.
2. A becuadro is used **only** to cancel a note of the armadura.
3. **No double sharps or double flats.** The plain name of the key that is played is used instead (in Mi mayor, a
   La## is written as Si).
4. A white key is written natural, **except** when its natural name is in the armadura and would need a becuadro. Then
   the other name of the same key is used, with a sign (in Mi mayor, the key Fa is written Mi#, not Fa becuadro). It is
   better to alter a note that is not in the armadura than to cancel one that is.
5. In an armadura with sostenidos, the black keys are written with sostenidos; with bemoles, with bemoles.
6. When a passage has many alteraciones, the LLM may change the armadura for that passage to the one with the fewest
   signs.
7. **A courtesy sign after a becuadro** (user, 2026-10-23, after Phase 2): when a note of the armadura gets a
   becuadro, the first time the same note (the same name and octave, in the same hand) comes back to its armadura
   name, it prints its sostenido or bemol again, if it is in the same beam group as the becuadro or is the next note
   of the hand. It is redundant on purpose, the only exception to "no sign for a note of the armadura": it says that
   the becuadro no longer applies. Later returns print nothing. Rule 7 changes only the printed signs, not the
   names (`frames.printed_signs`).

Rules 1 to 5 make the spelling a pure function of the pitch and the armadura of the passage. Phase 2 checks this and,
if it holds, makes the spelling a rule of the core; the LLM then decides only the armadura of each passage (rule 6).
This also makes transposition simple: the spelling is computed again from the new armadura. The case of Do mayor (no
armadura, so rule 5 gives no answer) is decided in phase 2. *Phase 2:* rules 1 to 5 hold as a function
(`aitu_backend.sheet.sheet.spelling`). Rule 4 keeps the becuadro when the key has no other name with one sign (Sol, Re,
La in Mi mayor). Do mayor: Do#, Mib, Fa#, Sol#, Sib. Rule 4 applies in every armadura, also with one to three signs
(Mi# in Sol mayor, Si# in Re and La mayor, Dob in Fa mayor): the user did not change it when Phase 2 closed.

## 3.5 The flow of a project

- Today the project steps are Source, Audio, Notes, Hands, Sheet. **The Hands step is removed**: the algorithm's hand
  split has many errors that the LLM corrects, and showing it first adds nothing.
- With the notes ready, the user can already play **Notes Falling**, without hand colours and without a sheet.
- The **Sheet step** shows the algorithm's sheet at once.
- The choice of the negra is removed from the user (section 3.3).

## 3.6 The LLM in the background, shown piece by piece

1. The algorithm's sheet is drawn immediately.
2. In the background, the backend sends the windows to Sonnet one after the other.
3. A segment that is being improved is shown with a light grey or transparent look. There is **no text**, only the
   visual sign that it is changing.
4. When a segment comes back, it is not shown all at once: it appears little by little (for example note column by
   column), while the next segment is already at the LLM. The effect is the one of an LLM that writes word by word,
   even though the backend receives whole segments.

## 3.7 Hands: one numeric truth

- The LLM is the first to decide the hands. The user can edit only the segments the LLM has already decided, or the
  segments where it failed (where the algorithm's sheet stays, and the user corrects by hand).
- The truth is numeric: one hand per note, as today in `notes.pmn` (the backend paints a left-hand matrix and a
  right-hand matrix from it). The LLM's hands are written there; a hand moved by the user is written there too.
- When the LLM runs again on a part, its input is built from that numeric truth, so it receives the user's changes.
  The text format is only a view made for the LLM; it is never the stored truth of the hands.
- *Phase 6 (the user's answer, 2026-10-25):* a run again **may change any hand**, the user's moves included: on a
  sheet the AI enhanced, the input shows every current hand as a suggestion (one line of the window prompt says so).
  A first run reads the notes without hands (the hands are then the hand split's). Nothing can be edited while the
  AI writes the sheet.
- *Phase 7 (the user's answer, 2026-10-25):* a run again on the whole sheet keeps the marks only the user writes
  (fingers, a figure set by hand, the grace note switch) and writes the AI's own kinds again (beams, clefs, 8va,
  armaduras, ornaments), as it does the hands.

## 3.8 Access to Sonnet 5.5

The backend uses the official `anthropic` Python SDK with an API key. The user's Claude Max 5x subscription includes
100 USD of API credits per month (`context/claude/01-uso-claude-api-con-subscripcion.md`): the key is created in the
Claude Console organization linked to those credits. At about 1 USD per 4-minute song (research estimate), this is
about 100 songs per month. When the credits are used up, the requests stop without extra charges: the product must
then keep the algorithm's sheet and say nothing alarming (the segments simply stay as they are, and stay editable).
The Batch API (half price, results within hours) does not fit the piece-by-piece view and is not used.

## 3.9 Where the work runs

- The research folder is copied to Ubuntu as `/home/david/Documents/projects/music/poc-aitu-research` (section 10).
- The agents run on Ubuntu, in the aimpromptu repository, on a new branch **`feat/migrate-new-logic`**. They read the
  research folder as the reference and copy code from it into aimpromptu.
- This plan is written here; phase 0 copies it into aimpromptu, where it becomes the living plan (section 6.1).

## 3.10 Everything that depends on vexflow-v2 moves to the new engine

The research covered the basic drawing: the two staves, the hands, the figures, the beams, the alteraciones, the
armaduras, the clefs, the grace notes and the ornaments. The app has more: lyrics, transpose figures, transposition of
notes, octave brackets (8va), clef changes from treble to bass and back, and others. **All of them are kept.** The plan
does not list them now: each phase first makes the inventory of its part of the app, then adapts its own tasks, and
asks the user only the questions that the study cannot answer. The new engine must stay light and fast while it gains
these features.

## 3.11 Beam groups: the LLM decides, with limits (user, 2026-10-23)

Very long beam groups of corcheas do not help the pianist: the eye cannot find a shape in them. Without compases, the
end of a group is not given by the bar or the beat any more, so **the LLM decides where to cut, by musical judgement**.
This is a criterion to give the LLM, not a problem to solve.

The LLM cuts a group:

- **at a jump**: the next note is far from the previous one;
- **where the direction changes or a pattern breaks**: for example an ascending line that turns down, or a figure that
  stops repeating;
- **to show a repeated contour**: when the notes go up and down, up and down, one group is one rise and one fall, then
  the next group is the next rise and fall, so the groups repeat the same shape;
- **at a maximum length**: a group never has more than **8 notes** (starting value; the LLM cuts earlier whenever one
  of the reasons above applies).

Other good reasons are allowed (the LLM knows many ways to read a figure); the rules above are the minimum. The left-hand
rule of the research stays: a left-hand pattern (an arpeggio, a bass and chord figure) is never cut between the two
hands. The algorithm, as the fallback, uses simple versions of the same rules: the maximum of 8, a cut at a large
jump, a cut where the direction changes after a run. Phase 4 writes these criteria into the prompt and the checker
(the maximum as a hard check, the others as instructions), and the user judges the groups by eye in the gallery.
*Phase 4:* prompt version 5, rules beam.1 to beam.8. A group the LLM writes is cut only where the rule's figures
break it; a semicorchea beamed to the corchea after it (two notes, one odd) is kept, by the user's rule. On the 10
songs 1,888 of 2,046 groups stay as written, mostly of 2 to 4 notes.

# 4. Binding rules

| Rule | Source | In this plan |
|---|---|---|
| 1. The stored notes are the piece; what changes only the reading is stored beside them | time model | kept: the new sheet is stored beside `notes.pmn` (for example `sheet.f1` next to `sheet.json`), except the hands, which stay in `notes.pmn` (section 3.7) |
| 2. A column never moves | time model | kept: every line of the F1 frames sheet is keyed by its frame |
| 3. No BPM, no bar lines, no time signature, no metre | time model | kept (section 3.1) |
| 4. `frameMs` is a view | time model | kept |
| 5. The reader's answer beats the rule | time model | kept: every automatic choice keeps a manual override, applied last |
| D-09: the app presents the gaps and the reader names the negra | 03 decisions | **changed**: the LLM (or the algorithm) names it; transpose figures is the override |
| D-31: the saved hands | 03 decisions | kept, but written first by the LLM instead of **Predict hands** |
| The left-hand clef rules, version 4 (bass, then treble, then treble + 8va; never 8va in the bass clef) | research phase 14 | kept: already in the frozen prompt. Phase 7: the product check (`frames.check`) forbids 8va and 15ma in the bass clef, not an 8vb that the user puts under very low notes |
| One notehead for one pitch at one time in one hand | research phase 11 | kept (`merge_unisons`) |
| Minimal UI (`09-minimal-ui-guidelines.md`) | aimpromptu | kept: no text for the LLM progress, only the visual sign |

# 5. What is reused

| Part | Where (research folder) | Use |
|---|---|---|
| Product core | `src/aitu_notation/` (`sheet`, `proposal`, `llm`, `engrave`; standard library + numpy) | copied into the backend in phase 1 |
| Golden files | `src/aitu_notation/tests/golden/` (2.4 MB) | the port must reproduce them before any change |
| Frozen prompt (version 4) | `src/aitu_notation/llm/prompt/` | the base of the new prompt (phase 4) |
| Viewer | `viewer/index.html`, `viewer/server.py` | the reference for the new view: cursor, lit notes, click to seek |
| Recorded LLM runs | `experiments/E07-pop-songs/runs/` (Opus and Sonnet sheets of the library songs) | comparisons in phases 2 to 4 |
| Measurements and rules | `rulebook/`, `synthesis/03-metrics.md` | background for the decisions |
| `aitu_backend.pmn`, `aitu_backend.matrix.keys` | aimpromptu | used instead of the core's copy `sheet.pmn` (identical, checked 2026-10-23) |

Two facts checked on 2026-10-23 that correct `synthesis/06-modules.md`: `aitu_backend/notation/` is not empty (5
modules for vexflow-v2: `figures`, `tuplets`, `trills`, `transpose`, `decorative`, about 860 lines), so the core needs a
folder of its own (proposal: `aitu_backend/sheet/`); and 13 frontend files import `@aimpromptu/grid-notation` (9 in
`src/pages/piece/sheet/`, 2 in `src/music/`, 2 in `src/components/time/`).

# 6. Method

## 6.1 Documents

Phase 0 creates the implementation folder in aimpromptu with its numbering rule (`context/implementations/README.md`):
`03-prompt.md` (a copy of `05-final-report-prompt.md`), `03-plan.md` (a copy of this file), `03-checklist.md`, a
`README.md`, and one report per phase, `03-implementation-phase-N.md`. From then on the aimpromptu copy is the plan
that agents update. The plan proposed the folder name `03-new-sheet/`; the user had already made
`context/implementations/03-apply-poc-research/` (with the first message of Phase 0, `03-apply-research-prompt.md`),
so Phase 0 used that folder. It is group 03 with one implementation, so its files sit at the top of the folder, as in
`02-private-web-app/`. Screenshots go into `screenshots/phase-N/`.

## 6.2 Every phase

1. **Study first.** Read the code of the part of the app that the phase changes, and list what exists today (features,
   routes, files, saved data). The list goes into the phase report.
2. **Adapt the plan.** Change the tasks of the phase (and later phases if needed) from what the study found, and write
   why.
3. **Ask the user only after the study**, and only for product choices that the code and the data cannot settle: what
   the user wants as the final result, or an important decision. Technical choices are taken by the agent from evidence
   and written in the report with their numbers.
4. **Build small, then larger**: a few passages or one song first, then the 10 viewer songs, then the whole library.
   LLM tests start with a few windows (credits are limited).
5. **Show the result.** Every visible change is checked in the browser by the user: in the app itself
   (`http://ubuntu:5173`), and for drawing changes also in a side-by-side gallery (the reference, the old sheet, the new
   sheet) with one sentence per example that says what to look at. The user is picky about engraving: smooth outlines,
   correct spacing.
6. **Keep the checks green**: the backend tests, the frontend checks, the golden files of the core (until a phase
   changes them on purpose and says why), and `scripts/docs/check-links.py`.
7. **Update the documentation** of aimpromptu that the phase makes stale (`context/00-documentation-instructions.md`).
8. **Report** with the two reports of the guidelines: the technical phase report, and the walkthrough message to the
   user (SUMMARY, CRITICAL ISSUES, DECISIONS, HUMAN INTERVENTION, HAND OFF).

## 6.3 Branch

All the work goes on `feat/migrate-new-logic` in aimpromptu, one or more commits per phase. At the start of each phase,
merge `master` into the branch if `master` moved. Whether to merge the branch into `master` before the end (for example
after phase 5, when the new sheet is visible but vexflow-v2 still edits) is asked to the user at the end of phase 5.

## 6.4 Where the engine runs

The engine runs **in the backend, in Python**, first. It exists, it is measured (about 140 ms per song, 1.9 ms per
compás of the research), and it can draw one segment at a time for the piece-by-piece view. A TypeScript port in the
browser is decided only in phase 6, from the measured time of one edit (change, new drawing, back in the page).

# 7. Phases

## Phase 0: The research folder on Ubuntu, the branch, the inventory

**Done 2026-10-23** ([`03-implementation-phase-0.md`](03-implementation-phase-0.md)).

*Why:* the agent of every later phase needs the research code and documents on Ubuntu, and a first map of everything
that vexflow-v2 does today, so that the later phases know their size.

1. Check the research folder (section 10): `uv sync` in it, then the core tests (`uv run pytest
   src/aitu_notation/tests`, 139 tests) and the golden files pass on Ubuntu.
2. Create the branch `feat/migrate-new-logic` in aimpromptu and the implementation folder (section 6.1).
3. **Inventory, high level**: every screen and every tool that uses vexflow-v2 or `TimeScorePayload` (start from the 13
   frontend files, the `/time/{uuid}/score` routes, `notation/`, `matrix/ladder.py`, `time_pipeline.to_score_payload`,
   the `sheet.json` fields of `synthesis/06-modules.md` §6.6). One table: feature, screen, files, which phase moves it.
   No deep study here: the phases do it.
4. Screenshots of every screen that shows a sheet today, as the baseline.

*Done when:* tests pass on Ubuntu, the branch and the folder exist, the inventory table and the screenshots are in
the report. No change to the app.

## Phase 1: The core inside the backend

**Done 2026-10-23** ([`03-implementation-phase-1.md`](03-implementation-phase-1.md)).

*Why:* before changing anything, the research code must run inside the backend exactly as it ran in the research.

1. Copy `aitu_notation` into the backend (`aitu_backend/sheet/`: `aitu_notation.X` is `aitu_backend.sheet.X`), with
   its frozen files; the golden tests go to the backend's `tests/` (`test_sheet_core_*.py`, `tests/golden/sheet/`).
   Replace the core's `sheet.pmn` with imports of `aitu_backend.pmn` and `aitu_backend.matrix.keys`, after checking
   again that they did not change.
2. The golden tests pass inside the backend container; the backend tests are unchanged.
3. A small backend command (`scripts/draw_sheet.py`) that draws library songs with the bars engine, to prove the
   chain runs in the container (time per song in the report).

*Done when:* the golden files are reproduced in the backend; no change visible to the user.

## Phase 2: The new sheet without compases (format and algorithm)

**Done 2026-10-23** ([`03-implementation-phase-2.md`](03-implementation-phase-2.md)). The user checked the gallery
after two review iterations (beam groups of one figure, acciaccaturas by the two-step rule).

*Why:* the product sheet is now the F1 frames sheet with the rules of section 3. The format, its reader and writer, and
the algorithm that writes it come before the engine and the LLM, because both depend on them.

1. Study: what the F1 frames view carries today, and what the algorithm needs from the pulse estimate (beams,
   figures, graces) once nothing is printed.
2. The format: hands, plain figures (no puntillos), beam groups, graces, ornaments, clef changes, armadura changes per
   passage, 8va; no rests, no compases. Reader, writer and round trip with the matrix (every onset kept).
3. **Figures from the note's own length** with the reference figure, and the thresholds of section 3.3, tuned on the 10
   viewer songs (MuScriptor's note lengths may be noisy under the pedal: measure it). Decide one figure per chord per
   hand when its notes have different lengths. *Done:* the split is 0.7; under the pedal 23 to 60 % of the notes sound
   past the next onset of their hand, so the length is capped there (a decision for the user); one figure per chord
   (the most common) and per run of even gaps. Notes struck together are grouped on raw onsets first (D-04), or the
   first note of an uneven chord becomes a false grace note.
4. **Grace notes** from the two-step rule (section 3.3). *Done:* a semicorchea or shorter, two figures or more shorter
   than the next note and sounding just before it (the gap is shorter than that note's figure). After the user's review
   of the gallery, beam groups hold one figure (one single odd note at an edge at most).
5. **Alteraciones** (section 3.4): check that rules 1 to 5 give one spelling per pitch and armadura; write it as a rule
   of the core; decide Do mayor; the algorithm proposes the armadura of each passage with the fewest signs. *Done:*
   one name for every key and armadura (`spelling.check_rules`); Do mayor Do#, Mib, Fa#, Sol#, Sib (research
   rulebook); rule 4 in every armadura, as written (95 of its 110 notes in the
   library).
6. The algorithm (`proposal`) writes this sheet for every library song, with the simple beam rules of section 3.11
   (at most 8 notes, a cut at a large jump or where the direction changes after a run). Its starting hands are the
   saved hands plus the beam search of `aitu_backend.hands` for the notes that have none (`hand_sheet`), as in the
   research: Phase 1 found 1,652 notes without a saved hand in 32 of the 33 library songs, and the core's default
   (`hand_sheet_of`) gives those a hand by middle C only. *Done:* `propose_frames`, `pipeline.starting_hands`,
   `scripts/write_sheet.py`: 33 of 33 songs valid, round trip exact, about 0.2 s per song after the hands.
7. Gallery for the user: the same passages as text and as notes for figures, graces and alteraciones, including the
   unusual cases of rule 4 (for example Mi# and Si# in Mi mayor), so that the user confirms the rules by eye.
   *Built:* `gallery/phase-2/index.html` (15 cases, drawn by Verovio until the Phase 3 engine exists).

*Done when:* every library song gets a valid F1 frames sheet from the algorithm, the round trip is exact, and the user
has checked the gallery.

## Phase 3: The engine without compases

**Done 2026-10-24** ([`03-implementation-phase-3.md`](03-implementation-phase-3.md)). The user checked the gallery
("perfect"): the spacing is approved, and an armadura change has no double line (the default; `Options.key_line`
stays available).

*Why:* the bars engine needs compases for its spacing, its accidentals and its line breaks. The new sheet has none, so
the engine needs a new layout. The look of each element (noteheads, stems, beams, graces, clefs, Leipzig glyphs, the
Verovio drawing rules) stays.

1. Study: which parts of `engrave` depend on compases (spacing, justification, line breaks, accidentals, rests, bar
   numbers) and which parts are reused unchanged. *Done:* the chords, voices, rests, accidentals, columns, spacing
   and line breaks of `layout` work per compás; every function that draws one chord, beam, grace note, ornament,
   8va, ledger line, clef or the brace is reused as it is. The new layout is `engrave/frames.py`; the bars engine and
   its golden files did not change.
2. **Spacing** (section 3.2): one x per onset frame for both hands; the width of a stretch from the notes that need room
   in either hand; compressed width when neither hand plays. Start from the measured spacing model and tune by eye.
   *Done:* section 3.2, the Phase 3 note.
3. **Line breaks** without compases (for example between beam groups, at the larger gaps); a stable rule so that a
   changed segment moves the rest of the sheet as little as possible (the piece-by-piece view of phase 5 needs this).
   *Done:* never inside a beam group when a free place exists; the break after the longest pause once the line is
   80 % full. A changed 10 s window moved no later line in 27 of 30 windows (fill to the end: 24 of 30).
4. Accidentals on every altered note (section 3.4: `frames.printed_signs`, rules 1 and 7), no rests, no compás lines, no meter,
   no bar numbers. A figure may be longer than the gap to the next note (it is rounded to the nearest figure), so the
   spacing must not read figures as durations. *Done*, and armadura changes inside a line (cancelling becuadros,
   optionally a thin double line), clef changes (between a grace note and its note when it sounds before the
   change).
5. Cursor map and note ids, as in the research (`render_song`), and drawing **one segment** on its own. *Done:*
   `render_frames(segment=(a, b))` draws the systems that hold the segment with the line breaks of the whole song,
   so that the page can replace them in place.
6. Speed: per song and per segment, cold and warm, on the 10 viewer songs, in the backend container. Phase 1 found
   the container about 30 % slower than the host on the same code (155 ms against 118 ms per song); the likely cause
   is the image's Python build (Debian's, shared `libpython`), and uv's Python in the image is the first thing to
   try. *Done:* 58 ms per song warm in the container (median of 33), 31 ms per 10 s segment; uv's Python in a test
   image takes the container from 32 % to about 8 % slower than the host. The image is not changed yet (a rebuild
   restarts the app); Phase 5 does it when the engine is served.
7. Gallery: the same passages drawn by vexflow-v2, by the bars engine and by the new engine, side by side.
   *Built:* [`gallery/phase-3/index.html`](gallery/phase-3/index.html), 8 passages and one whole song.

*Done when:* the 32 library songs draw without error, the speed table is in the report, and the user has approved the
look and the spacing in the gallery.

## Phase 4: The LLM step for the new sheet

**Done 2026-10-25** ([`03-implementation-phase-4.md`](03-implementation-phase-4.md)). The user checked the gallery
("all good"): the beam groups and the hands are approved; rule clef.L4 and the staccato figures stay as written
(the user did not choose another option).

*Why:* the frozen prompt asks Sonnet for F1 bars. The new sheet has no compases, and several decisions are now rules
(figures, spelling). Sonnet must write the new format, and decide what is left: hands, beam groups, clefs, 8va, graces
and ornaments, the armadura of each passage, and the reference figure on the first window.

1. **HUMAN INTERVENTION at this phase**: the user creates the API key in the Claude Console organization linked to the
   Max 5x credits and puts it in `.env` on Ubuntu (`ANTHROPIC_API_KEY`). Three test requests: their `usage` numbers
   and time. *Done:* an individual organization, no card; the cached instructions are 9,080 tokens, a cached
   reference request costs $0.009.
2. `complete(system, messages)` with the `anthropic` SDK, model `claude-sonnet-5-5`, prompt caching of the fixed
   instructions, time limits and retries (the product's job, `aitu_notation/README.md` §5). *Done:*
   `aitu_backend/sheet_llm.py`, streamed requests, adaptive thinking at effort `high`, the server-side fallback; a
   refusal fails one window, any other error keeps the algorithm for the rest of the song.
3. The new prompt (version 5) from version 4: the new format, the histogram of gaps in words for the reference figure,
   the alteraciones rules, the beam group criteria of section 3.11 (with a few examples of groups cut at a jump, at a
   change of direction and by a repeated contour), the clef rules version 4 unchanged. Windows by onsets or by time
   instead of compases. *Done:* `sheet/llm/prompt/frames/`; the LLM decides hands, beam groups, clefs and 8va,
   ornaments and the armadura of passages; the input shows the rule's figures of the starting hands and no hand.
   Windows of 12 to 16 s that end at a pause and outside the algorithm's beam groups, every answer kept whole (no
   bar decided twice): they are known before any request, so Phase 5 can use them as its segments.
4. The checker and the guards (beam share, beam overlaps, and at most 8 notes per beam group) for the new format; the
   fallback to the algorithm. The checker is `frames.check`; an answer is mapped back to the notes
   (`frames.cells_of`) and its figures are computed again by the rule (they need the measured lengths). Phase 2 left
   two points for the LLM: octaves played 40 to 80 ms apart stay two columns (the LLM may join them with `arp`), and
   tuplets are out of the product sheet unless this phase shows that the LLM's triplets read better. *Done:*
   `sheet/llm/frames.py` (`check_answer`, `assemble`); also no note four or more ledger lines above its staff
   (clef.L3, clef.6), added after the first run; nearby 8va notes joined into one line. Tuplets stay out: the
   new prompt has none, and no answer needed one; `arp` was written 94 times.
5. Test on a few windows, then the 10 viewer songs. Compare with the recorded Sonnet sheets of the research (same hands,
   beam groups). Real cost per song from `usage`, and how many songs the monthly credits cover. *Done:* 150 of 150
   windows accepted, $8.86 for the 10 songs ($0.51 to $1.73, median $0.77), 4 to 17 minutes per song; about 110
   songs a month. Same hand as the research's Sonnet on 96.3 to 99.8 % of the notes (the algorithm 88.7 to 99.1 %).
6. Gallery for the user: the algorithm and Sonnet, side by side, on the same passages. *Built:*
   [`gallery/phase-4/index.html`](gallery/phase-4/index.html), 10 passages.

*Done when:* the 10 songs are written by Sonnet in the new format, the cost table is in the report, and the user has
checked the gallery.

## Phase 5: The new Sheet step (to see and to hear)

**Done 2026-10-25** ([`03-implementation-phase-5.md`](03-implementation-phase-5.md)). The user checked it in the browser
("perfect"), asked for the wording "AI" (**Enhance with AI**, the green **Enhanced with AI** badge, **Enhance it again
with AI**) and for the AI mark on Projects and My library; the branch was merged into `master` (the user's answer to
task 10).

*Why:* this is the first time the user sees the new sheet inside the app, with the new flow of sections 3.5 and 3.6.

1. Study: the project steps, the Sheet step page, the jobs and progress stream of the transcription, how parts are
   stored, and how existing projects (with saved hands and `sheet.json` corrections) should open. **Question to the
   user after the study**: what happens to existing projects (redo them with the LLM, or keep their corrections; see
   phase 9). *Answered 2026-10-25:* the songs Sonnet already wrote (the 10 viewer songs of Phase 4) show Sonnet's
   sheet; every other song keeps its data and shows the algorithm's sheet from its saved hands, with a button that
   runs Sonnet on the whole piece; new transcriptions go to Sonnet by themselves.
2. The flow: Hands step removed; Notes Falling playable without hands; the negra choice removed. *Done:* four
   steps; the Sheet step opens once the notes are ready; the events route gives only saved hands; the negra choice
   is not on the new sheet (the old sheet keeps it until Phase 8). A part of a version keeps the key and, when the
   user renamed it with Transpose figures, the reference figure of its `sheet.json` (the negra of the highest pile
   was vexflow-v2's default, and the pulse estimate replaces it).
3. The Sheet step draws the algorithm's sheet at once, then starts the LLM job of the part in the background. Each
   segment being improved looks grey or transparent; a finished segment appears little by little while the next one
   is at the LLM; no text. *From Phase 3:* `render_frames(segment=(a, b))` gives the systems of a segment with the
   line breaks of the whole song (about 30 ms), and the cursor map gives the x of every column for a reveal column by
   column. Before the engine is served, the backend image takes uv's Python (Phase 3 measured the Debian build 32 %
   slower than the host, uv's 8 %). *From Phase 4:* the segments are the LLM's windows (`windows_of`, 12 to 16 s);
   the reference request comes first (about 5 s) and changes every figure, so the algorithm's sheet is drawn again
   whole before the first window returns (about 30 s per window); the image needs the `anthropic` package.
   *Done:* `part_sheet/` and `api/sheet.py` in the backend, `pages/piece/sheet/frames/` in the frontend; the page
   reads the whole sheet again at each window (about 40 ms to draw) and covers the segment that came back with blank
   staves that move away column by column; the segment at Sonnet has a pale veil. A new transcription is marked
   (`sheet.pending`) and its Sheet step starts Sonnet; a part made before stays as it is and offers **Write with
   Sonnet** (on a version of My library, through its edit copy: the library is never written in place). A deleted
   part stops the requests. The backend image runs uv's Python with `anthropic`.
4. The LLM's hands are saved in `notes.pmn` (Hands colours in Notes Falling and Play mode follow them). *Done:*
   at the end of the run; hands saved before go to the part's history.
5. The new sheet is saved beside `sheet.json`; reopening a part does not call the LLM again. *Done:* `sheet.f1`,
   carried by duplicate, export, Save to library and the history; laid again on the notes after a notes or hand
   edit. The 10 viewer songs got the sheets Phase 4 paid for (`scripts/import_llm_sheets.py`).
6. Playback: the cursor from the audio time, lit notes, click to seek (from `viewer/index.html`). *Done*, in the
   Sheet step and in Play mode (the cursor's line kept in the middle; no lyrics until Phase 8).
7. vexflow-v2 stays reachable for editing (a switch) until phase 8. Segments still waiting for the LLM cannot be edited.
   The switch belongs inside `SheetPage`: six screens draw their sheet through it (Phase 0 inventory), so the new view
   reaches them all at once, and each screen-specific part (Play mode, the passage page, the requests review) is
   checked in phase 8. *Done:* the new sheet is first on the Sheet step, a version of My library and Play mode; the
   passage page, From other projects and the requests review keep the old sheet until Phase 8 (their work is a
   marked stretch, which the new sheet has not yet).
8. The browser checks (`check:*`, `bench-sheet`, `time:flow`: 16 scripts) find the sheet by the classes of vexflow-v2
   (`.grid-note-target`, `.grid-frame-ruler`, `.grid-onset-group`, and others). The new view gives the same hooks as
   `data-*` attributes, and each check moves to them with its screen (the Sheet step checks here, the others in
   phases 6 to 8). *Done:* `check:frames-sheet` (new); `check:play` on the new hooks; the old sheet's checks press
   the switch first (`session.oldSheet`); `check:flow`, `check:journey` and `time:flow` walk the new flow (not run:
   they transcribe on the GPU and start Sonnet).
9. The line above each passage of the sheet that names the main figure and a tempo (`corchea = 217 ms · ≈138 BPM`,
   `matrix/ladder.header_label`) is not drawn on the new sheet (section 3.1). *Done* by the new sheet.
10. **Question to the user at the end**: merge the branch into `master` now, or at the end. *Answered:* now
    (2026-10-25); later phases go on on `feat/migrate-new-logic` and merge again at their end.

*Done when:* a new project goes from audio to the new sheet with the piece-by-piece view, and the user has checked it
in the browser on a few songs.

## Phase 6: Editing the new sheet (the edit model, hands, undo)

**Done 2026-10-25** ([`03-implementation-phase-6.md`](03-implementation-phase-6.md)). The user checked everything in
the browser; the audio after a jump was fixed during the check (report section 8), and the user's requests for the
range selection and Enhance with AI of a stretch went to Phase 7 (tasks 4 and 5).

*Why:* every editing tool needs one common way to work on the new sheet before the tools are moved one by one.

1. Study: how vexflow-v2's editor applies a change today (selections, `sheet.json` writes, undo and redo). *Done:*
   the page holds every reading decision in one value (`SheetEdits`) saved by **Save** into `sheet.json`; six edits
   are written to the recording at once (a hand move is `PUT /time/{uuid}/hands`); one undo history in the page
   (`useEditHistory`, one press one step, a step may carry the backend calls that take it back), lost on a reload.
2. The edit model: an edit changes the numeric truth (hands in `notes.pmn`) or the stored sheet, then the engine draws
   the affected segment again. Undo and redo on top of it. *Done:* `part_sheet/edits.py`: one write under the part's
   lock changes the hands and stores `sheet.f1` laid again on them (it stays current and keeps its AI mark); the
   answer is the whole sheet drawn again (about 50 ms in the backend), not one segment. Every edit is a step of the
   part's log `sheet.edits.json` (each note's hand before and after, one line patch of `sheet.f1` both ways), kept by
   the backend: undo and redo survive a reload. No Save button on the new sheet.
3. First tool: move notes from one hand to the other. Running the LLM again on a part sends the current hands
   (section 3.7). **Question to the user after the study**: may a new LLM run change notes that the user moved by hand?
   *Done:* notes are picked on the sheet (click, ⌘ or Shift, a box), the note toolbox has **Hand: Right / Left**.
   A note that changes staff gets the clefs and 8va of the clef rules around it (`build.fit_clefs`). The user's
   answer: a run again may change any hand (section 3.7); tested on 2 windows of 7 Years with 3 notes moved to the
   wrong hand: Sonnet moved the 3 back and changed no other of the 137 notes ($0.06).
4. Measure the time of one edit (click, backend, new drawing in the page). **Decision with numbers**: keep the engine
   in the backend, or port it to TypeScript in the browser (`synthesis/04-engine.md` §4.5). *Done:* about a quarter
   of a second from the click to the new drawing (report section 6); the engine **stays in the backend**: the drawing
   is about a third of the backend's time, and the rest (the rules that lay the sheet on the new hands) would need
   the whole core ported.

*Done when:* hand moves and undo work on the new sheet, and the engine location is decided.

## Phase 7: The note and range tools

**Done 2026-10-26** ([`03-implementation-phase-7.md`](03-implementation-phase-7.md)). The user checked the gallery
([`gallery/phase-7/index.html`](gallery/phase-7/index.html): "all good") and the tools in the browser ("all good");
the AI on a stretch was reworked during the check (report section 9: the user's words first, a simpler sheet,
pitches, added notes and figures). Merged into `master`.

*Why:* the note toolbox and the range toolbox of the Sheet step hold most of the editing tools (`annotations-notes.md`,
`annotations-stretches.md`).

1. Study and inventory: every tool, what it changes today, and its place in the new sheet. Some tools may no longer
   make sense without compases or with the measured spacing (for example the spacing sliders, the anchors and speed
   changes): the list of those goes to the user before anything is dropped. *Done* (report section 2): the user's
   answers of 2026-10-25 drop even spacing, the room of a stretch, speed changes, print smaller, the decoration that
   is not played (replaced by a grace note switch), and hiding or dragging an 8va bracket. Transpose figures and the
   transposition of notes are in the sheet toolbox, so they move to Phase 8 with it; so do the title-bar actions
   Copy, Record this passage and Start a new part.
2. Build them on the edit model: figures, transpose figures, fingers, beam joins and breaks, decorations and trills,
   clef changes, 8va brackets, armadura of a passage, transposition of notes, and the others the inventory finds.
   *From Phase 6:* an edit is a function of `part_sheet/edits.py` that changes `notes.pmn` or `sheet.f1` under the
   part's lock and records one step (`_Step`: hands before and after, a line patch of `sheet.f1`); a route of
   `api/sheet.py` answers the sheet drawn again; a row of `FramesNoteToolbox.tsx` calls it through `useFramesSheet`'s
   `edit`. A reading edit on a sheet the algorithm wrote must store it (today an `algorithm` record is computed
   again, not read), so the record needs a source for "the algorithm's, edited by the user". *Done:* `part_sheet/reading.py` and `edits.edit_reading` (the
   sheet drawn now is changed, laid again on the notes so the rules run, checked to hold what was asked and to break
   no rule, stored with `Record.edited`); figures (set by hand, `fix`), fingers (`fg3`; on one chord from the thumb
   in the right hand and from the little finger in the left), beams (join, take away, cut, join to the group
   before), the grace note switch (`asgrace`, `nograce`), ornaments (trill, mordent, turn over onsets; rolled chord,
   fermata), notes taken off the page (`edits.remove_notes`, undone), and over a stretch the armadura (with the one
   of fewest signs offered), the clef of each hand, the clef rules and the octave lines.
3. Engine features the tools need (for example fingers, octave brackets over a range), kept light. *Done:* none
   was needed: the engine already drew fingers (the research's phase 10), ornaments, 15ma and 15mb; the core gained
   the user's marks in the format and the rules, and `assemble(join=False)` for a sheet laid again.
4. **The range selection on the new sheet** (the user, 2026-10-25): a stretch of time frames picked on the sheet,
   with **Both / Right / Left** to limit it to one hand's staff, opening the range toolbox, as in the old sheet.
   *Done:* the strip above the upper staff of each line (click, drag, Shift-click), a lavender band over the staves
   in scope; each toolbox hands its selection to the other.
5. **Enhance with AI, with the user's own instruction** (the user, 2026-10-25), from **both selections**: the notes
   picked (the note toolbox) and a range of time frames (the range toolbox, Both / Right / Left). The user writes a
   short instruction (for example "all these notes are in the left hand: share them between the two hands"); the AI
   rewrites only that stretch: one window request with the stretch as its target, the music before and after as
   context and look-ahead, the current hands shown, and the instruction added to the window prompt. The answer
   goes through the checker and is written into the stored sheet and the hands for that stretch only, as one step
   of undo (the edit model of Phase 6). No text while it works, only the pale veil on the stretch (plan section
   3.6). A few cents and about half a minute a request. *Done:* `llm.frames.write_stretch` and `splice`,
   `job.start_stretch`, `POST /sheet/{uuid}/llm/stretch`, the ✨ of both toolboxes and its dialog; a real request on
   7 Years: 9 s, $0.0144.

*Done when:* every tool of the two toolboxes works on the new sheet or the user agreed to drop it, and a stretch can
be enhanced with AI with the user's instruction from either selection.

## Phase 8: The other screens and the sheet toolbox

*Why:* the sheet is also drawn outside the Sheet step, and the sheet toolbox has its own features.

1. Study and inventory: the sheet toolbox (title, key, transpose, lyrics, layout), the keyboard panel, Find trills,
   Play mode (cursor kept in the middle, lyrics by frames, Notes Falling as a view), Recording in Sheet (the Current
   and the Proposal, with its own sheet toolbox), copy and paste, parts and playlists, the PDF print, and what phase 0
   found besides: the Transpose preview dialog (it draws the sheet on its own, `TransposeDialog.tsx`), From other
   projects (`ComposePage.tsx`), and the requests review (`Conversation.tsx` and `RequestSheet.tsx`, Proposed and
   Now). The database held no request on 2026-10-23, so the review was not in the phase 0 screenshots; this phase
   makes one with temporary users, as `check:requests` does. *From Phase 7:* the sheet toolbox of the new sheet
   carries Transpose (figures: the reference figure `quarterMs`, which the spacing also reads; notes: every midi
   moves, so the stored sheet must move with it, since `build.reapply` matches notes by column and key) and Find
   trills; the range toolbox gains Copy, Record this passage and Start a new part.
2. **Lyrics** in the format and in the engine (they are keyed by frames, which fits the new sheet).
3. Each screen moved to the new engine; vexflow-v2 is no longer used anywhere for drawing or editing.

*After the study (2026-10-26, report section 2):* the phase is built in two halves, each checked by the user in the
browser. **8A, the Sheet step's own tools:** the sheet toolbox (Title, Key, Transpose notes and figures with their
preview, Lyrics, and a View tab with Zoom and Space between lines), the keyboard panel, Print to PDF from the new
engine, Play mode's lyrics. **8B, the screens of a stretch:** `sheet.f1` follows every change of a part's length
(paste, promotion, split, join, From other projects, a comment's excerpt: today its decisions after that point are
lost), copy and paste, Start a new part, the read-only stretch actions (Add to a playlist, Add this stretch, Comment on
this stretch), the requests review, Recording in Sheet, the blank sheet of From scratch; then the switch to the old
sheet is removed and its browser checks move. The user's answers (2026-10-26): Layout keeps only Zoom and Space between
lines; lyrics stay above the upper staff with the whole editor (pool, drag onto frames, split, merge, words, size,
lift); a take's sheet is the algorithm's, with Enhance with AI as a button, and Promote carries its reading into the
song; Find trills, Remove all and Bring back N notes taken off are dropped. The agent's choices: Transpose figures only
renames the figures and the page keeps its widths (D-18, nothing moves); the old `sheet.json` marks stay stored when
the switch goes, and Phase 9 maps them.

*The user's request of 2026-10-26, after 8A was built (part of 8A, before 8B):* **a keyboard in the note toolbox.**
When notes are picked (one note, or a chord: the notes of one column), the note toolbox shows a small piano (the
mini piano of the sheet toolbox's Transpose tab, `ui/MiniPiano.tsx`, or the keyboard panel's `piano/Piano.tsx`) with
the keys of the picked column lit in their hand's colour. On it the user changes the chord: a dark key adds a note to
that column (`POST /sheet/{uuid}/add`, in the hand of the picked chord, as long as the chord), a lit key takes that
note off (`POST /sheet/{uuid}/remove`); each press one step of undo. The study of the session decides what it shows
when notes of several columns are picked, and asks the user only if no answer follows from the old keyboard panel.

*Done when:* every screen of the inventory uses the new engine, checked in the browser by the user.

## Phase 9: The saved data

*Why:* existing projects and library versions hold `sheet.json` corrections made for vexflow-v2 (hands, overrides,
beam breaks, clefs, ottavas, keys, lyrics). They must open correctly in the new sheet.

1. Study: what the `.database/` holds (how many parts, which correction fields are used, how often).
2. With the user's answer of phase 5: map the corrections onto the new sheet (`synthesis/06-modules.md` §6.6), or
   write the new sheet again with the LLM (credits), or both.
3. A migration with a backup first (`make db-backup`), a dry run, a count of what moved and what could not move.

*Done when:* every part of the database opens in the new sheet, and the report says what could not be mapped.

## Phase 10: vexflow-v2 removed, documentation, closing

1. Remove the `@aimpromptu/grid-notation` dependency, the `TimeScorePayload` routes, the backend modules that only fed
   vexflow-v2 (`notation/`, the negra ladder for the sheet), and the Hands step code. The Hands step code is the page
   (`HandsTab.tsx`, the `hands` step of the status) and **Predict hands**; the beam search `aitu_backend/hands/` stays,
   because the algorithm and the LLM step receive its split as their starting hands (`hand_sheet`). Two routes have no
   caller in the frontend already (`GET /time/{uuid}/peaks`, `POST /time/{uuid}/ladder-preview`; only tests call
   them); `GET /time/{uuid}/default-reading` is the negra choice of the Sheet step.
2. Documentation: the time model (D-09 changed, rule 3 confirmed), the project steps, the sheet pages, rendering, the
   API.
3. All checks; the final screenshots against the phase 0 baseline; merge into `master` after the user's OK.
4. Licenses before any release (`synthesis/05-recommendations.md` §5.6): the Verovio rules ported in `engrave/vrv.py`
   (LGPL-3.0), the Leipzig glyphs (SIL OFL), the prompt examples.

# 8. Decision points (raised in the phases, after their study)

| Phase | Decision |
|---|---|
| 2 | The figure thresholds and the Do mayor spelling (agent, from songs: 0.7, and Do#, Mib, Fa#, Sol#, Sib; user checks the gallery); the cap of a figure at the next onset of its hand, and rule 4 in armaduras of one to three signs (user) |
| 3 | The look of the spacing without compases (approved), and a thin double line at an armadura change or none (none, the default) (user, in the gallery) |
| 4 | The API key (human intervention; done); how many songs the credits cover (information: about 110 a month); the beam groups and the maximum of 8 (user, in the gallery); the left hand's clef changes of rule clef.L4, and the figures of staccato notes (user: approved; both rules kept as written) |
| 5 | Existing projects: keep their data, the AI's sheet for the 10 songs it wrote, a button for the rest (user, 2026-10-25); merge to `master`: now (user, 2026-10-25) |
| 6 | May a new LLM run change hands that the user moved (user, 2026-10-25: yes, it reads them as a suggestion); the engine in the backend or in the browser (agent, from the time of one edit: the backend) |
| 7 | Tools that no longer make sense (user, 2026-10-25): drop even spacing, the room of a stretch and speed changes; replace print smaller and the unplayed decoration by a grace note switch; drop hiding and dragging an 8va bracket. A new AI run keeps the user's fingers, figures and grace switches and writes its own kinds again |
| 8 | Tools of the sheet toolbox and the other screens that no longer make sense (user, 2026-10-26): Layout keeps Zoom and Space between lines; lyrics stay above the staff with the whole editor; a take's sheet is the algorithm's with Enhance with AI as a button; Find trills, Remove all and Bring back are dropped |

# 9. Risks

- **Note lengths from the audio are noisy** (pedal, release), and figures now come from them. Phase 2 measures it; the
  LLM and the user's override correct the rest.
- **Beam groups without a printed pulse** depend on the LLM's judgement (section 3.11). The maximum of 8 notes is
  checked; the rest is judged by the user in the phase 4 gallery, and the criteria or the maximum change if needed.
- **The piece-by-piece view moves the sheet** when a segment changes width. Phase 3 makes line breaks stable; phase 5
  checks it in the browser.
- **The credits run out** (100 USD per month). The algorithm's sheet stays and stays editable; phase 4 measures the
  real cost per song.
- **The branch lives long** while `master` moves. Merge `master` in at the start of each phase; decide an early merge
  at phase 5.
- **Hidden uses of vexflow-v2** not in the docs. Phase 0's inventory starts from the code imports, not from the docs.

# 10. The copy to Ubuntu and the first hand-off

The copy was made before Phase 0; Phase 0 checked it on Ubuntu (the folder at git `a208a92`, 9.4 GB of `data/`, `uv
sync`, 139 core tests and 367 research tests passing). The section stays as the record of how it was made.

The research folder is copied from the Mac with all its history and data (about 10 GB, of which 9.4 GB is `data/`;
the Python environment `.venv` is not copied and is rebuilt with `uv sync`):

```bash
# on the Mac
rsync -a --exclude '.venv/' --exclude '__pycache__/' --exclude '.pytest_cache/' \
  /Volumes/DevSSD/Documents/projects/music/poc-research-aitu/ \
  ubuntu:/home/david/Documents/projects/music/poc-aitu-research/
```

The private library audio and the downloads in `data/raw/` stay private on the home machines.

First message for the agent on Ubuntu:

"You are working on an implementation plan. Read
@/home/david/Documents/projects/music/poc-aitu-research/context/implementation-plans/01-research-format-llm/05-final-report.md,
@/home/david/Documents/projects/music/poc-aitu-research/context/implementation-plans/01-research-format-llm/05-final-report-prompt.md,
@/home/david/Documents/projects/music/poc-aitu-research/guidelines/communication-implementation-plans.md,
@/home/david/Documents/projects/music/poc-aitu-research/guidelines/communication-style.md and
@/home/david/Documents/projects/music/poc-aitu-research/src/aitu_notation/README.md. Start Phase 0 in the aimpromptu
repository."

# 11. Changes made by the phases

| Phase | Change | Why |
|---|---|---|
| 0 | The folder is `03-apply-poc-research/`, not `03-new-sheet/` (section 6.1) | The user had already made it |
| 0 | Phase 5 tasks 7 to 9: the switch inside `SheetPage`; the browser checks move to `data-*` hooks; no line naming the figure and a tempo | The inventory: six screens draw through `SheetPage`; 16 scripts select vexflow-v2 classes; the line is on every sheet today |
| 0 | Phase 8 task 1 names the Transpose preview, From other projects and the requests review | Found by the inventory of imports, not in the first list |
| 0 | Phase 10 task 1: `aitu_backend/hands/` stays; two routes already have no caller | The algorithm and the LLM step start from its split |
| 1 | Phase 1 tasks 1 and 3: the core keeps its inner layout (`aitu_backend.sheet.sheet` is the research's `aitu_notation.sheet`), its tests live in the backend's `tests/`, and the proof is a command, not a route | A one-to-one name map keeps every later comparison with the research simple; `pytest` collects only `tests/`; a route needs the rights table and gives the user nothing yet |
| 1 | Phase 2 task 6: the algorithm's starting hands come from `aitu_backend.hands` for the notes without a saved hand | 1,652 notes of the library have none, and the core's default gives them a hand by middle C only |
| 1 | Phase 3 task 6: the speed is measured in the container, and its Python build is looked at | The container draws about 30 % slower than the host on the same code |
| 2 | Phase 2 tasks 3 and 4: the length is capped at the next onset of the hand (kept); one figure per run of even gaps; chords grouped on raw onsets (D-04); grace notes at most 100 ms early and not of the same note name | Measured: without the cap 37 % of the notes of even runs change figure inside the run; uneven chords and octaves made false grace notes |
| 2 | Section 3.3 and Phase 2 task 4: beam groups of one figure; the acciaccatura limits reduced to "a semicorchea or shorter, sounding just before" | The user's review of the gallery (2026-10-23) |
| 2 | Section 3.3: no tuplets in the new sheet | No beat to find a tresillo on; the figures are approximate by the user's rule |
| 2 | Section 3.4: rule 4 keeps the becuadro when the other name needs two signs; Do mayor's table | Rules 3 and 4 meet on Sol, Re, La in Mi mayor; the research rulebook |
| 2 | Phase 3 task 4 and Phase 4 task 4: accidentals by `frames.printed_signs` (rule 7 added by the user when Phase 2 closed); figures are not durations; the LLM's answer mapped back to the notes and its figures computed by the rule; `arp` and tuplets left to Phase 4 | What the new sheet carries (`03-implementation-phase-2.md` section 12) |
| 3 | Section 3.2: empty time is the time beyond a blanca between two columns, whatever still sounds; figures are not read by the spacing | The user's example is the gap after a redonda; a rule on the sounding figure left that gap at full width |
| 3 | Phase 3 task 5: one segment is drawn as the systems of the whole song that hold it, not as a sheet of its own | The page of Phase 5 replaces systems in place; a segment drawn alone would have other line breaks |
| 3 | Phase 3 task 6 and Phase 5 task 3: uv's Python in the backend image is measured, and done in Phase 5 | It removes most of the container's cost (32 % to 8 %), but a rebuild restarts the running app, and 10 ms per song do not matter before the engine is served |
| 4 | Phase 4 tasks 3 and 4: figures, grace notes and spelling stay rules computed after the LLM's hands; the reference figure is its own request; windows end at a pause and are kept whole | The cap of a figure needs the hand; without bars there is no last bar to decide again, and fixed windows give Phase 5 its segments |
| 4 | Section 3.11: a written group keeps a sixteenth beamed to its eighth (one odd note next to one note) | The algorithm's limit (two notes of the group's figure) removed 410 of Sonnet's 2,044 groups; the user's rule allows one odd note |
| 4 | Phase 4 task 4: no note four or more ledger lines above its staff in the checker; nearby 8va notes joined | The first run left 244 notes of one song far above the staff, and then one 8va bracket per note |
| 4 | Phase 5 task 3: the segments are the LLM's windows; the reference request redraws the algorithm's sheet first | What the LLM step gives |
| 5 | Phase 5 task 1: existing songs keep their data and get **Enhance with AI**; the 10 viewer songs show Sonnet's sheet; new transcriptions go to Sonnet by themselves (marked `sheet.pending`) | The user's answer of 2026-10-25 |
| 5 | Phase 5 task 3: on a version of My library, **Enhance with AI** opens the edit copy and starts there | The rights table: a library version is never written in place |
| 5 | Phase 5 task 7: the passage page, From other projects and the requests review keep the old sheet until Phase 8; Play mode has no lyrics until Phase 8 | Their work is a marked stretch; the new engine has no lyrics yet (4 parts had lyrics) |
| 5 | Phase 5 task 2: an old `sheet.json` keeps its key and a figure renamed by the user; the default negra is replaced by the pulse estimate | "Keep all the data"; the default negra was not a choice (36 of 43 sheets) |
| 5 | Phase 6: a stored sheet is laid again on changed notes by column and key (`build.reapply`); a paste moves the columns after it, so those decisions are lost there until notes are matched by id | What the study found about the edit model |
| 5 | The page says "AI", never the model's name; a sheet the AI enhanced keeps its **Enhanced with AI** mark through every later change, and a failed rerun keeps the earlier AI sheet; the AI mark on Projects and My library | The user's review of 2026-10-25: the model may change, and the user must know which sheets the AI wrote |
| 5 | Section 6.3: the branch was merged into `master` at the end of Phase 5 | The user's answer |
| 6 | Section 3.7: a run again may change any hand; it reads the current hands as a suggestion on a sheet the AI enhanced, the notes without hands on a first run; no edit while the AI writes | The user's answer of 2026-10-25; the research found the LLM copies the hand split's errors when it is shown them; the job's hands would replace the moves made during the run |
| 6 | Phase 6 task 2: the backend keeps undo and redo (a log per part), and the answer of an edit is the whole sheet drawn again, not one segment | A log in the backend survives a reload and checks each step against the stored truth; the whole sheet draws in about 50 ms, and a hand move can change the figures and the clefs around it |
| 6 | Phase 6 task 3: a note that changes staff gets the algorithm's clefs and 8va on the stretch where they differ from the stored ones | A high note moved to the left hand kept the bass clef with five ledger lines, which the AI's checker forbids (clef.L3) |
| 6 | Phase 6 task 4: the engine stays in the backend | One edit takes about 0.25 s to the page; the drawing is about a third of the backend's part |
| 6 | Playback of a part without cuts: a compressed file plays as a lossless FLAC copy | A jump inside a variable-bitrate MP3 landed up to 0.6 s away from the time the player reported, so the music did not match the notes after moving the cursor (the user's report; measured in Chromium) |
| 6 | Phase 7 tasks 4 and 5: the range selection (Both / Right / Left) on the new sheet, and **Enhance with AI** of a stretch with the user's own instruction, from the notes picked or from a range | The user's requests of 2026-10-25, during the Phase 6 check |
| 7 | Phase 7 task 2: transpose figures and the transposition of notes move to Phase 8, with the sheet toolbox that holds them; so do Copy, Record this passage and Start a new part | They are in the sheet toolbox and the range toolbox's title bar, which belong to the screens of Phase 8; the plan listed them in both phases |
| 7 | Phase 7 tasks 1 and 2: even spacing, the room of a stretch, speed changes, print smaller, the unplayed decoration, hiding and dragging an 8va bracket are dropped; a grace note switch is added | The user's answers of 2026-10-25 (report section 3) |
| 7 | Section 3.7: a new AI run keeps the marks only the user writes and writes the AI's kinds again | The user's answer of 2026-10-25 |
| 7 | Section 4: an 8vb in the bass clef is allowed (`frames.check`) | The old sheet's data has 139 8vb and 65 15mb brackets, and the clef rule forbids only 8va there |
| 7 | Fingers on one chord: from the thumb in the right hand, from the little finger in the left | The old sheet gave the lowest note the smallest number in both hands, which is wrong for the left hand |
| 7 | Phase 7 task 5: the stretch request shows the stretch as it is now, puts the user's words first ("of the utmost importance") and may leave notes out, which are taken off the page in the same step | The user's first check: "make all the notes single notes instead of the current octave notes" changed nothing, because the checker demanded every note back and the AI did not see the current beams |
| 7 | Phase 7 task 5: with the user's words a stretch request aims at a sheet simpler to read and to play (uniform patterns) and may change pitches, add notes and set figures; those go into `notes.pmn` and the sheet in the same undo step | The user's second check: a lone low note stayed when the octaves became single notes, and figures could not be asked for |
| 8 | Phase 8 is built in two halves (8A the Sheet step's tools, 8B the screens of a stretch), each checked in the browser; 8B starts with `sheet.f1` following every change of a part's length | The study: the phase holds more than Phase 7, and paste, promotion, split, join and From other projects lose the new sheet's decisions after the change today |
| 8 | Layout keeps Zoom and Space between lines; lyrics stay above the staff with the whole editor; a take's sheet is the algorithm's; Find trills, Remove all and Bring back are dropped | The user's answers of 2026-10-26 |
| 8 | Phase 8A gains a keyboard in the note toolbox: the picked chord's keys lit; a key adds or takes off a note of that column | The user's request of 2026-10-26, after seeing 8A |
| 8 | Transpose figures renames the figures and keeps the page's widths | D-18 ("nothing moves"); the spacing model reads the reference figure, so a rename alone would widen or narrow the page |
